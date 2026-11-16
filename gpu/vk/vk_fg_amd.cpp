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

#ifdef _WIN32
#include <windows.h>

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
    ffxContext sc = nullptr;   // (the swapchain context)
    VkSwapchainKHR handle = VK_NULL_HANDLE;   // (the swapchain it made: remade in place, destroyed after the context)
    ffxQueryDescSwapchainReplacementFunctionsVK fn{};
    // (what the context was made from, kept as the SDK asks)
    ffxCreateContextDescFrameGenerationSwapChainVK desc{};
    ffxCreateContextDescFrameGenerationSwapChainVersionVK version{};
    uint64_t presents = 0;   // (what the swapchain says it presented, for the log)
};
State& st() {
    static State& s = *new State;
    return s;
}

bool env_on() {
    static const bool on = [] {
        const char* e = getenv("RX_VK_FG_AMD");
        return e && *e && atoi(e) != 0;
    }();
    return on;
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
    if (!s.create || !s.destroy || !s.query || !s.dispatch) {
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

}  // namespace

bool fg_amd_requested() { return env_on(); }

bool fg_amd_active() { return st().sc != nullptr; }

VkResult fg_amd_create_swapchain(const VkSwapchainCreateInfoKHR& ci, VkSwapchainKHR* out) {
    State& s = st();
    if (!env_on() || s.failed) return VK_ERROR_FEATURE_NOT_PRESENT;
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

void fg_amd_surface_lost() {
    State& s = st();
    if (!s.sc) return;
    wait_presents();
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

VkResult fg_amd_acquire(VkSwapchainKHR sc, uint64_t timeout, VkSemaphore semaphore, uint32_t* index) {
    State& s = st();
    if (!s.sc) return VK_ERROR_FEATURE_NOT_PRESENT;
    return s.fn.pOutAcquireNextImageKHR(dev.device, sc, timeout, semaphore, VK_NULL_HANDLE, index);
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
        logf("vk: AMD FG: %llu presents by AMD's swapchain, %llu shown", (unsigned long long)s.presents, (unsigned long long)shown);
    }
    return r;
}

}  // namespace mkwvk

#else   // (_WIN32)

namespace mkwvk {

bool fg_amd_requested() { return false; }
bool fg_amd_active() { return false; }
VkResult fg_amd_create_swapchain(const VkSwapchainCreateInfoKHR&, VkSwapchainKHR*) { return VK_ERROR_FEATURE_NOT_PRESENT; }
void fg_amd_wait_presents() {}
void fg_amd_surface_lost() {}
VkResult fg_amd_get_images(VkSwapchainKHR, uint32_t*, VkImage*) { return VK_ERROR_FEATURE_NOT_PRESENT; }
VkResult fg_amd_acquire(VkSwapchainKHR, uint64_t, VkSemaphore, uint32_t*) { return VK_ERROR_FEATURE_NOT_PRESENT; }
VkResult fg_amd_present(const VkPresentInfoKHR*) { return VK_ERROR_FEATURE_NOT_PRESENT; }

}  // namespace mkwvk

#endif
