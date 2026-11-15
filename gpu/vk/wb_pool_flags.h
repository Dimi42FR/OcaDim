// (longshot) Which of the game's memory pools the CPU can read GPU writes from without telling NVN first, from the flags the
// pool was made with (nvnMemoryPoolBuilderSetFlags): what decides whether a written binding's write-back may be left out
// (RX_VK_WB_MAX_KB, wb_learn.h).
//
// NVN's CPU-cached pools (NVN_MEMORY_POOL_FLAGS_CPU_CACHED) need nvnMemoryPoolInvalidateMappedRange before the CPU reads what the
// GPU wrote, and the renderer hears every invalidate (vk_replay.cpp invalidate, memory_note_cpu_read): the learned leave-out sees
// all of those reads. Pools with no CPU access (CPU_NO_ACCESS) are never read by the CPU at all. Uncached pools (CPU_UNCACHED)
// are read with no call to NVN, so a left-out write-back there is found stale with nothing to learn from: the reason the cap was
// off for everyone. In Kokiri Forest 3,368 of the 4,588 pools the game made were CPU-cached (3.6 GB), and the import that took
// most of the write-back (about 5.6 MB of each submission's 6.8) was 126 MB of cached pools and 0.4 MB of uncached ones.
//
// Plain rules, no locking and no Vulkan: vk_memory.cpp holds a Map under its own mutex. tests/test_wb_pool_flags.py runs them.
#pragma once
#include <cstdint>
#include <iterator>
#include <map>

namespace wb_pool_flags {

constexpr uint32_t kCpuNoAccess = 0x1, kCpuUncached = 0x2, kCpuCached = 0x4;   // (NVN_MEMORY_POOL_FLAGS_CPU_*)

// The CPU access a pool's flags give: what a range in it needs before its write-back may be left out
enum Access : uint8_t { kUnknown, kUncached, kCached, kNoAccess };
inline Access access_of(uint32_t flags) {
    if (flags & kCpuUncached) return kUncached;   // (read with no call: never left out)
    if (flags & kCpuCached) return kCached;
    if (flags & kCpuNoAccess) return kNoAccess;
    return kUnknown;   // (no CPU bit: NVN's default is uncached, so treated as such)
}

// The game's pools by guest address, as they are made (a pool made over an older one's range replaces it there)
class Map {
public:
    void add(uint64_t lo, uint64_t hi, uint32_t flags) {
        if (hi <= lo) return;
        auto it = pools_.lower_bound(lo);
        if (it != pools_.begin() && std::prev(it)->second.hi > lo) --it;
        while (it != pools_.end() && it->first < hi) {   // (overlapped: cut down to the parts outside [lo, hi))
            const uint64_t plo = it->first, phi = it->second.hi;
            const uint32_t pf = it->second.flags;
            it = pools_.erase(it);
            if (plo < lo) pools_[plo] = {lo, pf};
            if (phi > hi) {
                pools_[hi] = {phi, pf};
                break;
            }
        }
        pools_[lo] = {hi, flags};
        if (pools_.size() > kMax) pools_.erase(pools_.begin());   // (bounded: the oldest addresses go first, read as unknown)
    }
    // The access the whole of [lo, hi) has: kUncached when any part of it is uncached or not covered by a known pool, else
    // kCached when any part is cached, else kNoAccess
    Access range(uint64_t lo, uint64_t hi) const {
        if (hi <= lo) return kUnknown;
        auto it = pools_.upper_bound(lo);
        if (it == pools_.begin()) return kUnknown;
        --it;
        Access a = kNoAccess;
        uint64_t at = lo;
        while (at < hi) {
            if (it == pools_.end() || it->first > at || it->second.hi <= at) return kUnknown;   // (a gap: no pool known there)
            const Access p = access_of(it->second.flags);
            if (p == kUncached || p == kUnknown) return p;
            if (p == kCached) a = kCached;
            at = it->second.hi;
            ++it;
        }
        return a;
    }
    // Whether a written binding over [lo, hi) may go without its write-back: the CPU reads none of it without an invalidate
    bool may_leave_out(uint64_t lo, uint64_t hi) const {
        const Access a = range(lo, hi);
        return a == kCached || a == kNoAccess;
    }
    size_t size() const { return pools_.size(); }

private:
    struct Pool { uint64_t hi; uint32_t flags; };
    static constexpr size_t kMax = 65536;
    std::map<uint64_t, Pool> pools_;
};

}  // namespace wb_pool_flags
