// (longshot) P1 of AMD FSR Frame Generation: AMD's swapchain, the renderer's image, no generated frames yet.
//
// AMD's FidelityFX SDK takes the window's swapchain over through one context: ffxCreateContext with
// ffxCreateContextDescFrameGenerationSwapChainVK makes a swapchain of its own (it stays behind the handle the game
// holds) and ffxQuery fills in the functions that replace vkCreateSwapchainKHR, vkDestroySwapchainKHR,
// vkGetSwapchainImagesKHR, vkAcquireNextImageKHR and vkQueuePresentKHR. Until P2 creates the frame generation context
// and configures it, that swapchain presents the picture as the plain one does: this is what the first test checks.
//
// What the SDK asks, and what this file keeps:
// - A present queue nothing else submits to. A queue of the game's own would be submitted to by the SDK's present
//   path and by the replay at once; the two deadlocked on the SDK's own queue in the reference implementation. The
//   device makes a second queue of the graphics family for it (vk_main.cpp create_device, RX_VK_FG_AMD=1).
// - The descriptions a context was made from stay alive until it is destroyed (the SDK keeps pointers into them): they
//   live here, not on the stack.
// - A new size remakes the swapchain in place with the context's create function, and the handle stays.
// - Taking it down waits for its presents, destroys the context, then calls its destroy function last.
//
// AMD's library is looked for beside the game as vk_fsr4.cpp looks for its upscaler: amd_fidelityfx_loader_vk.dll,
// with amd_fidelityfx_framegeneration_vk.dll beside it. RX_VK_FG_AMD=1: on. Without the library, the second queue or
// the SDK's agreement, the log says why and the present path is the one without it, unchanged.
#include "vk_fg_amd.h"

#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "vk_internal.h"
#include "vk_menu.h"      // (the menu open: frame generation paused, as the renderer's own is)
#include "vk_temporal.h"  // (the scene's depth, motion, jitter and camera for the frame)

#ifdef _WIN32
#include <windows.h>
#include <chrono>

#include "vk_paths.h"
#include "../../third_party/fidelityfx/api/include/ffx_api.h"
#include "../../third_party/fidelityfx/api/include/ffx_api_types.h"
#include "../../third_party/fidelityfx/api/include/vk/ffx_api_vk.h"
#include "../../third_party/fidelityfx/framegeneration/include/ffx_framegeneration.h"
#include "../../third_party/fidelityfx/framegeneration/include/vk/ffx_api_framegeneration_vk.h"

namespace mkwvk {
namespace {

constexpr const char* kLoader = "amd_fidelityfx_loader_vk.dll";

/// Everything AMD's swapchain keeps. Never destroyed: a run leaves through exit() with the device alive, and a
/// destructor here would call into AMD's DLL after its own detach.
struct State {
    bool loaded = false;      // (the loader was looked for)
    bool available = false;   // (it lists a swapchain for this device)
    bool failed = false;      // (asked, and refused: the plain swapchain for the rest of the run)
    HMODULE lib = nullptr;
    PfnFfxCreateContext create = nullptr;
    PfnFfxDestroyContext destroy = nullptr;
    PfnFfxQuery query = nullptr;
    PfnFfxDispatch dispatch = nullptr;
    PfnFfxConfigure configure = nullptr;
    ffxContext sc = nullptr;   // (the swapchain context)
    VkSwapchainKHR handle = VK_NULL_HANDLE;   // (the swapchain it made: remade in place, destroyed after the context)
    ffxQueryDescSwapchainReplacementFunctionsVK fn{};
    // (what the context was made from, kept as the SDK asks)
    ffxCreateContextDescFrameGenerationSwapChainVK desc{};
    ffxCreateContextDescFrameGenerationSwapChainVersionVK version{};
    // (P2: the frame generation context, for the swapchain's size and format)
    ffxContext fg = nullptr;
    ffxCreateBackendVKDesc backend{};
    ffxCreateContextDescFrameGeneration fg_desc{};
    ffxCreateContextDescFrameGenerationVersion fg_version{};
    uint32_t fg_w = 0, fg_h = 0;
    VkFormat fg_format = VK_FORMAT_UNDEFINED;
    uint64_t frame_id = 0;    // (one more a frame, as the API asks)
    uint64_t generated = 0;   // (the callback's count)
    bool prepared = false;    // (the last frame prepared: the next one after an off frame resets)
    bool gen_failed = false;  // (asked and refused: the swapchain stays, the frames are not generated)
    int64_t frame_ns = 0;     // (the last preparation's time, for frameTimeDelta)
    uint64_t presents = 0;    // (what the swapchain says it presented, for the log)
};
State& st() {
    static State& s = *new State;
    return s;
}

/// RX_VK_FG_AMD when set for this run (0 or 1), over the menu's row. False: the row decides
bool env_on(bool* value) {
    const char* e = getenv("RX_VK_FG_AMD");
    if (!e || !*e) return false;
    *value = atoi(e) != 0;
    return true;
}

void* symbol(const char* name) { return (void*)GetProcAddress(st().lib, name); }

/// The folders the library is looked for in: RX_VK_FSR_DIR, the executable's, the game folder (the same order as FSR 4's)
std::vector<std::string> library_dirs() {
    std::vector<std::string> dirs;
    if (const char* e = getenv("RX_VK_FSR_DIR"); e && *e) dirs.emplace_back(e);
    char exe[MAX_PATH];
    DWORD n = GetModuleFileNameA(nullptr, exe, MAX_PATH);
    if (n && n < MAX_PATH) {
        std::string s(exe, n);
        dirs.push_back(s.substr(0, s.find_last_of("\\/")));
    }
    n = game_module_path(exe, MAX_PATH);
    if (n && n < MAX_PATH) {
        std::string s(exe, n);
        s = s.substr(0, s.find_last_of("\\/"));
        if (dirs.empty() || dirs.back() != s) dirs.push_back(s);
    }
    return dirs;
}

/// The versions the loader lists for one kind of context, as text; 0 when it lists none.
int list_versions(uint64_t type, char* out, size_t size) {
    const VkDeviceContext context{dev.device, dev.physical, vkGetDeviceProcAddr};
    ffxQueryDescGetVersions q{};
    q.header.type = FFX_API_QUERY_DESC_TYPE_GET_VERSIONS;
    q.createDescType = type;
    q.device = (void*)&context;
    uint64_t n = 0;
    q.outputCount = &n;
    out[0] = 0;
    if (st().query(nullptr, &q.header) != FFX_API_RETURN_OK || !n) return 0;
    std::vector<uint64_t> ids(n);
    std::vector<const char*> names(n);
    q.versionIds = ids.data();
    q.versionNames = names.data();
    if (st().query(nullptr, &q.header) != FFX_API_RETURN_OK) return 0;
    size_t len = 0;
    for (uint64_t i = 0; i < n; i++) {
        len += (size_t)snprintf(out + len, size - len, "%s%s", i ? ", " : "", names[i] ? names[i] : "?");
        if (len >= size) len = size - 1;
    }
    return (int)n;
}

/// (OcaDim) The id of the frame generation version whose name starts with `want_major` ("4" or "3"), from what AMD's
/// loader lists for this device; 0 when it lists none like that (the SDK's own version is then used)
/// (OcaDim) The major of the frame generation version the context was made with (4 or 3), 0 before one is made
int g_fg_major = 0;

uint64_t pick_fg_version(int want_major) {
    const VkDeviceContext context{dev.device, dev.physical, vkGetDeviceProcAddr};
    ffxQueryDescGetVersions q{};
    q.header.type = FFX_API_QUERY_DESC_TYPE_GET_VERSIONS;
    q.createDescType = FFX_API_CREATE_CONTEXT_DESC_TYPE_FRAMEGENERATION;
    q.device = (void*)&context;
    uint64_t n = 0;
    q.outputCount = &n;
    if (st().query(nullptr, &q.header) != FFX_API_RETURN_OK || !n) return 0;
    std::vector<uint64_t> ids(n);
    std::vector<const char*> names(n);
    q.versionIds = ids.data();
    q.versionNames = names.data();
    if (st().query(nullptr, &q.header) != FFX_API_RETURN_OK) return 0;
    for (uint64_t i = 0; i < n; i++) {
        // (OcaDim) each entry as AMD names it, so a choice that finds nothing says what it was offered
        const char* name = names[i] ? names[i] : "";
        logf("vk: AMD FG: frame generation version %llu is \"%s\"", (unsigned long long)ids[i], name);
        // (OcaDim) the first number anywhere in the name: "4.0.2" and "FSR 4.0.2" both give 4
        for (const char* p = name; *p; p++)
            if (*p >= '0' && *p <= '9') {
                if (atoi(p) == want_major) return ids[i];
                break;
            }
    }
    return 0;
}

/// Loads AMD's loader once and asks it what this device can run. False: no library, or nothing for this GPU.
bool load() {
    State& s = st();
    if (s.loaded) return s.available;
    s.loaded = true;
    std::string where;
    for (const std::string& dir : library_dirs()) {
        const std::string path = dir + "\\" + kLoader;
        where += (where.empty() ? "" : ", ") + path;
        if (GetFileAttributesA(path.c_str()) == INVALID_FILE_ATTRIBUTES) continue;
        // (the module the loader picks lies beside it: the loader's own folder first)
        s.lib = LoadLibraryExA(path.c_str(), nullptr, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
        if (!s.lib) logf("vk: AMD FG: %s not loaded (Windows error %lu)", path.c_str(), (unsigned long)GetLastError());
        if (s.lib) break;
    }
    if (!s.lib) {
        logf("vk: AMD FG: no %s in %s", kLoader, where.c_str());
        return false;
    }
    s.create = (PfnFfxCreateContext)symbol("ffxCreateContext");
    s.destroy = (PfnFfxDestroyContext)symbol("ffxDestroyContext");
    s.query = (PfnFfxQuery)symbol("ffxQuery");
    s.dispatch = (PfnFfxDispatch)symbol("ffxDispatch");
    s.configure = (PfnFfxConfigure)symbol("ffxConfigure");
    if (!s.create || !s.destroy || !s.query || !s.dispatch || !s.configure) {
        logf("vk: AMD FG: %s lacks the FSR API's entry points", kLoader);
        return false;
    }
    char sc_list[160], fg_list[160];
    const int ns = list_versions(FFX_API_CREATE_CONTEXT_DESC_TYPE_FGSWAPCHAIN_VK, sc_list, sizeof sc_list);
    const int nf = list_versions(FFX_API_CREATE_CONTEXT_DESC_TYPE_FRAMEGENERATION, fg_list, sizeof fg_list);
    if (!ns) {
        logf("vk: AMD FG: AMD's loader lists no frame generation swapchain for this device (frame generation %s): off", nf ? fg_list : "none");
        return false;
    }
    logf("vk: AMD FG: AMD's frame generation for this device: swapchain %s; frame generation %s", sc_list, nf ? fg_list : "none");
    s.available = true;
    return true;
}

/// AMD's presents done before the swapchain is remade or taken down (the SDK's own dispatch asks for it).
void wait_presents() {
    State& s = st();
    if (!s.sc) return;
    ffxDispatchDescFrameGenerationSwapChainWaitForPresentsVK wait{};
    wait.header.type = FFX_API_DISPATCH_DESC_TYPE_FGSWAPCHAIN_WAIT_FOR_PRESENTS_VK;
    s.dispatch(&s.sc, &wait.header);
}

/// (P2) An HDR10 swapchain (10-bit PQ or 16-bit float): frame generation is told its inputs are HDR
bool hdr_format(VkFormat f) {
    return f == VK_FORMAT_A2B10G10R10_UNORM_PACK32 || f == VK_FORMAT_A2R10G10B10_UNORM_PACK32 ||
           f == VK_FORMAT_R16G16B16A16_SFLOAT;
}

/// A chain image as AMD's API takes it: its format and size, in the state the chain leaves them (GENERAL)
FfxApiResource image_resource(VkImage image, VkFormat format, uint32_t w, uint32_t h) {
    VkImageCreateInfo ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    ci.imageType = VK_IMAGE_TYPE_2D;
    ci.format = format;
    ci.extent = {w, h, 1};
    ci.mipLevels = 1;
    ci.arrayLayers = 1;
    ci.samples = VK_SAMPLE_COUNT_1_BIT;
    ci.tiling = VK_IMAGE_TILING_OPTIMAL;
    ci.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    return ffxApiGetResourceVK((void*)image, ffxApiGetImageResourceDescriptionVK(image, ci, 0),
                               FFX_API_RESOURCE_STATE_UNORDERED_ACCESS);
}

/// The swapchain's callback at its present: AMD's frame generation between the frame just shown and the one before
ffxReturnCode_t generate(ffxDispatchDescFrameGeneration* d, void* user) {
    State& s = st();
    s.generated++;
    return s.dispatch((ffxContext*)user, &d->header);
}

/// The frame generation context, let go (the swapchain context stays: the frames are the swapchain's). Its work must be
/// done: the caller waits its presents, and the device is idle.
void release_fg() {
    State& s = st();
    if (!s.fg) return;
    s.destroy(&s.fg, nullptr);
    s.fg = nullptr;
    s.prepared = false;
    s.fg_w = s.fg_h = 0;
    s.fg_format = VK_FORMAT_UNDEFINED;
}

/// Makes the frame generation context for a swapchain of w x h and fmt. False: AMD refused, the swapchain keeps showing
/// the frames as they are (gen_failed, said once).
bool create_fg(uint32_t w, uint32_t h, VkFormat fmt, bool depth_reversed, float far_z, uint32_t max_w, uint32_t max_h) {
    State& s = st();
    s.backend = {};
    s.backend.header.type = FFX_API_CREATE_CONTEXT_DESC_TYPE_BACKEND_VK;
    s.backend.deviceContext = VkDeviceContext{dev.device, dev.physical, vkGetDeviceProcAddr};
    s.fg_version = {};
    s.fg_version.header.type = FFX_API_CREATE_CONTEXT_DESC_TYPE_FRAMEGENERATION_VERSION;
    // (OcaDim) the version the Frame generation by row asks for: index 3 is AMD FSR 4's generation, 2 AMD FSR 3.1's;
    // anything else (Auto, the game's own, DLSS) leaves the SDK's own choice, the newest it lists.
    // (OcaDim) the row chooses when it names a generation (3: FSR 4's, 2: FSR 3.1's); anything else keeps what 0.0.2 did,
    // AMD's own FFX_FRAMEGENERATION_VERSION, which is FSR 4's on the SDK we ship
    const int want_major = [] {
        if (const char* force = getenv("RX_VK_FG_AMD_FORCE")) {   // (OcaDim) the run's switch: 4 or 3, and nothing else
            const int v = atoi(force);
            if (v >= 4) return 4;
            if (v == 3) return 3;
        }
        return opts.framegen_by == 3 ? 4 : opts.framegen_by == 2 ? 3 : 0;
    }();
    // (OcaDim) what this creation sees, said: the row as it stands at this instant, and the version that follows from it. A
    // framegen_by of 0 here means the context was made before the row was read, and the SDK's own (the newest it lists) is
    // what is asked for
    logf("vk: AMD FG: create_fg: framegen_by=%d, so %s", opts.framegen_by,
         want_major == 4 ? "AMD FSR 4's generation" : want_major == 3 ? "AMD FSR 3.1's generation" : "the SDK's own version");
    const uint64_t picked = want_major ? pick_fg_version(want_major) : 0;
    s.fg_version.version = picked ? picked : FFX_FRAMEGENERATION_VERSION;
    // (OcaDim) nothing is named before the context is made: a refused creation must leave the counter with no generation
    // at all, not with the one that was asked for
    g_fg_major = 0;
    logf("vk: AMD FG: the frame generation context is made with %s",
         picked ? (want_major == 4 ? "AMD FSR 4" : "AMD FSR 3.1") : "the SDK's own version");
    if (want_major && !picked)
        logf("vk: AMD FG: no FSR %d frame generation listed for this device; the SDK's own version is made instead", want_major);
    s.fg_version.header.pNext = &s.backend.header;
    s.fg_desc = {};
    s.fg_desc.header.type = FFX_API_CREATE_CONTEXT_DESC_TYPE_FRAMEGENERATION;
    s.fg_desc.header.pNext = &s.fg_version.header;
    // (the projection's far plane: infinite only where the camera says so (the chain's camera has a far of 1e8 there,
    // 1000.5 for Ocarina's own). FSR 3.1's reversed depth is the only input the chain gives reversed)
    const bool infinite = !(far_z > 0.0f) || far_z >= 1e6f;
    s.fg_desc.flags = (infinite ? FFX_FRAMEGENERATION_ENABLE_DEPTH_INFINITE : 0) |
                      (depth_reversed ? FFX_FRAMEGENERATION_ENABLE_DEPTH_INVERTED : 0) |
                      (hdr_format(fmt) ? FFX_FRAMEGENERATION_ENABLE_HIGH_DYNAMIC_RANGE : 0);
    s.fg_desc.displaySize = {w, h};
    // (the scene's render size may be larger than the window: the game renders at its output size and the picture is
    // scaled into the window. The depth and motion are at the scene's size, the colour at the window's, as in the
    // reference where the scene is a widescreen picture and the display the window)
    s.fg_desc.maxRenderSize = {max_w, max_h};
    s.fg_desc.backBufferFormat = ffxApiGetSurfaceFormatVK(fmt);
    if (!s.fg_desc.backBufferFormat) {
        logf("vk: AMD FG: the swapchain's format %d is no surface format AMD's frame generation takes", (int)fmt);
        s.gen_failed = true;
        return false;
    }
    const auto t0 = std::chrono::steady_clock::now();
    const ffxReturnCode_t r = s.create(&s.fg, &s.fg_desc.header, nullptr);
    const double made_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    if (r != FFX_API_RETURN_OK || !s.fg) {
        s.fg = nullptr;
        s.gen_failed = true;
        logf("vk: AMD FG: AMD's frame generation context refused (%u) for %ux%u: the frames are not generated", (unsigned)r, w, h);
        return false;
    }
    s.fg_w = w, s.fg_h = h, s.fg_format = fmt;
    s.prepared = false;
    ffxQueryGetProviderVersion provider{};
    provider.header.type = FFX_API_QUERY_DESC_TYPE_GET_PROVIDER_VERSION;
    const bool known = s.query(&s.fg, &provider.header) == FFX_API_RETURN_OK && provider.versionName;
    // (OcaDim) the counter's generation is the one the made context says it is, not the one that was asked for: the SDK's
    // own fallback may be the other generation, and a version picked by name can still be made as something else. The first
    // number of the provider's own version name: "4.0.2" is 4, "3.1.6" is 3
    int made_major = 0;
    if (known)
        for (const char* p = provider.versionName; *p; p++)
            if (*p >= '0' && *p <= '9') {
                made_major = atoi(p);
                break;
            }
    g_fg_major = made_major == 4 ? 4 : made_major == 3 ? 3 : picked ? want_major : 0;
    FfxApiEffectMemoryUsage mem{};
    ffxQueryDescFrameGenerationGetGPUMemoryUsage mq{};
    mq.header.type = FFX_API_QUERY_DESC_TYPE_FRAMEGENERATION_GPU_MEMORY_USAGE;
    mq.gpuMemoryUsageFrameGeneration = &mem;
    const bool sized = s.query(&s.fg, &mq.header) == FFX_API_RETURN_OK;
    logf("vk: AMD FG: AMD's frame generation %s made for %ux%u (render up to %ux%u)%s, %.0f ms of CPU, %llu MB%s",
         known ? provider.versionName : "?", w, h, max_w, max_h, hdr_format(fmt) ? " (HDR)" : "", made_ms,
         (unsigned long long)(sized ? mem.totalUsageInBytes >> 20 : 0),
         " (the picture whole, HUD included: the UI resource is the next step)");
    return true;
}

}  // namespace

bool fg_amd_requested() {
    bool v = false;
    // (OcaDim) RX_VK_FG_AMD_FORCE=<3|4>: AMD's generation on for this run, with that version, whatever the rows say
    if (const char* force = getenv("RX_VK_FG_AMD_FORCE")) return atoi(force) >= 3;
    if (env_on(&v)) return v;   // (the switch over the menu, for a run)
    // (the "by" row alone: AMD's makes one frame between each two of the game's, whatever Frame generation's multiplier
    // says (2x to 8x is the renderer's own and DLSS's). Reading the multiplier here too tore its swapchain down when a
    // quality preset changed that row mid-run, and the next context was refused)
    return opts.framegen_by == 2 || opts.framegen_by == 3;   // (OcaDim: 2 FSR 3.1's generation, 3 FSR 4's)
}

bool fg_amd_wanted() {
    // (AMD's FidelityFX frame generation is AMD's: the SDK's providers run on AMD's Vulkan driver. Its library is Windows's)
    return fg_amd_requested() && dev.props.vendorID == 0x1002;
}

int fg_amd_major() { return g_fg_major; }

bool fg_amd_active() { return st().sc != nullptr; }

bool fg_amd_generating() { return st().fg != nullptr && !st().gen_failed; }

VkResult fg_amd_create_swapchain(const VkSwapchainCreateInfoKHR& ci, VkSwapchainKHR* out) {
    State& s = st();
    if (!fg_amd_wanted() || s.failed) return VK_ERROR_FEATURE_NOT_PRESENT;
    if (!dev.fg_game_queue || !dev.fg_present_queue || !dev.fg_acquire_queue) {
        static bool told;
        if (!told) told = true, logf("vk: AMD FG: the device has no three queues for AMD's presents: the plain swapchain stays");
        s.failed = true;
        return VK_ERROR_FEATURE_NOT_PRESENT;
    }
    if (!load()) return s.failed = true, VK_ERROR_FEATURE_NOT_PRESENT;
    if (s.sc) {   // a new size or format: the swapchain is remade in place and keeps its handle
        device_wait_idle_locked();   // (the replay's writes into the old images done, then the SDK's presents)
        wait_presents();
        release_fg();   // (its display size is the swapchain's: made again for the new one on the next frame)
        VkSwapchainCreateInfoKHR in = ci;
        in.oldSwapchain = VK_NULL_HANDLE;
        if (in.minImageCount > 6) in.minImageCount = 6;   // (the SDK's most, as above)
        VkSwapchainKHR handle = s.handle;
        const VkResult r = s.fn.pOutCreateSwapchainFFXAPI(dev.device, &in, nullptr, &handle, (void*)s.handle);
        if (r != VK_SUCCESS) {
            logf("vk: AMD FG: AMD's swapchain could not be remade (VkResult %d, %ux%u)", (int)r, ci.imageExtent.width,
                 ci.imageExtent.height);
            return VK_ERROR_INITIALIZATION_FAILED;
        }
        s.handle = handle;
        *out = handle;
        logf("vk: AMD FG: AMD's swapchain remade in place, %ux%u", ci.imageExtent.width, ci.imageExtent.height);
        return VK_SUCCESS;
    }
    s.handle = VK_NULL_HANDLE;
    s.desc = {};
    s.desc.header.type = FFX_API_CREATE_CONTEXT_DESC_TYPE_FGSWAPCHAIN_VK;
    s.desc.physicalDevice = dev.physical;
    s.desc.device = dev.device;
    s.desc.swapchain = &s.handle;
    s.desc.createInfo = ci;
    s.desc.createInfo.oldSwapchain = VK_NULL_HANDLE;   // (the context makes its own; the old one is the caller's to retire)
    // (the SDK's three queues, all different and none used by anything else: vk_main.cpp create_device. Its async compute
    // queue may stay null, which the SDK accepts)
    s.desc.gameQueue = {dev.fg_game_queue, dev.fg_family, nullptr};
    s.desc.asyncComputeQueue = {VK_NULL_HANDLE, dev.fg_family, nullptr};
    s.desc.presentQueue = {dev.fg_present_queue, dev.fg_family, nullptr};
    s.desc.imageAcquireQueue = {dev.fg_acquire_queue, dev.fg_family, nullptr};
    // (the SDK holds at most 6 of the app's images: 2 + the renderer's frame generation multiplier, capped at 4, is 6)
    if (s.desc.createInfo.minImageCount > 6) {
        logf("vk: AMD FG: %u images asked; AMD's swapchain takes 6 at most", s.desc.createInfo.minImageCount);
        s.desc.createInfo.minImageCount = 6;
    }
    // (the version this file was built against, which the SDK asks for with every context)
    s.version = {};
    s.version.header.type = FFX_API_CREATE_CONTEXT_DESC_TYPE_FRAMEGENERATIONSWAPCHAIN_VERSION_VK;
    s.version.version = FFX_FRAMEGENERATION_SWAPCHAIN_VK_VERSION;
    s.desc.header.pNext = &s.version.header;
    const ffxReturnCode_t rc = s.create(&s.sc, &s.desc.header, nullptr);
    if (rc != FFX_API_RETURN_OK || !s.sc) {
        s.sc = nullptr, s.handle = VK_NULL_HANDLE;
        logf("vk: AMD FG: AMD's swapchain context refused (return %u): the plain swapchain stays", (unsigned)rc);
        s.failed = true;
        return VK_ERROR_FEATURE_NOT_PRESENT;
    }
    s.fn = {};
    s.fn.header.type = FFX_API_QUERY_DESC_TYPE_FGSWAPCHAIN_FUNCTIONS_VK;
    if (s.query(&s.sc, &s.fn.header) != FFX_API_RETURN_OK || !s.fn.pOutQueuePresentKHR || !s.fn.pOutCreateSwapchainFFXAPI ||
        !s.fn.pOutGetSwapchainImagesKHR || !s.fn.pOutAcquireNextImageKHR || !s.handle) {
        const VkSwapchainKHR handle = s.handle;
        const PFN_vkDestroySwapchainFFXAPI destroy_swapchain = s.fn.pOutDestroySwapchainFFXAPI;
        s.destroy(&s.sc, nullptr), s.sc = nullptr, s.handle = VK_NULL_HANDLE;
        if (handle && destroy_swapchain) destroy_swapchain(dev.device, handle, nullptr, nullptr);   // (nothing was handed out yet)
        logf("vk: AMD FG: AMD's swapchain functions are incomplete: the plain swapchain stays");
        s.failed = true;
        return VK_ERROR_FEATURE_NOT_PRESENT;
    }
    *out = s.handle;
    logf("vk: AMD FG: AMD's frame generation swapchain, %ux%u, %u images asked (RX_VK_FG_AMD=1; no frame generation yet)",
         ci.imageExtent.width, ci.imageExtent.height, ci.minImageCount);
    return VK_SUCCESS;
}

void fg_amd_wait_presents() {
    if (st().sc) wait_presents();
}

bool fg_amd_frame(VkCommandBuffer cmd, VkSwapchainKHR sc, VkFormat format, VkExtent2D display, uint32_t src_w, uint32_t src_h) {
    State& s = st();
    // (OcaDim) every reason this frame is not given to AMD's generator, said once: without them a context that is never made
    // shows only as a counter naming no version. RX_VK_FG_AMD_FORCE=4 is the run that tells them apart
    static bool told_call, told_off, told_noscene, told_size, told_big;
    if (!told_call)
        told_call = true,
        logf("vk: AMD FG: fg_amd_frame called: picture %ux%u, window %ux%u, format %d", src_w, src_h, display.width,
             display.height, (int)format);
    if (!s.sc || s.failed || s.gen_failed) {
        if (!told_off)
            told_off = true,
            logf("vk: AMD FG: fg_amd_frame: not this frame (swapchain %s, swapchain refused %d, generation refused %d)",
                 s.sc ? "yes" : "no", (int)s.failed, (int)s.gen_failed);
        return false;
    }
    TemporalFgInputs in{};
    const bool have = temporal_fg_take(&in);
    // (the context's largest render size: the game's picture (the scene never larger than it) and the window)
    const uint32_t pic_w = src_w ? src_w : display.width, pic_h = src_h ? src_h : display.height;
    const uint32_t max_w = pic_w > display.width ? pic_w : display.width;
    const uint32_t max_h = pic_h > display.height ? pic_h : display.height;
    if (!s.fg) {
        if (!have) {   // (no scene this frame: nothing to configure, no context made for nothing)
            if (!told_noscene)
                told_noscene = true,
                logf("vk: AMD FG: fg_amd_frame: no depth and motion published yet, so no context is made (the chain has "
                     "not run an upscaler this run; temporal_fg_publish in vk_temporal.cpp)");
            return false;
        }
        if (!create_fg(display.width, display.height, format, in.depth_reversed, in.far_z, max_w, max_h)) return false;
    } else if (max_w > s.fg_desc.maxRenderSize.width || max_h > s.fg_desc.maxRenderSize.height) {
        // (the picture grew: a new Output resolution, or an upscaler share. A context made for the smaller one stops
        // generating for the larger scenes: it is made again for the largest, after its work is done)
        logf("vk: AMD FG: the picture is now %ux%u (was up to %ux%u): AMD's frame generation context made again", max_w, max_h,
             s.fg_desc.maxRenderSize.width, s.fg_desc.maxRenderSize.height);
        device_wait_idle_locked();
        fg_amd_wait_presents();
        release_fg();
        if (!create_fg(display.width, display.height, format, in.depth_reversed, in.far_z, max_w, max_h)) return false;
    }
    if (s.fg_w != display.width || s.fg_h != display.height || s.fg_format != format) {
        if (!told_size)
            told_size = true,
            logf("vk: AMD FG: the swapchain changed under the frame generation context (%ux%u format %d, context %ux%u format "
                 "%d): those frames are not generated", display.width, display.height, (int)format, s.fg_w, s.fg_h,
                 (int)s.fg_format);
        return false;
    }
    // (the context's largest render size: a scene larger than it is not generated from, as the reference does)
    bool use = have;
    if (use && (in.width > s.fg_desc.maxRenderSize.width || in.height > s.fg_desc.maxRenderSize.height)) {
        if (!told_big)
            told_big = true,
            logf("vk: AMD FG: a %ux%u scene is larger than the context's %ux%u: those frames are not generated", in.width,
                 in.height, s.fg_desc.maxRenderSize.width, s.fg_desc.maxRenderSize.height);
        use = false;
    }
    // (the menu is drawn into the same picture: generated, it would warp. Its own frames are shown as they are)
    const bool on = use && !menu_is_open();
    ffxConfigureDescFrameGeneration cfg{};
    cfg.header.type = FFX_API_CONFIGURE_DESC_TYPE_FRAMEGENERATION;
    cfg.swapChain = (void*)sc;
    cfg.frameGenerationCallback = generate;
    cfg.frameGenerationCallbackUserContext = &s.fg;
    cfg.frameGenerationEnabled = on;
    cfg.allowAsyncWorkloads = false;
    cfg.generationRect = {0, 0, (int32_t)display.width, (int32_t)display.height};
    cfg.frameID = ++s.frame_id;
    // (no HUD-less picture yet: the whole picture is interpolated, the HUD and this menu's overlays included. The UI
    // resource is P2's next step; measured as it is first. HUDLessColor stays empty, which the SDK takes as "none")
    ffxReturnCode_t r = s.configure(&s.fg, &cfg.header);
    if (r != FFX_API_RETURN_OK) {
        s.gen_failed = true;   // (the context stays: nothing more is sent, the swapchain shows the frames as they are)
        logf("vk: AMD FG: generation configuration failed (%u): the frames are not generated", (unsigned)r);
        return false;
    }
    if (!on) {
        s.prepared = false;
        return true;
    }
    const int64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                               std::chrono::steady_clock::now().time_since_epoch()).count();
    double dt = s.frame_ns ? (now_ns - s.frame_ns) / 1e6 : 16.67;
    s.frame_ns = now_ns;
    if (!(dt > 0.0 && dt < 100.0)) dt = 16.67;
    ffxDispatchDescFrameGenerationPrepareV2 p{};
    p.header.type = FFX_API_DISPATCH_DESC_TYPE_FRAMEGENERATION_PREPARE_V2;
    p.frameID = s.frame_id;
    p.commandList = cmd;
    p.renderSize = {in.width, in.height};
    p.jitterOffset = {in.jitter[0], in.jitter[1]};
    p.motionVectorScale = {1.0f, 1.0f};   // (the chain's motion: render pixels, towards the frame before)
    p.frameTimeDelta = (float)dt;
    p.reset = in.reset || !s.prepared;
    p.cameraNear = in.near_z > 0.0f ? in.near_z : 0.1f;
    p.cameraFar = in.far_z > 0.0f ? in.far_z : 1e8f;
    p.cameraFovAngleVertical = in.fov_y > 0.0f ? in.fov_y : 1.0f;
    p.viewSpaceToMetersFactor = 1.0f;
    p.depth = image_resource(in.depth, in.depth_format, in.width, in.height);
    p.motionVectors = image_resource(in.motion, in.motion_format, in.width, in.height);
    // (the camera's axes, which FSR Frame Generation 4 takes: the chain has no world-space camera; a camera at the
    // origin looking down -z, as the reference does without one)
    p.cameraUp[1] = 1.0f, p.cameraRight[0] = 1.0f, p.cameraForward[2] = -1.0f;
    r = s.dispatch(&s.fg, &p.header);
    if (r != FFX_API_RETURN_OK) {
        s.gen_failed = true;
        logf("vk: AMD FG: preparation failed (%u): the frames are not generated", (unsigned)r);
        return false;
    }
    s.prepared = true;
    return true;
}

void fg_amd_surface_lost() {
    State& s = st();
    if (!s.sc) return;
    wait_presents();
    release_fg();   // (the SDK's order: the frame generation context first, then the swapchain's)
    // (the SDK's order: its presents waited for, the frame generation context, then the swapchain context, then the
    // destroy function it gave -- the swapchain outlives the context and is not destroyed with it)
    const VkSwapchainKHR handle = s.handle;
    const PFN_vkDestroySwapchainFFXAPI destroy_swapchain = s.fn.pOutDestroySwapchainFFXAPI;
    s.destroy(&s.sc, nullptr);
    s.sc = nullptr;
    s.handle = VK_NULL_HANDLE;
    if (handle && destroy_swapchain) destroy_swapchain(dev.device, handle, nullptr, nullptr);
    s.fn = {};
}

VkResult fg_amd_get_images(VkSwapchainKHR sc, uint32_t* count, VkImage* images) {
    State& s = st();
    if (!s.sc) return VK_ERROR_FEATURE_NOT_PRESENT;
    return s.fn.pOutGetSwapchainImagesKHR(dev.device, sc, count, images);
}

VkResult fg_amd_acquire(VkSwapchainKHR sc, uint64_t timeout, VkFence fence, uint32_t* index) {
    State& s = st();
    if (!s.sc) return VK_ERROR_FEATURE_NOT_PRESENT;
    // (OcaDim) the fence, as the engine's plain acquire signals it, and no semaphore: image_free waits on that fence before
    // the frame's copy goes into the image. A semaphore there (the merge's first try) was never waited on, so image_free
    // timed out every present, the image stayed held, and the window showed nothing
    return s.fn.pOutAcquireNextImageKHR(dev.device, sc, timeout, VK_NULL_HANDLE, fence, index);
}

VkResult fg_amd_present(const VkPresentInfoKHR* present) {
    State& s = st();
    if (!s.sc) return VK_ERROR_FEATURE_NOT_PRESENT;
    const VkResult r = s.fn.pOutQueuePresentKHR(dev.fg_game_queue, present);
    // (a line a minute of play at 60: what AMD's swapchain shows, for the test's log beside RX_VK_FRAME_LOG)
    if (++s.presents == 120 || s.presents % 3600 == 0) {
        const uint64_t shown = s.fn.pOutGetLastPresentCountFFXAPI && present->swapchainCount
                                   ? s.fn.pOutGetLastPresentCountFFXAPI(present->pSwapchains[0])
                                   : 0;
        logf("vk: AMD FG: %llu presents by AMD's swapchain, %llu shown, %llu generated", (unsigned long long)s.presents,
             (unsigned long long)shown, (unsigned long long)s.generated);
    }
    return r;
}

}  // namespace mkwvk

#else   // (_WIN32)

namespace mkwvk {

bool fg_amd_requested() { return false; }
bool fg_amd_wanted() { return false; }
bool fg_amd_active() { return false; }
bool fg_amd_generating() { return false; }
VkResult fg_amd_create_swapchain(const VkSwapchainCreateInfoKHR&, VkSwapchainKHR*) { return VK_ERROR_FEATURE_NOT_PRESENT; }
void fg_amd_wait_presents() {}
void fg_amd_surface_lost() {}
VkResult fg_amd_get_images(VkSwapchainKHR, uint32_t*, VkImage*) { return VK_ERROR_FEATURE_NOT_PRESENT; }
VkResult fg_amd_acquire(VkSwapchainKHR, uint64_t, VkFence, uint32_t*) { return VK_ERROR_FEATURE_NOT_PRESENT; }
VkResult fg_amd_present(const VkPresentInfoKHR*) { return VK_ERROR_FEATURE_NOT_PRESENT; }
bool fg_amd_frame(VkCommandBuffer, VkSwapchainKHR, VkFormat, VkExtent2D, uint32_t, uint32_t) { return false; }

}  // namespace mkwvk

#endif
