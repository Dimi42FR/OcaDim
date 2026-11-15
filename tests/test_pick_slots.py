"""The last picks' program stands across texture registrations and uniform updates, and the pick is the one the full pick makes.

A graphics program whose answers are read from c2 (answer_stage_mask) has its handles from its stages' bindings alone: while those
stand (tex_gen) and its entry in `picks` is the one it was kept from (Pick::gen), the full pick reads the same handles, finds them
the same and keeps the same program, unless a slot they name was registered anew (pick_slots_kept). The real program_for and the
code around it are cut out of gpu/vk/vk_shader.cpp and driven through a stream of binds, registrations, uniform updates, program
and input changes and draws, once as it is and once with RX_VK_PICK_REG_GEN=1 (the last picks wait for every registration and
update, as before): the two pick the same program for every draw, the program the bound textures still answer, and the first
reads fewer handles.

python -I -B tests/test_pick_slots.py --headers <Vulkan-Headers/include> [--cxx clang++]
"""
# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
import os
import subprocess
import tempfile
from pathlib import Path

RUN_ALL_ARGS = ["--cxx", "{cxx}", "--headers", "{vulkan_headers}"]

ROOT = Path(__file__).resolve().parents[1]
ENV_ON_H = str(ROOT / "gpu" / "vk" / "compat" / "longshot_env.h")


def block(text, marker):
    start = text.index(marker)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def span(text, first, last):
    """From the marker first to the end of the block that last starts"""
    start = text.index(first)
    tail = block(text[start:], last)
    return text[start:text.index(tail, start) + len(tail)]


FIXTURE = r'''
// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <unordered_map>
#include <vector>
#include "vk_shader.h"
namespace mkwvk {
// (the world: 63 texture slots, their versions and the types they answer, a uniform buffer handles are read from too)
static uint32_t versions[64], types_of[64];
static uint64_t reg_gen, ub_gen;
static uint32_t ub_words[4];
static long answer_reads;   // (handles read by the full pick, answer_handles)
void logf(const char*, ...) {}
bool scene_tonemap_on() { return false; }
uint64_t ub_generation() { return ub_gen; }
uint64_t registrations_generation() { return reg_gen; }
uint32_t texture_slot_version(int id) { return versions[id & 63]; }
const Program* mesh_program_for(const NvnState&, const uint8_t*) { std::abort(); }
static uint32_t bound(const NvnState& s, const Program& p, const Program::Answer& a) {
    const Stage& st = p.stages[a.stage];
    const auto& d = st.info.texture_descriptors[a.desc];
    return d.cbuf_index == 2 ? (uint32_t)s.tex[st.nvn_stage][d.cbuf_offset / 8] : ub_words[d.cbuf_offset / 8 % 4];
}
uint32_t answer_handle(const NvnState& s, const Program& p, const Program::Answer& a) {
    answer_reads++;
    return bound(s, p, a);
}
bool still_valid(const NvnState& s, const Program& p) {
    for (const Program::Answer& a : p.answers) {
        const uint32_t h = bound(s, p, a);
        if (h && types_of[h & 63] != a.type) return false;
    }
    return true;
}
// (the programs: 1 reads a texture in c2 of its vertex stage and two of its fragment stage; 2 one in c2 and one from a uniform
// buffer (a handle answer_stage_mask refuses); 3 none)
static std::vector<Stage> stages_of(uint64_t serial) {
    std::vector<Stage> out;
    auto stage = [&](int nvn, std::vector<uint32_t> banks) {
        Stage st;
        st.nvn_stage = nvn;
        for (size_t i = 0; i < banks.size(); i++) {
            Shader::TextureDescriptor d{};
            d.type = Shader::TextureType::Color2D, d.count = 1, d.cbuf_index = banks[i], d.cbuf_offset = 8 * (uint32_t)i;
            st.info.texture_descriptors.push_back(d);
        }
        out.push_back(std::move(st));
    };
    if (serial == 1) stage(0, {2}), stage(1, {2, 2});
    if (serial == 2) stage(0, {}), stage(1, {2, 3});
    if (serial == 3) stage(0, {}), stage(1, {});
    return out;
}
static std::unordered_map<uint64_t, std::vector<std::unique_ptr<Program>>> variants;
static uint64_t made;
const Program* program_pick(const NvnState& s, ProgramKind, const uint8_t ct[8]) {   // (the first variant that stands, or a new one)
    auto& list = variants[s.prog.serial << 16 | s.vattr[0] << 8 | ct[0]];
    for (auto& p : list)
        if (still_valid(s, *p)) return p.get();
    auto p = std::make_unique<Program>();
    p->key = ++made;
    p->stages = stages_of(s.prog.serial);
    for (size_t k = 0; k < p->stages.size(); k++)
        for (size_t i = 0; i < p->stages[k].info.texture_descriptors.size(); i++) {
            Program::Answer a{(uint16_t)k, (uint16_t)i, 0, false};
            const uint32_t h = bound(s, *p, a);
            a.type = (uint8_t)(h ? types_of[h & 63] : 0);
            p->answers.push_back(a);
        }
    p->ready.store(true);
    list.push_back(std::move(p));
    return list.back().get();
}
#include PICK_CODE
}  // namespace mkwvk
int main(int argc, char** argv) {
    using namespace mkwvk;
    auto s = std::make_unique<NvnState>();
    s->has_prog = true, s->prog.serial = 1;
    uint8_t ct[8]{};
    uint64_t x = argc > 1 ? std::strtoull(argv[1], nullptr, 10) : 1;
    auto rnd = [&](uint32_t n) {
        x ^= x << 13, x ^= x >> 7, x ^= x << 17;
        return (uint32_t)(x % n);
    };
    for (int i = 0; i < 64; i++) types_of[i] = i % 3;
    long draws = 0;
    for (int e = 0; e < 200000; e++) {
        const uint32_t r = rnd(100);
        if (r < 40) {
            const Program* p = program_for(*s, ProgramKind::Graphics, ct);
            if (!p || !still_valid(*s, *p)) {
                std::fprintf(stderr, "FAIL: draw %ld picked a program its textures do not answer\n", draws);
                return 1;
            }
            std::printf("%llu\n", (unsigned long long)p->key);
            draws++;
        } else if (r < 55) {   // (a uniform update, now and then of the words a handle is read from)
            ub_gen++;
            if (rnd(4) == 0) ub_words[rnd(4)] = 1 + rnd(15);
        } else if (r < 70) {   // (a slot registered anew, now and then as another type)
            const uint32_t id = 1 + rnd(63);
            versions[id]++, reg_gen++;
            if (rnd(5) == 0) types_of[id] = rnd(3);
        } else if (r < 80) {   // (a texture bound, as NOP_BIND_TEX)
            const int st = rnd(2), at = rnd(3);
            const uint64_t h = 1 + rnd(15);
            if (s->tex[st][at] != h) s->bind_gen++, s->tex_gen[st] = s->bind_gen;
            s->tex[st][at] = h;
        } else if (r < 88) {
            s->bind_gen++;   // (a uniform buffer bound)
        } else if (r < 94) {
            s->prog.serial = 1 + rnd(3);
        } else if (r < 97) {
            s->vattr[0] = rnd(2);
        } else {
            ct[0] = (uint8_t)rnd(2);
        }
    }
    std::fprintf(stderr, "draws %ld, programs %llu, handles read %ld\n", draws, (unsigned long long)made, answer_reads);
    std::printf("reads %ld\n", answer_reads);
    return 0;
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cxx", default="clang++")
    p.add_argument("--headers", type=Path, required=True)
    a = p.parse_args()
    vk = ROOT / "gpu" / "vk"
    shader = (vk / "vk_shader.cpp").read_text(encoding="utf-8")
    choose = block(shader, "const Program* program_for(")
    for needle, why in (
        ("!by_reg && !compute && f.amask != ~0u && fbind == bind", "the slots stand in for a program whose handles may move"),
        ("keep(by_slots->p, by_slots)", "a pick kept by its slots is not kept again as the full pick keeps it"),
        ("f.pick = from, f.pick_gen = from ? from->gen : 0", "a kept pick does not remember its entry"),
        ("prog_fast[0].pick = prog_fast[1].pick = nullptr", "the kept picks outlive the entries they name"),
        ('env_on("RX_VK_PICK_REG_GEN")', "the switch is missing"),
    ):
        if needle not in choose:
            raise SystemExit(f"program_for: {why} ({needle} missing)")
    if choose.count("pk.gen++") != 2 or choose.index("pk.handles.swap(now);") > choose.index("pk.gen++"):
        raise SystemExit("program_for: an entry of picks changes without its gen")
    code = span(shader, "struct Pick {", "void answer_handles(") + "\n\n" + span(shader, "bool prog_same(", "const Program* program_for(")
    flags = ["-std=c++20", "-include", ENV_ON_H, "-O1", "-w", "-DNDEBUG", "-DVK_NO_PROTOTYPES", "-DMKWVK_INCLUDES=2"]
    for header in ("algorithm", "cstdio", "cstdlib", "cstring", "functional", "string", "vector"):
        flags += ["-include", header]
    includes = [vk, vk / "compat", ROOT / "gpu/compat", vk / "eden", ROOT / "gpu/third_party/suyu", a.headers]
    if os.name != "nt":
        includes.insert(0, ROOT / "host/posix")
    flags += ["-I" + str(path.resolve()) for path in includes]
    with tempfile.TemporaryDirectory(prefix="pick-slots-") as tmp:
        folder = Path(tmp)
        (folder / "pick_code.inc").write_text(code, encoding="utf-8")
        cpp, exe = folder / "fixture.cpp", folder / "fixture.exe"
        cpp.write_text(FIXTURE.replace("PICK_CODE", '"pick_code.inc"'), encoding="utf-8")
        subprocess.run([a.cxx, *flags, str(cpp), "-o", str(exe)], cwd=folder, check=True)
        for seed in ("1", "7", "12345"):
            runs = {}
            for name, value in (("now", None), ("before", "1")):
                env = os.environ.copy()
                env.pop("RX_VK_PICK_REG_GEN", None)
                env.pop("RX_VK_PICK_BIND_GEN", None)
                if value: env["RX_VK_PICK_REG_GEN"] = value
                out = subprocess.run([str(exe), seed], cwd=folder, env=env, check=True, capture_output=True, text=True)
                lines = out.stdout.split()
                runs[name] = (lines[:-2], int(lines[-1]))
            (now, now_reads), (before, before_reads) = runs["now"], runs["before"]
            if now != before:
                first = next(i for i, (n, b) in enumerate(zip(now, before)) if n != b) if len(now) == len(before) else -1
                raise SystemExit(f"seed {seed}: draw {first} picked program {now[first]} where the full pick picks {before[first]}")
            if not now_reads < before_reads:
                raise SystemExit(f"seed {seed}: the last picks read {now_reads} handles, as many as before ({before_reads})")
            print(f"seed {seed}: {len(now)} draws, the same picks; handles read {now_reads} (before {before_reads})")
    print("PASS: the last picks stand across registrations and uniform updates, and pick as the full pick does")


if __name__ == "__main__":
    main()
