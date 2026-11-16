"""A draw does not bind vertex streams or an index buffer already on the command buffer.

A direct indexed draw binds its index buffer at the buffer's start and counts its offset in indices as its first index
(index_bind_base), so that the submeshes of one pool keep one binding: the indices it reads are at the addresses the bind
at its own offset read, inside robust access's bounds exactly when they were. An indirect one binds at its own offset: the
GPU-written records' first indices count from there.

python -I -B tests/test_draw_binds.py [--cxx g++]
"""
import argparse
import subprocess
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))   # (tests/srccut.py: python -I leaves this folder off the path)
from srccut import block   # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cxx", default="g++")
    a = p.parse_args()
    source = (ROOT / "gpu" / "vk" / "vk_draw.cpp").read_text(encoding="utf-8")
    draw = block(source, "void draw(")
    streams = draw.index("for (uint32_t b = 0; b < 16; b++)")
    if draw.index("vertex_set_same(") > streams:
        raise SystemExit("vertex streams are looked up before checking the set already bound")
    if "vertex_set.on = false" not in draw:
        raise SystemExit("a vertex set is remembered when a stream did not bind")
    if "vsize[i] ? vsize[i] : 1" not in draw:
        raise SystemExit("a vertex set remembers an empty size as empty")
    if "gpu_bind_stamp() == vstamp" not in draw:
        raise SystemExit("a vertex set is remembered across a mirror")
    if draw.count("bind_index(") != 3:
        raise SystemExit("an indexed draw binds its index buffer on its own")
    bound = block(source, "void bind_index(")
    if bound.index("index_bind_same(") > bound.index("vkCmdBindIndexBuffer("):
        raise SystemExit("an index buffer is bound before checking it is already bound")
    if source.count("vkCmdBindIndexBuffer(") != 1:
        raise SystemExit("an index buffer is bound from more than one place")
    if bound.index("index_bind_same(") > bound.index("FINE_N(FC_IBIND_CMDS, 1);") or \
            bound.index("FINE_N(FC_IBIND_CMDS, 1);") > bound.index("vkCmdBindIndexBuffer("):
        raise SystemExit("the index bind commands are not counted where one is recorded")
    # (the direct indexed draw: bound at index_bind_base's base, from the first index it gave; the indirect one at its own
    # offset)
    direct = draw[draw.index("    } else if (d.indexed) {"):]
    direct = direct[:direct.index("    } else {")]
    if draw.count("index_bind_base(") != 1 or "bind_index(cmd, ib.buffer, index_bind_base(ib.offset, unit, (uint32_t)d.count, " \
            "!at_offset, &first), itype);" not in direct:
        raise SystemExit("a direct indexed draw is not bound at index_bind_base's base")
    if "vkCmdDrawIndexed(cmd, (uint32_t)d.count, (uint32_t)std::max(1, d.instances), first, " not in direct:
        raise SystemExit("a direct indexed draw does not draw from the first index index_bind_base gave")
    if 'env_on("RX_VK_INDEX_AT_OFFSET")' not in direct:
        raise SystemExit("RX_VK_INDEX_AT_OFFSET (the A/B: bound at each draw's offset) is not read")
    indirect = draw[draw.index("    if (d.indirect) {"):draw.index("    } else if (d.indexed) {")]
    if "bind_index(cmd, ib.buffer, ib.offset, itype);" not in indirect:
        raise SystemExit("an indirect indexed draw is not bound at its own offset")
    base = block(source, "uint64_t index_bind_base(")
    begin = block(source, "void draw_begin_recording(")
    if "vertex_set.on = false" not in begin or "last_ib.on = false" not in begin:
        raise SystemExit("a new command buffer keeps the vertex set and index buffer of the last one")
    verts = block(source, "bool vertex_set_same(")
    index = block(source, "bool index_bind_same(")
    fixture = f'''#include <cstdint>
#include <cstdio>
#include <cstdlib>
#define CHECK(x) do {{ if (!(x)) {{ std::fprintf(stderr, "FAIL:%d %s\\n", __LINE__, #x); std::exit(1); }} }} while (0)
{verts}
{index}
{base}
// (an index read as Vulkan makes it: at bound + (first + i) * unit; with robust access, in bounds while the index lies
// inside [bound, size) of the buffer, whole)
struct Fetch {{ uint64_t at; bool in; }};
Fetch fetch(uint64_t bound, uint32_t first, uint32_t i, uint32_t unit, uint64_t size) {{
    const uint64_t at = bound + ((uint64_t)first + i) * unit;
    return {{at, bound <= size && ((uint64_t)first + i) < (size - bound) / unit}};
}}
// (a draw's reads bound at its own offset, as before, and at index_bind_base's: the same, in bounds or out alike)
void same_reads(uint64_t offset, uint32_t unit, uint32_t count, uint64_t size) {{
    uint32_t first = 7;
    const uint64_t bound = index_bind_base(offset, unit, count, 1, &first);
    CHECK(bound == 0 ? offset % unit == 0 : bound == offset && first == 0);   // (moved only from an aligned offset)
    CHECK((uint64_t)first + count <= UINT32_MAX);
    const uint32_t step = count > 64 ? count / 61 : 1;
    for (uint64_t i = 0; i < count; i += step) {{
        const Fetch a = fetch(offset, 0, (uint32_t)i, unit, size), b = fetch(bound, first, (uint32_t)i, unit, size);
        CHECK(a.at == b.at && a.in == b.in);
    }}
    if (count) {{
        const Fetch a = fetch(offset, 0, count - 1, unit, size), b = fetch(bound, first, count - 1, unit, size);
        CHECK(a.at == b.at && a.in == b.in);
    }}
}}
int main() {{
    uint64_t addr[16]{{}}, size[16]{{}}, caddr[16]{{}}, csize[16]{{}};
    uint32_t stride[16]{{}}, cstride[16]{{}};
    addr[0] = 0x1000; size[0] = 64; stride[0] = 12;
    caddr[0] = 0x1000; csize[0] = 64; cstride[0] = 12;
    CHECK(vertex_set_same(3, addr, size, stride, 3, caddr, csize, cstride, 1));
    CHECK(!vertex_set_same(4, addr, size, stride, 3, caddr, csize, cstride, 1));
    CHECK(!vertex_set_same(3, addr, size, stride, 3, caddr, csize, cstride, 0));
    stride[0] = 16;
    CHECK(!vertex_set_same(3, addr, size, stride, 3, caddr, csize, cstride, 1));
    stride[0] = 12;
    caddr[2] = 0x2000;
    CHECK(!vertex_set_same(3, addr, size, stride, 3, caddr, csize, cstride, 1));
    caddr[2] = 0;
    size[0] = 0; csize[0] = 1;
    CHECK(vertex_set_same(3, addr, size, stride, 3, caddr, csize, cstride, 1));
    csize[0] = 0;
    CHECK(!vertex_set_same(3, addr, size, stride, 3, caddr, csize, cstride, 1));
    size[0] = 64; csize[0] = 64;
    addr[15] = 0x9999;
    CHECK(vertex_set_same(3, addr, size, stride, 3, caddr, csize, cstride, 1));
    addr[15] = 0;
    CHECK(index_bind_same(0x10, 32, 1, 0x10, 32, 1, 1));
    CHECK(!index_bind_same(0x10, 64, 1, 0x10, 32, 1, 1));
    CHECK(!index_bind_same(0x10, 32, 2, 0x10, 32, 1, 1));
    CHECK(!index_bind_same(0x20, 32, 1, 0x10, 32, 1, 1));
    CHECK(!index_bind_same(0x10, 32, 1, 0x10, 32, 1, 0));
    CHECK(!index_bind_same(0, 0, 1, 0, 0, 1, 1));
    // index_bind_base: at the buffer's start, the offset in indices as the first index
    uint32_t first = 7;
    CHECK(index_bind_base(0x1230, 2, 300, 1, &first) == 0 && first == 0x1230 / 2);
    CHECK(index_bind_base(0x1230, 4, 300, 1, &first) == 0 && first == 0x1230 / 4);
    CHECK(index_bind_base(0x1231, 1, 300, 1, &first) == 0 && first == 0x1231);
    CHECK(index_bind_base(0, 4, 300, 1, &first) == 0 && first == 0);
    // (else at the offset, from index 0, as before: an offset no multiple of the index size, past 32 bits, or off)
    CHECK(index_bind_base(0x1231, 2, 300, 1, &first) == 0x1231 && first == 0);
    CHECK(index_bind_base(0x1232, 4, 300, 1, &first) == 0x1232 && first == 0);
    CHECK(index_bind_base(0x1230, 2, 300, 0, &first) == 0x1230 && first == 0);
    CHECK(index_bind_base(0x1230, 0, 300, 1, &first) == 0x1230 && first == 0);
    CHECK(index_bind_base((uint64_t)(UINT32_MAX - 300) * 4, 4, 300, 1, &first) == 0 && first == UINT32_MAX - 300);
    CHECK(index_bind_base((uint64_t)(UINT32_MAX - 299) * 4, 4, 300, 1, &first) == (uint64_t)(UINT32_MAX - 299) * 4 && first == 0);
    CHECK(index_bind_base(1ull << 36, 2, 300, 1, &first) == 1ull << 36 && first == 0);
    CHECK(index_bind_base(0x40, 2, UINT32_MAX, 1, &first) == 0x40 && first == 0);   // (a count from a negative one)
    CHECK(index_bind_base(0, 2, UINT32_MAX, 1, &first) == 0 && first == 0);
    // (the same indices read, and robust access's bounds alike: inside the buffer, across its end, wholly past it, at the
    // edge of 32 bits)
    const uint64_t offsets[] = {{0, 4, 0x1230, 0x1231, 0x1232, 0xFFF0, 0x10000, (1ull << 32) - 8, 1ull << 33}};
    const uint32_t units[] = {{1, 2, 4}}, counts[] = {{0, 1, 3, 300, 0x8000, 1u << 24}};
    for (uint32_t unit : units)
        for (uint64_t offset : offsets)
            for (uint32_t count : counts) {{
                const uint64_t end = offset + (uint64_t)count * unit;
                const uint64_t sizes[] = {{0x800, 0x10000, 0x10006, offset + 0x101, end, end ? end - 1 : 0, 1ull << 30, 1ull << 34}};
                for (uint64_t size : sizes) same_reads(offset, unit, count, size);
            }}
    // (one pool's submeshes, each at an offset of its own: bound once, where each at its own offset was a bind)
    struct {{ uint64_t buffer, offset; uint32_t type; bool on; }} at{{}}, own{{}};
    int binds_at = 0, binds_own = 0;
    const uint64_t submesh[][2] = {{{{0x10, 0x400}}, {{0x10, 0x9a0}}, {{0x10, 0x1f00}}, {{0x10, 0x9a0}}, {{0x20, 0x80}}, {{0x20, 0x300}},
                                    {{0x10, 0x400}}, {{0x10, 0x6000}}}};
    for (const auto& m : submesh) {{
        const uint64_t base = index_bind_base(m[1], 2, 96, 1, &first);
        if (!index_bind_same(m[0], base, 1, at.buffer, at.offset, at.type, at.on)) binds_at++, at = {{m[0], base, 1, true}};
        if (!index_bind_same(m[0], m[1], 1, own.buffer, own.offset, own.type, own.on)) binds_own++, own = {{m[0], m[1], 1, true}};
    }}
    CHECK(binds_own == 8 && binds_at == 3);
    std::printf("PASS: a draw keeps the vertex set and index buffer already bound; one pool's submeshes keep one\\n");
}}
'''
    with tempfile.TemporaryDirectory(prefix="draw-binds-") as tmp:
        cpp = Path(tmp) / "fixture.cpp"
        exe = Path(tmp) / "fixture"
        cpp.write_text(fixture, encoding="utf-8")
        subprocess.run([a.cxx, "-std=c++20", "-Wall", "-Wextra", "-Werror", str(cpp), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    main()
