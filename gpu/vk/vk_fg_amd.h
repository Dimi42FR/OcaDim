// (longshot) AMD FSR Frame Generation's swapchain, first step (P1): with RX_VK_FG_AMD=1, AMD's frame generation
// swapchain takes the place of the window's, and every swapchain call goes through the functions it hands back.
// Nothing is generated yet: no frame generation context and no dispatch. This step only proves that AMD's swapchain
// shows the renderer's image as the plain one does; the configuration, the generated frames and the UI follow.
//
// Off, or refused at any point (no library, no second queue, no context), the real Vulkan functions stay in place and
// the present path is the one without it, unchanged. Every function here is safe to call with the feature off.
#pragma once

#include <cstdint>

#include "vk_loader.h"   // (Vulkan with the platform's surface types, as every file of the back end sees it)

namespace mkwvk {

/// (longshot) The menu's Frame generation by at AMD FSR FG (2), or RX_VK_FG_AMD=1 / 0 over it: asked for. (Read each time:
/// the row applies at once. Not a promise that it runs.)
bool fg_amd_requested();

/// (longshot) And it can run here: asked for, Windows, an AMD GPU. False: the plain swapchain and the renderer's own frames
bool fg_amd_wanted();

/// AMD's swapchain owns the window's handle: every swapchain call must go through fg_amd_get_images / fg_amd_acquire /
/// fg_amd_present, never through the Vulkan ones.
bool fg_amd_active();
int fg_amd_major();   // (OcaDim) 4 or 3: the frame generation version the context was made with, 0 before one is

/// And its frame generation context is in place: the frames between the game's are AMD's (the FPS counter's maker name)
bool fg_amd_generating();

/// The swapchain for ci, AMD's when it can be made. VK_ERROR_FEATURE_NOT_PRESENT: not asked for, not available, or it
/// refused before a swapchain existed: the caller makes the plain one. Any other result: AMD's context is in place and
/// the caller must not touch the handle with the Vulkan functions.
VkResult fg_amd_create_swapchain(const VkSwapchainCreateInfoKHR& ci, VkSwapchainKHR* out);

/// AMD's presents done: its own dispatch asks for it before the swapchain is remade or taken down. The app's semaphores
/// they wait on must not be destroyed before it.
void fg_amd_wait_presents();

/// The surface is gone, or the swapchain made here cannot be used: AMD's presents are waited for, then its context and
/// the swapchain it made are destroyed, in the SDK's order (the context first, its destroy function last). The handle is
/// invalid afterwards; the caller only drops its own state.
void fg_amd_surface_lost();

VkResult fg_amd_get_images(VkSwapchainKHR sc, uint32_t* count, VkImage* images);
/// (OcaDim) its acquire takes the engine's acquire fence, as the plain swapchain's does: image_free waits on that fence
/// before the frame's copy is recorded into the image, so a semaphore there left the image held and nothing was ever shown
VkResult fg_amd_acquire(VkSwapchainKHR sc, uint64_t timeout, VkFence fence, uint32_t* index);
VkResult fg_amd_present(const VkPresentInfoKHR* present);

/// (P2) One game frame's frame generation: the frame's command buffer gets AMD's preparation (depth, motion, camera),
/// and the configuration the swapchain's present uses to generate between this frame and the one before. Called once a
/// frame right after the picture is recorded, before the submit; true when the frame was configured (generation on or
/// off, its inputs being there or not). No-op without AMD's swapchain. src_w x src_h: the picture's size (the game's
/// output, which may be larger than the window); the context's largest render size follows it.
bool fg_amd_frame(VkCommandBuffer cmd, VkSwapchainKHR sc, VkFormat format, VkExtent2D display, uint32_t src_w, uint32_t src_h);

}  // namespace mkwvk
