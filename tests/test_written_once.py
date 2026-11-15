"""A storage buffer a program writes, bound again in the same recording, is noted once: the answers stay the same.

Most draws rebuild their descriptors, and the culling dispatches bind the same written ranges one after another. Each
binding noted the write three times over: texture_gpu_wrote (a lock and a map lookup), gpu_buffer_bind's write-back and
hazard (ParLock and the pools' lock) and memory_stamp_gpu (a page loop and cap_view_bump). The same range again is now
left as it was while nothing a reader asks has moved (RX_VK_WRITTEN_EACH=1: every one, as before).

Cuts the actual texture_gpu_wrote and memory_stamp_gpu with their memos out of the sources and runs the same pseudo-random
sequence of notes, stamps, kept generations, captures and readers' questions with RX_VK_WRITTEN_EACH=1 and without: the
map of GPU writes (its bound made small, so that its evictions run) and every answer must be the same, with fewer locks
and stamps. A copy with the memo's main check taken out must answer differently (the sequence can tell). Then checks
in the sources that every reader keeping a generation, and the capture, moves the stamps' fence. gpu_buffer_bind's
memo runs in tests/test_direct_buffer_writes.py (its written_again cases). No game or GPU is needed.

python -I -B tests/test_written_once.py [--cxx g++]
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

RUN_ALL_ARGS = ["--cxx", "{cxx}"]

ROOT = Path(__file__).resolve().parents[1]
# (env_on, the switches' rule, before the code cut out of the sources: gpu/vk/compat/longshot_env.h)
ENV_ON_H = str(ROOT / "gpu" / "vk" / "compat" / "longshot_env.h")


def block(text, marker, semicolon=False):
    start = text.index(marker)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    if semicolon:
        assert text[end] == ";", marker
        end += 1
    return text[start:end]


def cut(text, start, end):
    if text.count(start) != 1:
        raise SystemExit("FAIL: marker not found once: " + start)
    a = text.index(start)
    return text[a:text.index(end, a)]


FIXTURE = r"""
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <mutex>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

// ---- texture_gpu_wrote, as vk_texture.cpp has it, and what it reads ----
struct CountingMutex {   // (the locks taken)
    std::mutex m;
    int64_t n = 0;
    void lock() { m.lock(); n++; }
    void unlock() { m.unlock(); }
};
std::map<uint64_t, std::pair<uint64_t, uint64_t>> gpu_wrote;
CountingMutex gpu_wrote_mu;
uint64_t rec_value = 1, frame_no = 0, tl_watch_prog = 0;
void logf(const char*, ...) {}
namespace wrote_regions { void mark(uint64_t, uint64_t) {} }   // (its own behaviour is another test's: here the mark only has to exist)
#include "gpu_wrote_seen.inc"
#include "texture_gpu_wrote.inc"

// ---- memory_stamp_gpu, as vk_memory.cpp has it, over a model of the page generations ----
constexpr uint64_t kPageShift = 12;
uint32_t gen_now = 1;
std::map<uint64_t, uint32_t> page_gen, cap_entry;   // (a page's generation; the capture's entry of a page it took)
int64_t stamps = 0;
void memory_stamp(uint64_t guest, uint64_t size) {   // (vk_memory.cpp's: a new generation over the range's pages)
    stamps++;
    const uint32_t g = ++gen_now;
    for (uint64_t p = guest >> kPageShift; p <= (guest + size - 1) >> kPageShift; p++) page_gen[p] = g;
}
bool gpu_pages_on() { return false; }
std::mutex gpu_pages_mu;
std::unordered_map<uint32_t, uint32_t> gpu_pages;
namespace {
#include "stamp_seen.inc"
#include "stamp_gpu.inc"
uint32_t memory_generation() {   // (as vk_memory.cpp's: the script checks it moves the fence)
    stamp_fence_bump();
    return gen_now;
}
void take_capture(uint64_t guest, uint64_t size) {   // (as take_capture: the fence, then its pages and entries)
    stamp_fence_bump();
    const uint32_t g = ++gen_now;
    for (uint64_t p = guest >> kPageShift; p <= (guest + size - 1) >> kPageShift; p++) page_gen[p] = g, cap_entry[p] = g;
}
bool written_since(uint64_t guest, uint64_t size, uint32_t gen) {   // (memory_written_since)
    for (uint64_t p = guest >> kPageShift; p <= (guest + size - 1) >> kPageShift; p++)
        if (page_gen.count(p) && page_gen[p] > gen) return true;
    return false;
}
}  // namespace

uint64_t mix(uint64_t h, uint64_t v) { return (h ^ v) * 0x100000001B3ull; }

int main(int argc, char** argv) {
    const std::string what = argc > 1 ? argv[1] : "";
    std::mt19937_64 rng(1234);
    uint64_t h = 0xCBF29CE484222325ull;
    if (what == "wrote") {   // (the map of GPU writes after every note)
        const uint64_t los[] = {0x10000, 0x10040, 0x20000, 0x20000, 0x30000, 0x30100, 0x40000, 0x50000};
        const uint64_t sizes[] = {0x40, 0x100, 0x1000, 0x40, 0x2000, 0x100, 0x10, 0x8000};
        int64_t notes = 0;
        for (int i = 0; i < 40000; i++) {
            const uint64_t r = rng();
            if (r % 97 == 0) rec_value++;   // (a new recording)
            const int k = (int)((r >> 8) % 8);
            for (int n = 1 + (int)((r >> 32) % 6); n--;) {   // (a range bound by one draw after another, a few times)
                texture_gpu_wrote(los[k] + ((r >> 16) % 5 == 0 ? 0x40 : 0), sizes[(k + (r >> 24) % 2) % 8]);
                notes++;
            }
            for (const auto& [lo, e] : gpu_wrote) h = mix(mix(mix(h, lo), e.first), e.second);
            h = mix(h, gpu_wrote.size());
        }
        std::printf("%016llx %lld %lld\n", (unsigned long long)h, (long long)gpu_wrote_mu.n, (long long)notes);
        return 0;
    }
    if (what == "stamp") {   // (every reader's answer, in order)
        struct Kept { uint64_t guest, size; uint32_t gen; };
        std::vector<Kept> kept;
        const uint64_t guests[] = {0x1000, 0x1800, 0x3000, 0x8000, 0x8000, 0xC000};
        const uint64_t sizes[] = {0x100, 0x2000, 0x1000, 0x40, 0x3000, 0x800};
        for (int i = 0; i < 40000; i++) {
            const uint64_t r = rng();
            const int k = (int)((r >> 8) % 6);
            const int op = (int)(r % 100);
            if (op < 55) memory_stamp_gpu(guests[k], sizes[k]);                  // (a draw's written storage buffer)
            else if (op < 62) memory_stamp(guests[(k + 1) % 6], sizes[(k + 3) % 6]);   // (another write)
            else if (op < 72) kept.push_back({guests[k], sizes[(k + 2) % 6], memory_generation()});   // (a reader keeps one)
            else if (op < 75) take_capture(guests[(k + 4) % 6], sizes[k]);
            else {
                for (const Kept& q : kept) h = mix(h, written_since(q.guest, q.size, q.gen));
                for (const auto& [p, g] : cap_entry) h = mix(h, page_gen[p] == g);   // (the capture's copy stands)
                if (kept.size() > 64) kept.erase(kept.begin());
            }
        }
        std::printf("%016llx %lld\n", (unsigned long long)h, (long long)stamps);
        return 0;
    }
    return 2;
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    cxx = shutil.which(args.cxx)
    if not cxx:
        raise SystemExit("C++ compiler not found: " + args.cxx)
    memory = (ROOT / "gpu" / "vk" / "vk_memory.cpp").read_text(encoding="utf-8")
    texture = (ROOT / "gpu" / "vk" / "vk_texture.cpp").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "development.md").read_text(encoding="utf-8")

    # ---- the sources: who moves the fence ----
    if "`RX_VK_WRITTEN_EACH=1`" not in docs:
        raise SystemExit("FAIL: docs/development.md does not list RX_VK_WRITTEN_EACH")
    gen = block(memory, "uint32_t memory_generation() {")
    if "stamp_fence_bump();" not in gen or gen.index("stamp_fence_bump();") > gen.index("return gen_now;"):
        raise SystemExit("FAIL: memory_generation hands out a generation without moving the stamps' fence")
    stamp = block(memory, "void memory_stamp_gpu(uint64_t guest, uint64_t size) {")
    for needle in ('env_on("RX_VK_WRITTEN_EACH")', "!gpu_pages_on()", "stamp_seen_hit(seen, guest, size, fence)"):
        if needle not in stamp:
            raise SystemExit("FAIL: memory_stamp_gpu's memo no longer has: " + needle)
    if not stamp.index("stamp_fence.load(") < stamp.index("stamp_seen_hit(") < stamp.index("memory_stamp(guest, size);") \
            < stamp.index("seen = {guest, size, fence};"):
        raise SystemExit("FAIL: memory_stamp_gpu reads the fence after its stamp, or keeps the range before it")
    # (every generation a reader keeps (a pool's sync, a protected page), but the GPU pages' diagnostic table, which only asks
    # whether a page is in it: the fence moves in that function)
    keeps = [m.start() for m in re.finditer(r"=\s*gen_now;", memory)]
    if len(keeps) < 4:
        raise SystemExit("FAIL: fewer generations kept than this test knows of: update it")
    for at in keeps:
        line = memory[memory.rindex("\n", 0, at) + 1:memory.index("\n", at)]
        if "gpu_pages[(uint32_t)p] = gen_now;" in line:
            continue
        head = max(memory.rfind("\n}\n", 0, at), memory.rfind("\n    }\n", 0, at))   # (its function, or its block)
        tail = memory.index("\n}\n", at)
        if "stamp_fence_bump();" not in memory[head:tail]:
            raise SystemExit("FAIL: a generation is kept without moving the stamps' fence: " + line.strip())
    take = block(memory, "bool take_capture(std::unique_ptr<Capture> c, uint64_t value, uint64_t completed) {")
    if "stamp_fence_bump();" not in take or take.index("stamp_fence_bump();") > take.index("g = ++gen_now;"):
        raise SystemExit("FAIL: a capture gives pages entries of its own generation without moving the stamps' fence first")
    # (the map of GPU writes changes in texture_gpu_wrote only, which counts each change)
    note = block(texture, "void texture_gpu_wrote(uint64_t gpu, uint64_t size) {")
    rest = texture.replace(note, "")
    for change in ("gpu_wrote[", "gpu_wrote.erase(", "gpu_wrote.clear(", "gpu_wrote.emplace(", "gpu_wrote.insert("):
        if change in rest:
            raise SystemExit("FAIL: the map of GPU writes changes outside texture_gpu_wrote: " + change)
    if note.count("gpu_wrote_changes.fetch_add(") != 2:
        raise SystemExit("FAIL: texture_gpu_wrote changes the map without counting it")

    # ---- the code cut out, run ----
    seen = cut(texture, "std::atomic<uint64_t> gpu_wrote_changes{0};", "}  // namespace\nbool gpu_wrote_into(Texture& tex);")
    if "65536" not in note:
        raise SystemExit("FAIL: texture_gpu_wrote's bound is not where this test makes it small")
    note_small = note.replace("65536", "6")   # (its evictions run in a short sequence)
    fence = cut(memory, "std::atomic<uint64_t> stamp_fence{1};", "} // namespace\nvoid memory_stamp_gpu(")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    env = dict(os.environ)
    env["PATH"] = str(Path(cxx).parent) + os.pathsep + env.get("PATH", "")
    env.pop("RX_VK_WRITTEN_EACH", None)
    with tempfile.TemporaryDirectory(prefix="written-once-") as folder:
        tmp = Path(folder)
        (tmp / "fixture.cpp").write_text(FIXTURE, encoding="utf-8")

        def build(name, seen_text, note_text, fence_text):
            (tmp / "gpu_wrote_seen.inc").write_text(seen_text + "\n", encoding="utf-8")
            (tmp / "texture_gpu_wrote.inc").write_text(note_text + "\n", encoding="utf-8")
            (tmp / "stamp_seen.inc").write_text(fence_text + "\n", encoding="utf-8")
            (tmp / "stamp_gpu.inc").write_text(stamp + "\n", encoding="utf-8")
            exe = tmp / (name + (".exe" if os.name == "nt" else ""))
            r = subprocess.run([cxx, "-std=c++20", "-include", ENV_ON_H, "-O1", "-Wall", "-Wextra", "-Werror",
                                "-Wno-unused-function", "-D_CRT_SECURE_NO_WARNINGS", "-I" + str(tmp), str(tmp / "fixture.cpp"),
                                "-o", str(exe)] + ([] if os.name == "nt" else ["-pthread"]),
                               capture_output=True, text=True, timeout=180, env=env, creationflags=flags)
            if r.returncode:
                print(r.stdout + r.stderr)
                raise SystemExit("FAIL: the code cut out does not build in this test's fixture")
            return exe

        def run(exe, what, each):
            e = dict(env)
            if each:
                e["RX_VK_WRITTEN_EACH"] = "1"
            r = subprocess.run([str(exe), what], capture_output=True, text=True, timeout=60, env=e, creationflags=flags)
            if r.returncode:
                raise SystemExit("FAIL: the fixture stopped (%s): %s" % (what, r.stdout + r.stderr))
            return r.stdout.split()

        actual = build("actual", seen, note_small, fence)
        wrote_each, wrote_once = run(actual, "wrote", True), run(actual, "wrote", False)
        if wrote_each[0] != wrote_once[0]:
            raise SystemExit("FAIL: the map of GPU writes differs with notes left out (%s against %s)" % (wrote_once[0], wrote_each[0]))
        if int(wrote_each[1]) != int(wrote_each[2]) or int(wrote_once[1]) >= int(wrote_each[1]):
            raise SystemExit("FAIL: no note was left out: %s locks against %s, of %s notes" % (wrote_once[1], wrote_each[1], wrote_each[2]))
        print("PASS: the map of GPU writes is the same with %s of %s notes under the lock (RX_VK_WRITTEN_EACH=1: every one)"
              % (wrote_once[1], wrote_each[2]))
        stamp_each, stamp_once = run(actual, "stamp", True), run(actual, "stamp", False)
        if stamp_each[0] != stamp_once[0]:
            raise SystemExit("FAIL: a reader's answer differs with stamps left out (%s against %s)" % (stamp_once[0], stamp_each[0]))
        if int(stamp_once[1]) >= int(stamp_each[1]):
            raise SystemExit("FAIL: no stamp was left out: %s against %s" % (stamp_once[1], stamp_each[1]))
        print("PASS: every reader's answer is the same with %s stamps against %s (RX_VK_WRITTEN_EACH=1)" % (stamp_once[1], stamp_each[1]))

        # (a memo that does not look at what moved answers differently: the sequences can tell)
        loose = build("loose", seen.replace("s.value == value && s.changes == changes", "((void)value, (void)changes, true)"), note_small,
                      fence.replace("s.fence == fence", "((void)fence, true)"))
        if run(loose, "wrote", False)[0] == wrote_each[0]:
            raise SystemExit("FAIL: a note memo blind to the recording and the map leaves the same map: this test cannot tell")
        if run(loose, "stamp", False)[0] == stamp_each[0]:
            raise SystemExit("FAIL: a stamp memo blind to the fence gives the same answers: this test cannot tell")
        print("PASS: a memo blind to the recording, the map's changes or the fence is caught")


if __name__ == "__main__":
    main()
