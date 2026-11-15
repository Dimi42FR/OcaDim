// (longshot) How many workers the parallel replay takes from the logical processors the process may run on, when RX_VK_PARALLEL
// says nothing: one for every four, never more than four, and none under six, where a small machine keeps every core for the game.
// One rule, in one place: gpu/vk/vk_replay.cpp's par_threads reads it, the log names what it picked, and
// tests/test_parallel_workers.py compiles this file alone and checks the mapping (a 4-core machine starved is the thing this
// rule exists to avoid, so it is checked, not said).
#pragma once

namespace mkwvk::par {

/// The workers for `cpus` logical processors the process may run on (its affinity mask; 0 or unknown: none)
constexpr int workers(unsigned cpus) {
    if (cpus < 6) return 0;                 // (4 cores or fewer: the game keeps them all)
    return (int)(cpus / 4 > 4 ? 4 : cpus / 4);   // (6 -> 1, 8 -> 2, 12 -> 3, 16 and more -> 4)
}

/// The descriptor prefetch's own thread is worth it from six processors: under it, it would take a core the game needs
constexpr bool prefetch(unsigned cpus) { return cpus >= 6; }

} // namespace mkwvk::par
