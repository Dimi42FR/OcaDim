"""A stage's descriptors are kept for the next build of its program only while what they were resolved from stands.

gpu/vk/vk_draw.cpp build_descriptors keeps, per program and stage, the textures (a stage whose handles are all words of its
own c2), the storage buffers (a stage whose buffers are all read only and named in c0 or c1) and each c1 or user uniform
buffer (bound where it is, no update over it) as the last build in the same recording part resolved them (desc_kept).

First the keys and the stage rules are cut out of the source and compiled alone: a kept segment holds with the same key,
and not once any one of its parts moves (the state, the recording part, the texture destroy generation, the samplers'
registrations, the texture epoch, a slot's version; a dummy handle's registrations; the stage's c0 table, the pools and the
game's pool table; a uniform buffer's range, the stream's updates and the pools); written storage buffers, handles through a
handle program or from another bank, and compute, task and mesh stages are never kept. Then the source is read for the
rules the build keeps around them: what resolving does besides (Descriptor reuse's handles, the GPU-written textures
sampled, the dummy count) is done again from what was kept; a kept texture segment through new bindings is used only with
the same handles; nothing is kept that was resolved while the pools changed, or with a sampler not made; storage images,
texel buffers and stream copies of uniform ranges are never kept; a recording part's start drops it all; RX_VK_DESC_KEEP=0,
RX_VK_DESC_REUSE=never, a dump and the per-descriptor diagnostics turn it off.

python -I -B tests/test_desc_keep.py [--cxx g++]
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

RUN_ALL_ARGS = ["--cxx", "{cxx}"]

ROOT = Path(__file__).resolve().parents[1]

FIXTURE = r"""
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr, "FAIL:%d %s\n", __LINE__, #x); std::exit(1); } } while (0)

namespace Shader {
struct TextureDescriptor { uint32_t handle_program = ~0U, cbuf_index = 2, secondary_cbuf_index = 2, count = 1; bool has_secondary = false; };
struct StorageBufferDescriptor { uint32_t cbuf_index = 0, cbuf_offset = 0x110, count = 1; bool is_written = false; };
struct Info {
    std::vector<TextureDescriptor> texture_descriptors;
    std::vector<StorageBufferDescriptor> storage_buffers_descriptors;
};
}  // namespace Shader
struct Stage { int nvn_stage = 1; Shader::Info info; };
struct NvnState { int unused; };
uint32_t versions[16];
uint32_t texture_slot_version(int id) { return versions[id & 15]; }

@CODE@

int main() {
    NvnState a{}, b{};
    // (textures: every part of the key but tex_gen, which the build checks by reading the handles again)
    const KeptTexKey t{&a, 7, 100, 3, 4, 5, 9, false};
    CHECK(kept_tex_holds(t, t));
    { KeptTexKey n = t; n.tex_gen = 101; CHECK(kept_tex_holds(t, n)); }
    { KeptTexKey n = t; n.s = &b; CHECK(!kept_tex_holds(t, n)); }
    { KeptTexKey n = t; n.part = 8; CHECK(!kept_tex_holds(t, n)); }
    { KeptTexKey n = t; n.dgen = 4; CHECK(!kept_tex_holds(t, n)); }
    { KeptTexKey n = t; n.samp = 5; CHECK(!kept_tex_holds(t, n)); }
    { KeptTexKey n = t; n.epoch = 10; CHECK(!kept_tex_holds(t, n)); }
    { KeptTexKey n = t; n.reg = 6; CHECK(kept_tex_holds(t, n)); }   // (no dummy handle: a registration elsewhere does not matter)
    { KeptTexKey d = t; d.dummy = true; KeptTexKey n = d; n.reg = 6; CHECK(kept_tex_holds(d, d)); CHECK(!kept_tex_holds(d, n)); }
    // (the slots the handles named)
    versions[2] = 5, versions[3] = 1;
    std::vector<uint64_t> fp{(uint64_t)5 << 20 | 2, (uint64_t)1 << 20 | 3};
    CHECK(kept_slots_hold(fp));
    versions[3] = 2;
    CHECK(!kept_slots_hold(fp));
    // (storage buffers)
    const KeptBufKey s{&a, 7, 40, 0x1234, 11};
    CHECK(kept_buf_holds(s, s));
    { KeptBufKey n = s; n.s = &b; CHECK(!kept_buf_holds(s, n)); }
    { KeptBufKey n = s; n.part = 8; CHECK(!kept_buf_holds(s, n)); }
    { KeptBufKey n = s; n.ssbo_gen = 41; CHECK(!kept_buf_holds(s, n)); }
    { KeptBufKey n = s; n.stamp = 0x1235; CHECK(!kept_buf_holds(s, n)); }
    { KeptBufKey n = s; n.pools = 12; CHECK(!kept_buf_holds(s, n)); }
    // (uniform buffers: a user one by its range, the updates and the pools; c1 by the part alone)
    KeptUboKey u;
    u.on = true, u.part = 7, u.addr = 0x10000, u.size = 0x100, u.ub_gen = 3, u.ub_list = 4, u.stamp = 5;
    CHECK(kept_ubo_holds(u, u, false));
    { KeptUboKey off = u; off.on = false; CHECK(!kept_ubo_holds(off, u, false)); CHECK(!kept_ubo_holds(off, u, true)); }
    { KeptUboKey n = u; n.part = 8; CHECK(!kept_ubo_holds(u, n, false)); CHECK(!kept_ubo_holds(u, n, true)); }
    { KeptUboKey n = u; n.addr = 0x10100; CHECK(!kept_ubo_holds(u, n, false)); }
    { KeptUboKey n = u; n.size = 0x200; CHECK(!kept_ubo_holds(u, n, false)); }
    { KeptUboKey n = u; n.ub_gen = 4; CHECK(!kept_ubo_holds(u, n, false)); CHECK(kept_ubo_holds(u, n, true)); }
    { KeptUboKey n = u; n.ub_list = 5; CHECK(!kept_ubo_holds(u, n, false)); CHECK(kept_ubo_holds(u, n, true)); }
    { KeptUboKey n = u; n.stamp = 6; CHECK(!kept_ubo_holds(u, n, false)); CHECK(kept_ubo_holds(u, n, true)); }
    // (which stages keep their textures)
    Stage st;
    CHECK(!desc_keep_textures(st));   // (none to keep)
    st.info.texture_descriptors.resize(3);
    CHECK(desc_keep_textures(st));
    for (int ns : {-1, 5, 6, 7}) { Stage o = st; o.nvn_stage = ns; CHECK(!desc_keep_textures(o)); }
    for (int ns : {0, 2, 3, 4}) { Stage o = st; o.nvn_stage = ns; CHECK(desc_keep_textures(o)); }
    { Stage o = st; o.info.texture_descriptors[1].handle_program = 0; CHECK(!desc_keep_textures(o)); }
    { Stage o = st; o.info.texture_descriptors[2].cbuf_index = 3; CHECK(!desc_keep_textures(o)); }
    { Stage o = st; o.info.texture_descriptors[0].has_secondary = true; CHECK(desc_keep_textures(o)); }
    { Stage o = st; o.info.texture_descriptors[0].has_secondary = true, o.info.texture_descriptors[0].secondary_cbuf_index = 1; CHECK(!desc_keep_textures(o)); }
    // (which keep their storage buffers)
    Stage sb;
    CHECK(!desc_keep_storage(sb));
    sb.info.storage_buffers_descriptors.resize(2);
    sb.info.storage_buffers_descriptors[1].cbuf_index = 1;
    CHECK(desc_keep_storage(sb));
    for (int ns : {-1, 5, 6, 7}) { Stage o = sb; o.nvn_stage = ns; CHECK(!desc_keep_storage(o)); }
    { Stage o = sb; o.info.storage_buffers_descriptors[0].is_written = true; CHECK(!desc_keep_storage(o)); }
    { Stage o = sb; o.info.storage_buffers_descriptors[1].cbuf_index = 4; CHECK(!desc_keep_storage(o)); }
    { Stage o = sb; o.info.storage_buffers_descriptors[0].cbuf_offset = 0xff0; CHECK(!desc_keep_storage(o)); }
    { Stage o = sb; o.info.storage_buffers_descriptors[0].cbuf_offset = 0xff0, o.info.storage_buffers_descriptors[0].count = 2; CHECK(desc_keep_storage(o)); }
    std::printf("ok: a kept stage's keys and rules\n");
    return 0;
}
"""


def block(text, marker):
    start = text.index(marker)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def need(cond, why):
    if not cond:
        raise SystemExit("desc_kept: " + why)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cxx", default="g++")
    a = p.parse_args()
    src = (ROOT / "gpu" / "vk" / "vk_draw.cpp").read_text(encoding="utf-8")
    build = block(src, "void build_descriptors(const NvnState& s, const Program& p) {")
    # (what is kept is looked up per program, and only for a program that is whole, with the switch on and no dump running)
    kept = block(src, "KeptProgram* kept_program(const Program& p) {")
    need('getenv("RX_VK_DESC_KEEP")' in kept and "env_value_off(e)" in kept, "RX_VK_DESC_KEEP=0 does not turn it off")
    need("desc_reuse_level() != 0" in kept, "RX_VK_DESC_REUSE=never does not turn it off")
    need("dump_on()" in kept and "p.ready.load(std::memory_order_acquire)" in kept, "kept during a dump, or for a program not whole")
    for name in ("RX_VK_TRACE_TEX", "RX_VK_LOG_IMG", "RX_VK_WATCH_PROG", "RX_VK_DRAW_STATS", "RX_VK_PEEK_PROG", "RX_VK_ASYNC_IMPORT"):
        need(name in kept, name + " (a diagnostic of each descriptor, or stream copies of read binds) leaves it on")
    need("k.p != &p || k.key != p.key || k.stages.size() != p.stages.size()" in kept, "another program's kept stages are used")
    need("kept_program(p)" in build, "build_descriptors does not look up what was kept")
    # (textures)
    need("kept_tex_holds(ks->tex, tx_now) && kept_slots_hold(ks->fp)" in build, "kept textures are used without their key or slots")
    need("ks->tex.tex_gen != tx_now.tex_gen" in build and "tex_handle(d, k) == ks->handles[i++]" in build,
         "kept textures are used through new bindings without the same handles")
    need("is_table ? table[k] : tex_handle(d, k)" in build, "the handles kept are not read as the check reads them")
    reused = block(build, "if (tx_reused) {")
    need("desc_fp().insert(desc_fp().end(), ks->fp.begin(), ks->fp.end())" in reused and "desc_fp_dummy |= ks->tex.dummy" in reused
         and "if (desc_fp_on)" in reused, "kept textures do not note their handles for Descriptor reuse")
    need("if (t->gpu_written) draw_sampled().push_back(t);" in reused, "kept textures do not give draw_sampled the GPU-written ones")
    need("st_dummy_textures += ks->dummies;" in reused, "kept textures are not counted as dummies")
    need("if (!out.imgs.back().sampler) tx_whole = false;" in build and "if (tx_keep && !tx_reused && tx_whole)" in build,
         "a texture segment with a sampler not made is kept")
    need("ks->fp.push_back((uint64_t)texture_slot_version((int)slot) << 20 | slot);" in build, "the slots' versions are not kept")
    # (storage buffers)
    need("kept_buf_holds(ks->buf, sb_now)" in build and "if (sb_reused) break;" in build, "kept storage buffers are not checked")
    need("gpu_bind_stamp() == sb_now.stamp && guest_pools_stamp() == sb_now.pools" in build,
         "storage buffers resolved while the pools changed are kept")
    need("if ((addr && plausible && !b) || addr >= (1ull << 40)) sb_whole = false;" in build,
         "an unbound storage buffer, or one in a virtual pool, is kept")
    # (uniform buffers)
    need("kept_ubo_holds(ks->ubo_keys[ui], now, c1)" in build and "now.on = keep && (c1 || gpu_bind_stamp() == now.stamp);" in build,
         "kept uniform buffers are not checked, or are kept across a pool change")
    uniform = block(src, "VkDescriptorBufferInfo uniform_range(")
    need("gap = !asked;" in uniform and "if (keep) *keep = gap;" in uniform, "a uniform buffer with an update over it is kept")
    user = block(uniform, "if (index >= 3 && index < 3 + 16) {")
    copy = user[user.index("const uint64_t at = stream_alloc(n, align);   // (unaligned"):]
    need("keep" not in copy, "a uniform range copied into the stream is kept")
    overlay = user[user.index("if (at != UINT64_MAX) {"):]
    need("keep" not in overlay[:overlay.index("}")], "an update's overlay copy is kept")
    # (what is never kept: storage images (texture_written), texel buffers)
    images = block(build, "for (const auto& d : info.image_descriptors) {")
    texel = block(build, "auto texel_views = [&](")
    need("ks->" not in images and "ks->" not in texel, "storage images or texel buffers are kept")
    # (a recording part's start drops it all)
    need("desc_kept_part++;" in block(src, "void draw_begin_recording("), "what is kept outlives its recording part")
    need("| `RX_VK_DESC_KEEP=0` |" in (ROOT / "docs" / "development.md").read_text(encoding="utf-8"),
         "docs/development.md does not list RX_VK_DESC_KEEP")
    code = "\n".join(block(src, m) + (";" if m.startswith("struct ") else "") for m in (
        "struct KeptTexKey {", "bool kept_tex_holds(", "struct KeptBufKey {", "bool kept_buf_holds(", "struct KeptUboKey {",
        "bool kept_ubo_holds(", "bool kept_slots_hold(", "bool desc_keep_textures(", "bool desc_keep_storage("))
    with tempfile.TemporaryDirectory(prefix="desc-keep-") as tmp:
        c = Path(tmp) / "fixture.cpp"
        exe = Path(tmp) / "fixture"
        c.write_text(FIXTURE.replace("@CODE@", code), encoding="utf-8")
        subprocess.run([a.cxx, "-std=c++20", "-Wall", "-Wextra", "-Werror", str(c), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    print("PASS: a stage's descriptors are kept only while what they were resolved from stands")


if __name__ == "__main__":
    main()
