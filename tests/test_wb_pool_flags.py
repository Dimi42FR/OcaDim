"""A written binding's write-back is left out (RX_VK_WB_MAX_KB) only in pools the CPU cannot read without an invalidate.

NVN's CPU-cached pools need nvnMemoryPoolInvalidateMappedRange before the CPU reads what the GPU wrote, and the renderer hears
each one (the learned leave-out, wb_learn.h, keeps those ranges written back); pools with no CPU access are never read. Uncached
pools are read with no call, so a left-out write-back there was found stale with nothing to learn from. The pools' flags come
from nvnMemoryPoolInitialize through rx_nvn_pool_created (MKWVK_API_VERSION 24) into gpu/vk/wb_pool_flags.h's map, which
wb_leave_out asks before the table.

The map's rules are compiled and run (the access a flag set gives, a pool made over an older one's range, ranges across pools
and gaps), and the wiring from the host to wb_leave_out is checked in the source. No GPU or game.

python -I -B tests/test_wb_pool_flags.py [--cxx clang++] [--source /path/to/source/tree]
"""
import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path

RUN_ALL_ARGS = ["--cxx", "{cxx}"]

ROOT = Path(__file__).resolve().parents[1]


def block(text, marker):
    if text.count(marker) != 1:
        raise SystemExit("marker not found once: " + marker)
    start = text.index(marker)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def need(where, text, needles):
    for needle in needles:
        if needle not in text:
            raise SystemExit(where + " no longer has: " + needle)


def check_source(src):
    native = (src / "host/nvn_native.c").read_text(encoding="utf-8")
    backend = (src / "host/rx_backend.c").read_text(encoding="utf-8")
    api = (src / "gpu/vk/vk_api.h").read_text(encoding="utf-8")
    mem = (src / "gpu/vk/vk_memory.cpp").read_text(encoding="utf-8")
    need("host/nvn_native.c: nvnMemoryPoolInitialize", block(native, "NV(nvnMemoryPoolInitialize)"),
         ["rx_nvn_pool_created(o->gpu, o->size, o->flags);"])
    need("host/rx_backend.c: rx_nvn_pool_created", block(backend, "void rx_nvn_pool_created("),
         ["vk->nvn_pool_created(gpu, size, flags);"])
    need("gpu/vk/vk_api.h", api, ["void (*nvn_pool_created)(uint64_t gpu, uint64_t size, uint32_t flags);"])
    if int(re.search(r"#define MKWVK_API_VERSION (\d+)", api).group(1)) < 24:
        raise SystemExit("gpu/vk/vk_api.h: nvn_pool_created changed without MKWVK_API_VERSION 24")
    need("vk_memory.cpp: memory_pool_created()", block(mem, "void memory_pool_created(uint64_t gpu, uint64_t size, uint32_t flags)"),
         ["pool_flags.add(gpu, gpu + size, flags);"])
    leave = block(mem, "bool wb_leave_out(uint64_t lo, uint64_t hi")
    need("vk_memory.cpp: wb_leave_out()", leave, ["if (!wb_any_pool() && hi - lo > wb_cap())", "pool_flags.may_leave_out(lo, hi)"])
    if leave.index("pool_flags.may_leave_out") > leave.index("wb_table.plan("):
        raise SystemExit("vk_memory.cpp: wb_leave_out() asks the table before the pool's flags: an uncached pool's binding could be left out")
    need("vk_memory.cpp: the write-back's runs", mem, ["wb_access_note(p->lo + r.dstOffset, r.size);"])


FIXTURE = r'''
#include <cstdio>
#include "wb_pool_flags.h"
using namespace wb_pool_flags;
int failed = 0;
#define CHECK(c) do { if (!(c)) { std::printf("FAIL line %d: %s\n", __LINE__, #c); failed++; } } while (0)
int main() {
    // the flag sets OoT makes its pools with (Kokiri Forest)
    CHECK(access_of(0x24) == kCached);     // CPU_CACHED | GPU_CACHED: most pools
    CHECK(access_of(0x64) == kCached);     // and SHADER_CODE
    CHECK(access_of(0x22) == kUncached);   // CPU_UNCACHED | GPU_CACHED
    CHECK(access_of(0x12) == kUncached);
    CHECK(access_of(0x62) == kUncached);
    CHECK(access_of(0x21) == kNoAccess);   // CPU_NO_ACCESS | GPU_CACHED
    CHECK(access_of(0xa1) == kNoAccess);   // and COMPRESSIBLE
    CHECK(access_of(0x18c) == kCached);    // PHYSICAL | COMPRESSIBLE | GPU_NO_ACCESS | CPU_CACHED
    CHECK(access_of(0x20) == kUnknown);    // no CPU bit: not left out
    CHECK(access_of(0x6) == kUncached);    // both bits: uncached wins

    Map m;
    CHECK(!m.may_leave_out(0x1000, 0x2000));   // nothing known
    m.add(0x10000, 0x20000, 0x24);
    CHECK(m.may_leave_out(0x10000, 0x20000));
    CHECK(m.may_leave_out(0x18000, 0x19000));
    CHECK(!m.may_leave_out(0x0f000, 0x11000));   // starts before it
    CHECK(!m.may_leave_out(0x1f000, 0x21000));   // ends past it
    // a neighbour: across both
    m.add(0x20000, 0x30000, 0x21);
    CHECK(m.range(0x18000, 0x28000) == kCached);
    CHECK(m.range(0x20000, 0x30000) == kNoAccess);
    // an uncached one beside: a binding over the edge is kept
    m.add(0x30000, 0x31000, 0x22);
    CHECK(!m.may_leave_out(0x2f000, 0x30800));
    CHECK(m.range(0x30000, 0x31000) == kUncached);
    // a gap between two known pools
    m.add(0x40000, 0x50000, 0x24);
    CHECK(m.range(0x31000, 0x41000) == kUnknown);
    // a pool made over part of an older one's range takes that part; the older one keeps the rest
    m.add(0x14000, 0x16000, 0x22);
    CHECK(m.range(0x10000, 0x14000) == kCached);
    CHECK(m.range(0x14000, 0x16000) == kUncached);
    CHECK(m.range(0x16000, 0x20000) == kCached);
    CHECK(!m.may_leave_out(0x10000, 0x20000));
    // and one made over the whole of it, cached again
    m.add(0x10000, 0x20000, 0x24);
    CHECK(m.may_leave_out(0x10000, 0x20000));
    CHECK(m.size() == 4);
    // one over several: all of them replaced
    m.add(0x0, 0x60000, 0x22);
    CHECK(m.size() == 1);
    CHECK(m.range(0x48000, 0x49000) == kUncached);
    CHECK(m.range(0x5f000, 0x61000) == kUncached);   // (its first part uncached: kept, whatever follows)
    CHECK(m.range(0x60000, 0x61000) == kUnknown);
    CHECK(!m.may_leave_out(0x5f000, 0x61000));
    // empty and inverted ranges
    CHECK(m.range(0x100, 0x100) == kUnknown);
    CHECK(!m.may_leave_out(0x200, 0x100));
    std::printf(failed ? "FAIL: %d checks\n" : "ok: the pools' CPU access\n", failed);
    return failed ? 1 : 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default="clang++")
    parser.add_argument("--source", type=Path, default=ROOT)
    args = parser.parse_args()
    check_source(args.source)
    with tempfile.TemporaryDirectory(prefix="wb-pool-flags-") as tmp:
        folder = Path(tmp)
        (folder / "fixture.cpp").write_text(FIXTURE, encoding="utf-8")
        exe = folder / "fixture.exe"
        cmd = [args.cxx, "-std=c++20", "-O1", "-w", "-I" + str(args.source / "gpu/vk"), str(folder / "fixture.cpp"), "-o", str(exe)]
        if os.name == "nt":
            cmd.append("-static")   # (the fixture runs without the toolchain's runtime DLLs on PATH)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.returncode:
            print(r.stdout + r.stderr)
            raise SystemExit("the fixture did not build")
        r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
        print(r.stdout, end="")
        if r.returncode:
            raise SystemExit("FAIL: the pools' CPU access")
    print("PASS: write-backs are left out only in pools the CPU reads after an invalidate or not at all; the flags reach "
          "wb_leave_out from nvnMemoryPoolInitialize")


if __name__ == "__main__":
    main()
