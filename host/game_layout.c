/* The game folder's two folders of what the game makes as it runs (game_layout.h):
   - cache/: the shader and pipeline caches (the program cache, the pipeline notes and lists, the Vulkan pipeline cache and its
     play files, the prepare's record, the driver's faults) and the button prompts made from the player's controls (cache/prompts,
     host/prompts.c). Made for this build and this GPU, several GB: its name says it can be deleted, and the next start makes it
     again;
   - logs/: ocadim_log.txt and the runs before it, and the other logs and traces a run writes.
   Both are made at the start, before anything writes there; the renderer finds them by gpu/vk/vk_paths.h's cache_path and
   log_path. What a build from before left loose beside the game is moved into them once: renames in the same folder, never over
   a file already there (one that cannot move stays, and the log says so). A file a build before OcaDim's rename left under its
   old name (longshot_*) is renamed to its ocadim_* one, in the game folder or in cache/ and logs/, so the player keeps the
   shader caches and the settings survive the change; the Vulkan pipeline cache is renamed on the way, from mkw-recomp's
   mkw_vk_pipelines*.bin and the merge's longshot_vk_pipelines*.bin to ocadim_vk_pipelines*.bin, and what a write of it cut short
   left (a .tmp) is deleted; the button prompts an older build made in prompts/ are deleted, as they are made again in
   cache/prompts. The build's own files stay where the build put them (image.bin, romfs, ocadim_shaders.bin, the shipped pipeline
   list, prompts/<face>/, texts/, language.txt), and so do the settings (ocadim_options.ini; in the user folder when --user names
   one: host/options_path.c), ocadim_env.txt and the saves (user/). */
#include "hos_paths.h"   /* (first: windows.h, host/posix's on Linux) */
#include <stdio.h>
#include <string.h>
#include "game_layout.h"

#ifdef _WIN32
#define SEP_S "\\"
#else
#define SEP_S "/"
#endif

void hos_log(const char *fmt, ...);   /* (hos.h; declared here so tests/test_game_layout.py builds this file alone) */

/* The logs into logs/, the caches into cache/ */
static const char *const to_logs[] = {
    "ocadim_log.txt", "ocadim_log.1.txt", "ocadim_log.2.txt", "ocadim_log.3.txt", "ocadim_log.4.txt",
    "ocadim_startup.log", "ocadim_frames.csv",
};
static const char *const to_cache[] = {
    "ocadim_programs.bin", "ocadim_programs.idx", "ocadim_programs.zst.bin", "ocadim_programs.zst.idx",
    "ocadim_module_ids.bin", "ocadim_pipelines.bin", "ocadim_pipelines.bin.predicted",
    "ocadim_pipelines.bin.predicted_keys", "ocadim_pipelines.bin.built", "ocadim_pipelines.bin.running",
    "ocadim_pipelines.bin.predicting", "ocadim_pipelines.bin.built.warming", "ocadim_computes.bin",
    "ocadim_compute_variants.bin", "ocadim_pipeline_states.bin", "ocadim_pipeline_states_v1.bin", "ocadim_prepared.bin",
    "ocadim_prepared.bin.warming", "ocadim_prepare_skipped", "ocadim_driver_faults.txt", "ocadim_load_start.txt",
    "ocadim_load_start.txt.waited",
};
/* The Vulkan pipeline cache, mkw_vk_pipelines.bin and the merge's longshot_vk_pipelines*.bin, its stamp and its play files
   (mkw-recomp's and Longshot's names), renamed ocadim_vk_pipelines* as they move into cache/ (gpu/vk/vk_draw.cpp,
   pcache_stamp.h) */
static const char new_pcache[] = "ocadim_vk_pipelines";
/* The program cache's lock files beside it (gpu/vk/vk_progcache.cpp): the game locks cache/'s now, and nothing holds these: deleted */
static const char *const old_locks[] = {"ocadim_programs.bin.lock", "ocadim_programs.zst.bin.lock"};
/* Made from the player's choices and made again when missing (host/prompts.c): deleted from the game folder */
static const char *const made_again[] = {
    "prompts" SEP_S "Common.bntx.zs", "prompts" SEP_S "Common.blarc.zs", "prompts" SEP_S "Common.key",
    "prompts" SEP_S "Common.blarc.key", "prompts" SEP_S "External.bfotf.zs", "prompts" SEP_S "rsizetable.mod.zs",
};

static int done, moved, kept;
static char kept_first[MAX_PATH];

static int exists(const char *p) { return GetFileAttributesA(p) != INVALID_FILE_ATTRIBUTES; }
static int is_dir(const char *p) {
    const DWORD a = GetFileAttributesA(p);
    return a != INVALID_FILE_ATTRIBUTES && (a & FILE_ATTRIBUTE_DIRECTORY);
}

/* the name a build before the rename used for one of ours: ocadim_x was longshot_x */
static void old_name(const char *name, char *out, size_t cap) {
    if (!strncmp(name, "ocadim_", 7)) snprintf(out, cap, "longshot_%s", name + 7);
    else snprintf(out, cap, "%s", name);
}

/* game's file name into dir (both with their separator) as as: never over one there, never a folder */
static void move_as(const char *game, const char *name, const char *dir, const char *as) {
    char from[MAX_PATH], to[MAX_PATH];
    if (snprintf(from, sizeof from, "%s%s", game, name) >= (int)sizeof from || !exists(from) || is_dir(from)) return;
    if (snprintf(to, sizeof to, "%s%s", dir, as) >= (int)sizeof to) return;
    if (!exists(to) && MoveFileExA(from, to, 0)) {
        moved++;
        return;
    }
    if (!kept++) snprintf(kept_first, sizeof kept_first, "%s", from);
}

/* a file of the old name already in dir, renamed to its new one there (never over one): the caches and logs an install from
   before the rename already has in cache/ and logs/ */
static void rename_old(const char *dir, const char *name) {
    char old[128], from[MAX_PATH], to[MAX_PATH];
    old_name(name, old, sizeof old);
    if (!strcmp(old, name)) return;
    if (snprintf(from, sizeof from, "%s%s", dir, old) >= (int)sizeof from ||
        snprintf(to, sizeof to, "%s%s", dir, name) >= (int)sizeof to)
        return;
    if (exists(from) && !exists(to) && !is_dir(from) && MoveFileExA(from, to, 0)) moved++;
}

/* a file of the old name left loose in the game folder: gone once the new name is in its folder (the old copy is only a
   duplicate then), or when no new one was there to take its place and it could not move */
static void drop_old(const char *game, const char *name) {
    char old[128], path[MAX_PATH];
    old_name(name, old, sizeof old);
    if (!strcmp(old, name)) return;
    if (snprintf(path, sizeof path, "%s%s", game, old) >= (int)sizeof path) return;
    DeleteFileA(path);
}

/* the files of dir whose names start with prefix and end with suffix: moved into to_dir under the new prefix (rename: 1),
   or deleted */
static void each_prefix(const char *dir, const char *to_dir, const char *prefix, const char *suffix, int rename) {
    char pattern[MAX_PATH];
    if (snprintf(pattern, sizeof pattern, "%s%s*%s", dir, prefix, suffix) >= (int)sizeof pattern) return;
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA(pattern, &fd);
    if (h == INVALID_HANDLE_VALUE) return;
    const size_t plen = strlen(prefix);
    do {
        if (strncmp(fd.cFileName, prefix, plen)) continue;
        if (rename) {
            char as[MAX_PATH];
            snprintf(as, sizeof as, "%s%s", new_pcache, fd.cFileName + plen);
            move_as(dir, fd.cFileName, to_dir, as);
        } else {
            char path[MAX_PATH];
            snprintf(path, sizeof path, "%s%s", dir, fd.cFileName);
            DeleteFileA(path);
        }
    } while (FindNextFileA(h, &fd));
    FindClose(h);
}

void hos_game_layout(void) {
    if (done) return;
    done = 1;
    char game[MAX_PATH], cache[MAX_PATH], logs[MAX_PATH], prompts[MAX_PATH];
    DWORD n = hos_game_path_a(game, MAX_PATH);
    if (!n || n >= MAX_PATH) return;
    while (n && game[n - 1] != '\\' && game[n - 1] != '/') n--;
    if (!n) return;
    game[n] = 0;   /* (the game folder, with its separator) */
    if (snprintf(cache, sizeof cache, "%scache" SEP_S, game) >= (int)sizeof cache ||
        snprintf(logs, sizeof logs, "%slogs" SEP_S, game) >= (int)sizeof logs ||
        snprintf(prompts, sizeof prompts, "%scache" SEP_S "prompts", game) >= (int)sizeof prompts)
        return;
    CreateDirectoryA(cache, NULL);
    CreateDirectoryA(logs, NULL);
    CreateDirectoryA(prompts, NULL);
    for (size_t i = 0; i < sizeof to_logs / sizeof *to_logs; i++) {
        char old[128];
        old_name(to_logs[i], old, sizeof old);
        move_as(game, to_logs[i], logs, to_logs[i]);
        move_as(game, old, logs, to_logs[i]);
        rename_old(logs, to_logs[i]);
        drop_old(game, to_logs[i]);
    }
    for (size_t i = 0; i < sizeof to_cache / sizeof *to_cache; i++) {
        char old[128];
        old_name(to_cache[i], old, sizeof old);
        move_as(game, to_cache[i], cache, to_cache[i]);
        move_as(game, old, cache, to_cache[i]);
        rename_old(cache, to_cache[i]);
        drop_old(game, to_cache[i]);
    }
    /* (the shader seed and the shipped pipeline list beside the game: an install from before the rename keeps them) */
    rename_old(game, "ocadim_shaders.bin");
    rename_old(game, "ocadim_pipeline_states_shipped.bin");
    /* (the Vulkan pipeline cache: mkw-recomp's and the merge's names, loose or already in cache/) */
    each_prefix(game, cache, "mkw_vk_pipelines", ".bin", 1);
    each_prefix(game, cache, "longshot_vk_pipelines", ".bin", 1);
    each_prefix(cache, cache, "longshot_vk_pipelines", ".bin", 1);
    move_as(game, "mkw_vk_pipelines.stamp", cache, "ocadim_vk_pipelines.stamp");
    rename_old(cache, "ocadim_vk_pipelines.stamp");
    each_prefix(game, cache, "mkw_vk_pipelines", ".tmp", 0);     /* (a write cut short: never read) */
    each_prefix(game, cache, "mkw_vk_pipelines", ".tmp-*", 0);   /* (one with its writer's own name, gpu/vk/pipeline_cache_file.h) */
    each_prefix(game, cache, "longshot_vk_pipelines", ".tmp", 0);
    each_prefix(game, cache, "longshot_vk_pipelines", ".tmp-*", 0);
    for (size_t i = 0; i < sizeof old_locks / sizeof *old_locks; i++) {
        char path[MAX_PATH], old[128];
        snprintf(path, sizeof path, "%s%s", game, old_locks[i]);
        DeleteFileA(path);
        old_name(old_locks[i], old, sizeof old);
        snprintf(path, sizeof path, "%s%s", game, old);
        DeleteFileA(path);
    }
    for (size_t i = 0; i < sizeof made_again / sizeof *made_again; i++) {
        char path[MAX_PATH];
        snprintf(path, sizeof path, "%s%s", game, made_again[i]);
        DeleteFileA(path);
    }
}

void hos_game_layout_log(void) {
    if (moved) hos_log("game folder: %d logs and shader caches moved or renamed into its logs and cache folders", moved);
    if (kept) hos_log("game folder: %d files stayed where they were (one of that name was there already): %s, ...", kept, kept_first);
}
