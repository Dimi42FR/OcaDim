"""Programs with the same bindings share one set layout and pipeline layout (gpu/vk/vk_draw.cpp layout_signature, layouts_for).

One layout a program, a program change at a bind point pushed every descriptor again (bind_descriptors: ps.layout != p.layout),
even between two programs whose sets are laid out the same. The signature and the cache are cut out of the source and compiled
with stub Vulkan calls: the same create infos give the same handles, made once; a binding's number, type, count or stages, the
push-descriptor flag, the binding count or the push constant range told apart; immutable samplers and pNext chains not shared;
a create the driver failed not kept; and RX_VK_LAYOUT_EACH=1 makes each program its own, as before. The source is then read for
the rules the layouts' users keep: ensure_layout takes its layouts from the cache and marks them, and every place that destroys a
program's layouts leaves the shared ones (other programs, their pipelines and recordings use them).

python -I -B tests/test_shared_layouts.py [--cxx g++]
"""
import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path

RUN_ALL_ARGS = ["--cxx", "{cxx}"]

ROOT = Path(__file__).resolve().parents[1]
VK = ROOT / "gpu" / "vk"

FIXTURE = r"""
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <mutex>
#include <vector>
#include "longshot_env.h"
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr, "FAIL:%d %s\n", __LINE__, #x); std::exit(1); } } while (0)
typedef uint64_t VkDescriptorSetLayout;
typedef uint64_t VkPipelineLayout;
typedef uint64_t VkSampler;
typedef uint64_t VkDevice;
typedef uint32_t VkFlags;
typedef VkFlags VkShaderStageFlags;
#define VK_NULL_HANDLE 0
enum VkDescriptorType { UBO = 6, SSBO = 7, TEX = 1, IMG = 3 };
struct VkDescriptorSetLayoutBinding {
    uint32_t binding; VkDescriptorType descriptorType; uint32_t descriptorCount; VkShaderStageFlags stageFlags;
    const VkSampler* pImmutableSamplers;
};
struct VkDescriptorSetLayoutCreateInfo {
    int sType; const void* pNext; VkFlags flags; uint32_t bindingCount; const VkDescriptorSetLayoutBinding* pBindings;
};
struct VkPushConstantRange { VkShaderStageFlags stageFlags; uint32_t offset, size; };
struct VkPipelineLayoutCreateInfo {
    int sType; const void* pNext; VkFlags flags; uint32_t setLayoutCount; const VkDescriptorSetLayout* pSetLayouts;
    uint32_t pushConstantRangeCount; const VkPushConstantRange* pPushConstantRanges;
};
struct { VkDevice device = 1; } dev;
uint64_t next_handle = 100;
int set_made = 0, layout_made = 0;
bool fail_next_layout = false;
VkDescriptorSetLayout set_seen = 0;   // (the set layout the pipeline layout was made over)
int vkCreateDescriptorSetLayout(VkDevice, const VkDescriptorSetLayoutCreateInfo*, const void*, VkDescriptorSetLayout* out) {
    set_made++, *out = ++next_handle;
    return 0;
}
int vkCreatePipelineLayout(VkDevice, const VkPipelineLayoutCreateInfo* pi, const void*, VkPipelineLayout* out) {
    CHECK(pi->setLayoutCount == 1 && pi->pSetLayouts && *pi->pSetLayouts);
    set_seen = *pi->pSetLayouts;
    if (fail_next_layout) return fail_next_layout = false, *out = 0, -1;
    layout_made++, *out = ++next_handle;
    return 0;
}
void logf(const char*, ...) {}

@CACHE@

struct Made { VkDescriptorSetLayout set; VkPipelineLayout layout; bool shared; };
struct Sig {
    std::vector<VkDescriptorSetLayoutBinding> b;
    VkFlags flags = 1;   // (push descriptors)
    VkPushConstantRange range{0x11, 0, 64};
    const void* next = nullptr;
};
Sig base() {
    Sig s;
    s.b = {{0, UBO, 1, 0x1, nullptr}, {1, SSBO, 2, 0x1, nullptr}, {2, TEX, 4, 0x10, nullptr}};
    return s;
}
Made make(const Sig& s) {
    VkDescriptorSetLayoutCreateInfo li{};
    li.pNext = s.next, li.flags = s.flags, li.bindingCount = (uint32_t)s.b.size(), li.pBindings = s.b.data();
    VkPipelineLayoutCreateInfo pi{};
    pi.setLayoutCount = 1, pi.pushConstantRangeCount = 1, pi.pPushConstantRanges = &s.range;
    Made m{};
    m.shared = layouts_for(li, pi, &m.set, &m.layout);
    CHECK(pi.pSetLayouts == &m.set);   // (pSetLayouts set, to the set given back)
    return m;
}

int main() {
    const bool each = env_on("RX_VK_LAYOUT_EACH");
    const Made a = make(base());
    CHECK(a.set && a.layout && set_made == 1 && layout_made == 1 && set_seen == a.set);
    const Made b = make(base());
    if (each) {   // (one each, as before: never shared, never the same)
        CHECK(!a.shared && !b.shared && b.set != a.set && b.layout != a.layout && set_made == 2 && layout_made == 2);
        std::puts("each");
        return 0;
    }
    CHECK(a.shared && b.shared && b.set == a.set && b.layout == a.layout && set_made == 1 && layout_made == 1);
    // (each part of the signature told apart: a new pair for each, made once)
    std::vector<Sig> other;
    { Sig s = base(); s.b[1].binding = 5; other.push_back(s); }
    { Sig s = base(); s.b[1].descriptorType = IMG; other.push_back(s); }
    { Sig s = base(); s.b[2].descriptorCount = 5; other.push_back(s); }
    { Sig s = base(); s.b[0].stageFlags = 0x11; other.push_back(s); }
    { Sig s = base(); s.flags = 0; other.push_back(s); }                    // (a set allocated from a pool, not pushed)
    { Sig s = base(); s.b.pop_back(); other.push_back(s); }
    { Sig s = base(); s.range.stageFlags = 0x31; other.push_back(s); }      // (a stage without descriptors: the push range only)
    { Sig s = base(); s.range.size = 128; other.push_back(s); }
    { Sig s = base(); s.range.offset = 16; other.push_back(s); }
    std::vector<Made> made;
    for (const Sig& s : other) {
        const Made m = make(s);
        CHECK(m.shared && m.set != a.set && m.layout != a.layout);
        for (const Made& o : made) CHECK(m.set != o.set && m.layout != o.layout);
        made.push_back(m);
    }
    CHECK(set_made == 1 + (int)other.size() && layout_made == 1 + (int)other.size());
    for (size_t i = 0; i < other.size(); i++) {   // (and each found again)
        const Made m = make(other[i]);
        CHECK(m.shared && m.set == made[i].set && m.layout == made[i].layout);
    }
    CHECK(set_made == 1 + (int)other.size());
    // (not shared: immutable samplers, a pNext chain; each its own, every time)
    const VkSampler sampler = 7;
    Sig imm = base();
    imm.b[2].pImmutableSamplers = &sampler;
    const Made i1 = make(imm), i2 = make(imm);
    CHECK(!i1.shared && !i2.shared && i1.layout != i2.layout && i1.layout != a.layout);
    Sig chained = base();
    const int ext = 0;
    chained.next = &ext;
    const Made c1 = make(chained);
    CHECK(!c1.shared && c1.layout != a.layout);
    // (a pipeline layout the driver did not make is not kept: the next program of that signature makes its own again)
    Sig fresh = base();
    fresh.b[0].descriptorCount = 9;
    fail_next_layout = true;
    const Made f1 = make(fresh);
    CHECK(!f1.shared && !f1.layout && f1.set);
    const int before = layout_made;
    const Made f2 = make(fresh);
    CHECK(f2.shared && f2.layout && layout_made == before + 1);
    std::puts("shared");
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


def code(text):
    """the text without // comments"""
    return re.sub(r"//[^\n]*", "", text)


def check_sources(draw):
    ensure = code(block(draw, "void ensure_layout(Program& p) {"))
    if "p.layout_shared = layouts_for(li, pi, &p.set_layout, &layout);" not in ensure:
        raise SystemExit("ensure_layout does not take its layouts from layouts_for and mark them")
    if "vkCreateDescriptorSetLayout(" in ensure or "vkCreatePipelineLayout(" in ensure:
        raise SystemExit("ensure_layout makes layouts itself, past the cache")
    if ensure.index("layouts_for(") > ensure.index("p.layout = layout;"):
        raise SystemExit("ensure_layout publishes p.layout before its layouts are made")
    cache = code(block(draw, "bool layouts_for("))
    for needle, why in (('env_on("RX_VK_LAYOUT_EACH")', "the A/B switch is read"),
                        ("std::lock_guard lk(shared_layouts_mu);", "the cache is locked (the prepare's workers share it)")):
        if needle not in cache:
            raise SystemExit("layouts_for: " + why + " (not found: " + needle + ")")
    if "vkDestroy" in cache:
        raise SystemExit("layouts_for destroys a layout: the shared ones are kept for the device's life")
    header = (VK / "vk_shader.h").read_text(encoding="utf-8")
    if "bool layout_shared = false;" not in header:
        raise SystemExit("vk_shader.h: Program::layout_shared must start false (a program's own layouts)")
    # (every destroy of a program's layouts leaves the shared ones: within the lines before it, a test of layout_shared)
    destroy = re.compile(r"vkDestroy(?:PipelineLayout|DescriptorSetLayout)\(dev\.device, p(?:\.|->)(?:set_)?layout\b")
    found = 0
    for path in sorted(VK.glob("*.cpp")):
        lines = (draw if path.name == "vk_draw.cpp" else path.read_text(encoding="utf-8")).splitlines()
        for n, line in enumerate(lines):
            if not destroy.search(line):
                continue
            window = "\n".join(lines[max(0, n - 4):n + 1])
            if path.name == "vk_framegen.cpp" and "drop_pipe(Pipe& p)" in window:
                continue   # (its own pipelines' layouts, not a program's)
            found += 1
            if "layout_shared" not in window:
                raise SystemExit("%s:%d destroys a program's layout without leaving a shared one" % (path.name, n + 1))
    if found < 4:
        raise SystemExit("the destroys of programs' layouts were not found (%d): the check reads nothing" % found)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cxx", default="g++")
    a = p.parse_args()
    draw = (VK / "vk_draw.cpp").read_text(encoding="utf-8")
    check_sources(draw)
    start = draw.index("std::vector<uint64_t> layout_signature(")
    cache = draw[start:draw.index("bool layouts_for(", start)] + block(draw, "bool layouts_for(")
    with tempfile.TemporaryDirectory(prefix="shared-layouts-") as tmp:
        c = Path(tmp) / "fixture.cpp"
        exe = Path(tmp) / ("fixture.exe" if os.name == "nt" else "fixture")
        with open(c, "w", encoding="utf-8", newline="\n") as f:
            f.write(FIXTURE.replace("@CACHE@", cache))
        cmd = [a.cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-I", str(VK / "compat"), str(c),
               "-o", str(exe)]
        if os.name == "nt":
            cmd.append("-static")
        subprocess.run(cmd, check=True)
        env = dict(os.environ)
        env.pop("RX_VK_LAYOUT_EACH", None)
        out = subprocess.run([str(exe)], env=env, check=True, capture_output=True, text=True).stdout.strip()
        if out != "shared":
            raise SystemExit("the default run did not share: " + out)
        env["RX_VK_LAYOUT_EACH"] = "1"
        out = subprocess.run([str(exe)], env=env, check=True, capture_output=True, text=True).stdout.strip()
        if out != "each":
            raise SystemExit("RX_VK_LAYOUT_EACH=1 did not make each program its own: " + out)
    print("ok: programs with the same bindings share their layouts; the shared ones are never destroyed")


if __name__ == "__main__":
    main()
