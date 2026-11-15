"""The uniform update lookup (ub_buckets) answers as a walk of the whole update list does.

ub_overlay and ub_read look an address range up in the buckets the updates touch instead of walking the list, which
spans the submissions still in flight. The list's own functions (ub_push, ub_prune, ub_truncate, the lookups, ub_read
and ub_overlay with their caches) are cut out of gpu/vk/vk_replay.cpp and run on random lists, limits (a parallel
replay's worker sees the updates before its segment only) and ranges, against a walk of a copy of the list: the same
bytes for every read and overlay, the same answer whether an update overlaps, gaps no update of the range's limit
covers. Then the list is held still and threads read it at once, as the workers do.
python -I -B tests/test_ub_index.py [--cxx g++]
"""
import argparse
import os
import subprocess
import tempfile
from pathlib import Path

RUN_ALL_ARGS = ["--cxx", "{cxx}"]

ROOT = Path(__file__).resolve().parents[1]


def block(text, marker):
    start = text.index(marker)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def between(text, start, stop):
    a = text.index(start)
    return text[a:text.index(stop, a)]


STUBS = r'''
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <functional>
#include <map>
#include <memory>
#include <random>
#include <thread>
#include <vector>
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr, "FAIL:%d %s (seed %u, step %d)\n", __LINE__, #x, seed, step); std::exit(1); } } while (0)
unsigned seed = 0;
thread_local int step = 0;
thread_local size_t ub_limit = SIZE_MAX;
size_t ub_first_of_recording = 0;
uint64_t rec_value_now = 1;
std::atomic<int64_t> st_ub_overlays{0};
bool env_on(const char* name) { const char* e = std::getenv(name); return e && std::atoi(e); }
uint64_t memory_capture_view() { return 1; }
bool stream_holds(const uint8_t*, uint64_t, uint64_t) { return true; }   // (the fixture's copies are never written over)
uint32_t memory_page_stamp(uint64_t) { return 1; }
uint8_t captured(uint64_t a) { a ^= a >> 7; a *= 0x9e3779b97f4a7c15ull; return (uint8_t)(a >> 56); }
std::atomic<bool> reads_fail{false};
bool memory_read_as_submitted(uint64_t addr, void* dst, uint64_t n) {
    if (reads_fail) return false;
    for (uint64_t i = 0; i < n; i++) ((uint8_t*)dst)[i] = captured(addr + i);
    return true;
}
'''

MAIN = r'''
// ---- the walk the lookups stand in for: a copy of the list ----
struct Ref {
    uint64_t value, dst;
    std::vector<uint8_t> bytes;
};
std::vector<Ref> ref;
bool ref_overlaps(size_t first, size_t lim, uint64_t addr, uint64_t n) {
    for (size_t i = first; i < lim; i++)
        if (ref[i].dst < addr + n && addr < ref[i].dst + ref[i].bytes.size()) return true;
    return false;
}
void ref_apply(size_t first, size_t lim, uint64_t addr, uint64_t n, uint8_t* p) {
    for (size_t i = first; i < lim; i++) {
        const Ref& u = ref[i];
        const uint64_t lo = std::max(addr, u.dst), hi = std::min(addr + n, u.dst + u.bytes.size());
        if (lo < hi) std::memcpy(p + (lo - addr), u.bytes.data() + (lo - u.dst), hi - lo);
    }
}
bool ref_odd(size_t first, size_t lim) {   // (an update the buckets may leave to the walk: one that wraps, or a big one)
    for (size_t i = first; i < lim; i++)
        if (ref[i].dst + ref[i].bytes.size() <= ref[i].dst || ref[i].bytes.size() > 65536) return true;
    return false;
}

constexpr uint64_t kBase = 0x80000000ull, kSpan = 0x40000;   // (the updates and ranges: 256 KB of guest memory)
struct Range {
    uint64_t addr, n;
};
Range pick_range(std::mt19937_64& r) {
    const int k = (int)(r() % 100);
    uint64_t n = k < 40 ? 4 : k < 60 ? 16 * (1 + r() % 16) : k < 85 ? 1 + r() % 4096 : k < 97 ? 1 + r() % 65536 : k < 99 ? 0 : 64;
    uint64_t addr = kBase - 0x1000 + r() % (kSpan + 0x2000);
    if (k >= 99) addr = ~uint64_t{0} - r() % 32;   // (a range that wraps)
    if (k < 40) addr &= ~3ull;
    return {addr, n};
}
std::atomic<int64_t> by_index{0}, walked{0};
void stream_reset(uint64_t& used) {   // (its copies are written over from here on: the ones kept go)
    used = 0;
    for (auto& c : ub_copies) c = {};
}

/// One range checked every way, on the list's [first, lim)
void check_range(std::mt19937_64& r, size_t lim, Range q, std::vector<uint8_t>& stream, uint64_t& used) {
    const size_t size = ref.size();
    const size_t first = r() % 4 == 0 && lim ? r() % (lim + 1) : 0;
    const bool any = ref_overlaps(first, lim, q.addr, q.n);
    std::vector<uint8_t> want(q.n), got(q.n);
    for (uint64_t i = 0; i < q.n; i++) want[i] = got[i] = captured(q.addr + i);
    ref_apply(first, lim, q.addr, q.n, want.data());
    // the lookups
    uint64_t lo = 1, hi = 0;
    const int found = ub_find(first, lim, q.addr, q.n, &lo, &hi);
    if (found < 0) {
        CHECK(ub_walk(first, lim, q.addr, q.n));
        CHECK(!q.n || q.addr + q.n < q.addr || ref_odd(first, lim));
        walked++;
    } else {
        CHECK(!ub_walk(first, lim, q.addr, q.n));
        CHECK((found == 1) == any);
        if (!found) {   // (a gap: round the range, and no update of [first, lim) in it)
            CHECK(lo <= q.addr && q.addr + q.n <= hi);
            CHECK(!ref_overlaps(first, lim, lo, hi - lo));
        }
        by_index++;
    }
    CHECK(ub_overlaps(first, lim, q.addr, q.n) == any);
    ub_apply(first, lim, q.addr, q.n, got.data());
    CHECK(got == want);
    if (ub_try_gap(first, lim, q.addr, q.n)) {
        CHECK(!any);
        CHECK(ub_gap_cache.lo <= q.addr && q.addr + q.n <= ub_gap_cache.hi);
        CHECK(!ref_overlaps(first, lim, ub_gap_cache.lo, ub_gap_cache.hi - ub_gap_cache.lo));
    } else {
        CHECK(any || !q.n || q.addr + q.n < q.addr);
    }
    // ub_read and ub_overlay, as a worker with this limit sees them (ub_limit: SIZE_MAX the whole list, 0 a background
    // thread's none), with their caches as they are
    ub_limit = lim == size && r() % 2 ? SIZE_MAX : lim;
    std::fill(want.begin(), want.end(), 0);
    for (uint64_t i = 0; i < q.n; i++) want[i] = captured(q.addr + i);
    ref_apply(0, lim, q.addr, q.n, want.data());
    std::fill(got.begin(), got.end(), 0);
    if (q.n <= 65536 && (q.n || r() % 2)) {
        CHECK(ub_read(q.addr, got.data(), q.n));
        CHECK(got == want);
    }
    if (q.n && q.n <= 65536 && q.addr + q.n >= q.addr) {
        static const bool cur_only = env_on("RX_VK_UB_CUR_ONLY");
        const size_t from = cur_only ? std::min(ub_first_of_recording, lim) : 0;
        std::vector<uint8_t> over(q.n);
        for (uint64_t i = 0; i < q.n; i++) over[i] = captured(q.addr + i);
        ref_apply(from, lim, q.addr, q.n, over.data());
        const bool full = r() % 16 == 0;   // (the stream has no room: no copy)
        const uint64_t at = ub_overlay(q.addr, q.n, stream.data(), [&](uint64_t bytes) {
            if (full || used + bytes > stream.size()) return UINT64_MAX;
            const uint64_t a = used;
            used += bytes;
            return a;
        });
        if (at != UINT64_MAX) {
            CHECK(ref_overlaps(from, lim, q.addr, q.n));
            CHECK(std::memcmp(stream.data() + at, over.data(), q.n) == 0);
        } else {
            CHECK(!ref_overlaps(from, lim, q.addr, q.n) || full || used + q.n > stream.size());
        }
    }
    ub_limit = SIZE_MAX;
}

int main(int argc, char** argv) {
    seed = argc > 1 ? (unsigned)std::atoi(argv[1]) : 1;
    std::mt19937_64 r(seed);
    std::vector<uint8_t> stream(64 << 20);
    uint64_t used = 0, value = 1, done = 0;
    for (step = 0; step < 6000; step++) {
        const int op = (int)(r() % 100);
        if (op < 55) {   // an update: mostly small and often on the same few addresses, sometimes big, rarely odd
            const int k = (int)(r() % 100);
            uint64_t size = k < 60 ? 4 * (1 + r() % 64) : k < 90 ? 1 + r() % 4096 : 1 + r() % 65536;
            uint64_t dst = k < 30 ? kBase + 0x1000 * (r() % 8) + 0x40 * (r() % 4) : kBase + r() % kSpan;
            const int odd = (int)(r() % 400);
            if (odd == 0) size = 65536 * 2 + r() % 4096;                                   // (over 128 buckets)
            if (odd == 1) dst = ~uint64_t{0} - r() % 64, size = 1 + r() % 256;   // (wraps)
            std::vector<uint8_t> bytes(size);
            for (auto& b : bytes) b = (uint8_t)r();
            if (r() % 8 == 0) value++;
            ub_push(value, dst, bytes.data(), size);
            ref.push_back({value, dst, bytes});
        } else if (op < 62) {   // a prune: the submissions the GPU is done with
            done = std::min(value, done + r() % 3);
            ub_prune(done);
            size_t n = 0;
            while (n < ref.size() && ref[n].value <= done) n++;
            ref.erase(ref.begin(), ref.begin() + (ptrdiff_t)n);
            ub_first_of_recording = std::min(ub_first_of_recording, ub_updates.size());
        } else if (op < 64) {   // the benchmark's cut back
            const size_t n = ref.empty() ? 0 : r() % (ref.size() + 1);
            ub_truncate(n);
            ref.resize(n);
            ub_first_of_recording = std::min(ub_first_of_recording, ub_updates.size());
        } else if (op < 66) {
            ub_first_of_recording = ub_updates.size();
            rec_value_now++;
        } else if (op < 67) {
            stream_reset(used);
            rec_value_now++;
        }
        CHECK(ub_updates.size() == ref.size());
        for (size_t i = 0; i < ref.size(); i += 1 + ref.size() / 8)
            CHECK(ub_updates[i].dst == ref[i].dst && ub_updates[i].size == ref[i].bytes.size() &&
                  std::memcmp(ub_updates[i].bytes, ref[i].bytes.data(), ref[i].bytes.size()) == 0);
        for (int i = 0; i < 6; i++) {
            const size_t lim = r() % 3 == 0 ? r() % (ref.size() + 1) : ref.size();
            Range q = pick_range(r);
            if (i % 3 == 2 && !ref.empty()) {   // (a range at an update, or right beside one)
                const Ref& u = ref[r() % ref.size()];
                const uint64_t at[] = {u.dst, u.dst + u.bytes.size(), u.dst - q.n, u.dst + r() % u.bytes.size()};
                q.addr = at[r() % 4];
            }
            check_range(r, lim, q, stream, used);
            if (i == 0) {   // (the same range again: from the caches now)
                ub_limit = SIZE_MAX;
                check_range(r, ref.size(), q, stream, used);
            }
        }
        if (used > stream.size() / 2) stream_reset(used);
    }
    // the parallel replay: the list held still, threads read it at once, each with its own limit
    rec_value_now++;
    std::vector<std::thread> threads;
    for (int t = 0; t < 4; t++)
        threads.emplace_back([t] {
            std::mt19937_64 tr(seed * 31 + t);
            std::vector<uint8_t> own(16 << 20);
            uint64_t own_used = 0;
            for (step = 0; step < 3000; step++) {
                const size_t lim = ref.empty() ? 0 : tr() % (ref.size() + 1);
                check_range(tr, lim, pick_range(tr), own, own_used);
                if (own_used > own.size() / 2) stream_reset(own_used);
            }
        });
    for (auto& t : threads) t.join();
    // a failed read of the capture: ub_read says so
    reads_fail = true;
    uint32_t w = 0;
    CHECK(!ub_read(kBase, &w, 4));
    reads_fail = false;
    // all of it pruned: nothing kept
    ub_prune(~uint64_t{0});
    ref.clear();
    CHECK(ub_updates.empty() && ub_buckets.empty() && ub_odd.empty() && ub_chunks.empty());
    std::printf("seed %u: %lld ranges looked up in the buckets, %lld walked\n", seed, (long long)by_index.load(),
                (long long)walked.load());
    CHECK(walked > 0 && by_index > 2 * walked);
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cxx", default="g++")
    a = p.parse_args()
    source = (ROOT / "gpu" / "vk" / "vk_replay.cpp").read_text(encoding="utf-8")
    fixture = STUBS
    fixture += between(source, "struct UbUpdate {", "// ---- parallel replay (RX_VK_PARALLEL")
    fixture += block(source, "void ub_prune(") + "\n"
    start = source.index("/// The open gap around [addr, addr+bytes)")
    read = block(source, "bool ub_read(")
    fixture += source[start:source.index(read) + len(read)] + "\n"
    fixture += MAIN
    with tempfile.TemporaryDirectory(prefix="ub-index-") as tmp:
        cpp = Path(tmp) / "fixture.cpp"
        exe = Path(tmp) / "fixture"
        cpp.write_text(fixture, encoding="utf-8")
        subprocess.run([a.cxx, "-std=c++20", "-O2", "-pthread", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function",
                        "-D_CRT_SECURE_NO_WARNINGS", str(cpp), "-o", str(exe)], check=True)
        for seed in ("1", "2", "3"):
            subprocess.run([str(exe), seed], check=True)
        # (RX_VK_UB_CUR_ONLY=1: ub_overlay's updates from the recording's first on)
        subprocess.run([str(exe), "4"], check=True, env=dict(os.environ, RX_VK_UB_CUR_ONLY="1"))
    print("PASS: the uniform update lookup answers as the walk of the list does")


if __name__ == "__main__":
    main()
