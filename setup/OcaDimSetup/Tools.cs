using System.Globalization;
using System.IO.Compression;
using System.Security.Cryptography;

namespace OcaDimSetup;

/// One line of tools.lock (`tool <name> <version> <system> <sha256> <size> <dest> <prefix> <url>...`). Dest is where the
/// tool becomes in a builder install: LongshotBuilder/tools/<folder>, whose last part is the folder under our tools\.
sealed record BuildTool(string Name, string Version, string Sha256, long Size, string Dest, string Prefix, string[] Urls);

/// tools.lock and the tools it names (docs/releases.md): the Windows builder's setup (builder/setup/setup.c) and
/// builder/linux/linux_tools.py read the same lines. What this adds is the wizard's progress and a resumable download.
static class ToolsLock
{
    public const string System = "windows-x64";

    public static List<BuildTool> Read(string path)
    {
        var tools = new List<BuildTool>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var raw in File.ReadAllLines(path))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith('#')) continue;
            if (!line.StartsWith("tool ", StringComparison.Ordinal))
                throw new FormatException("tools.lock: a line that is neither a comment nor a tool: " + line);
            var p = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (p.Length < 9) throw new FormatException("tools.lock: a tool line is short of a field: " + line);
            if (p[3] != System) continue;                       // (linux-x64's lines are the AppImage's)
            if (p[4].Length != 64 || p[4] != p[4].ToLowerInvariant())
                throw new FormatException("tools.lock: " + p[1] + "'s SHA-256 is not 64 lowercase hex digits");
            if (!long.TryParse(p[5], NumberStyles.None, CultureInfo.InvariantCulture, out var size) || size <= 0)
                throw new FormatException("tools.lock: " + p[1] + "'s size is not a positive number");
            if (!seen.Add(p[1])) throw new FormatException("tools.lock: " + p[1] + " is named twice");
            if (!p[6].StartsWith("LongshotBuilder/tools/", StringComparison.Ordinal))
                throw new FormatException("tools.lock: " + p[1] + "'s dest is not under LongshotBuilder/tools/: " + p[6]);
            var urls = p.Skip(8).ToArray();
            if (urls.Length == 0 || urls.Any(u => !u.StartsWith("https://", StringComparison.OrdinalIgnoreCase)))
                throw new FormatException("tools.lock: " + p[1] + " has no https URL");
            tools.Add(new BuildTool(p[1], p[2], p[4], size, p[6], p[7], urls));
        }
        return tools;
    }
}

/// The tools a build needs, in <tools>\, downloaded once and kept for every later build (tools.lock's SHAs are the
/// stamps: a tool whose stamp matches is not fetched again). One download at a time, the ways scripts/tools.py has.
sealed class ToolInstaller
{
    readonly string root;                 // <install>\tools: python\, llvm-mingw\, cpm\, wgpu-native\, third_party\
    readonly List<BuildTool> tools;
    readonly Action<string> line;

    public ToolInstaller(string root, List<BuildTool> tools, Action<string> line)
    {
        this.root = root;
        this.tools = tools;
        this.line = line;
    }

    public bool AllPresent => tools.All(Present);

    public string FolderOf(BuildTool tool) =>
        Path.Combine(root, tool.Dest.TrimEnd('/').Split('/').Last());   // (third-party → third_party, as the build reads it)
    string StampPath(BuildTool tool) => Path.Combine(FolderOf(tool), ".ocadim-tool");
    string ArchivePath(BuildTool tool) => Path.Combine(root, ".downloads", tool.Name + "-" + tool.Sha256[..12] + ".zip");

    bool Present(BuildTool tool)
    {
        try
        {
            // (the stamp lives in the tool's own folder: a source folder of the same name, which has none, is not a tool)
            return File.Exists(StampPath(tool)) && File.ReadAllText(StampPath(tool)).Trim() == tool.Sha256;
        }
        catch (IOException) { return false; }
    }

    /// Copies a tool an earlier install (or the developer's HookshotBuilder tools) already holds, with its stamp: no
    /// download, the same files. OCADIM_TOOLS_FROM, or --tools-from in the CLI.
    public void Seed(string seedRoot)
    {
        foreach (var tool in tools)
        {
            if (Present(tool)) continue;
            var from = FolderOf(tool);   // (the seed root has the same layout: python\, llvm-mingw\, third_party\)
            from = Path.Combine(seedRoot, Path.GetFileName(from));
            if (!Directory.Exists(from)) continue;
            line(string.Format(CultureInfo.InvariantCulture, "{0}: taken from {1}", tool.Name, from));
            CopyTree(from, FolderOf(tool));
            WriteStamp(tool);
        }
    }

    /// <summary>Downloads and unpacks what is missing. progress: (overall 0..1, "name, part 2 of 5").</summary>
    public async Task InstallAsync(Action<double, string> progress, CancellationToken cancel)
    {
        using var http = new HttpClient { Timeout = TimeSpan.FromMinutes(60) };
        http.DefaultRequestHeaders.UserAgent.ParseAdd("OcaDimSetup/0.0.2");
        var todo = tools.Where(t => !Present(t)).ToList();
        if (todo.Count == 0)
        {
            line("The build tools are all here: nothing to download.");
            progress(1.0, "Outils déjà installés");
            return;
        }
        long totalBytes = todo.Sum(t => t.Size), doneBytes = 0;
        for (int i = 0; i < todo.Count; i++)
        {
            var tool = todo[i];
            cancel.ThrowIfCancellationRequested();
            var archive = ArchivePath(tool);
            Directory.CreateDirectory(Path.GetDirectoryName(archive)!);
            if (!await ArchiveIsGoodAsync(archive, tool, cancel))
            {
                var got = await FetchAsync(http, tool, archive, fraction =>
                {
                    var overall = totalBytes == 0 ? 0 : (doneBytes + (long)(fraction * tool.Size)) / (double)totalBytes;
                    progress(overall, string.Format(CultureInfo.InvariantCulture, "{0} {1} · {2:0}%", tool.Name, tool.Version, fraction * 100));
                }, cancel);
                if (!got) throw new InvalidOperationException(
                    "Le téléchargement de " + tool.Name + " a échoué. Vérifiez la connexion, ou réessayez : le dossier garde ce qui est déjà là.");
            }
            progress(totalBytes == 0 ? 0 : Math.Min(1.0, (doneBytes + tool.Size) / (double)totalBytes), "Décompression de " + tool.Name);
            Unpack(archive, tool);
            WriteStamp(tool);
            doneBytes += tool.Size;
            line(string.Format(CultureInfo.InvariantCulture, "{0} {1}: {2}", tool.Name, tool.Version, FolderOf(tool)));
        }
        progress(1.0, "Outils installés");
    }

    static async Task<bool> ArchiveIsGoodAsync(string archive, BuildTool tool, CancellationToken cancel)
    {
        if (!File.Exists(archive)) return false;
        if (new FileInfo(archive).Length != tool.Size) return false;
        return await HashAsync(archive, cancel) == tool.Sha256;
    }

    /// The first URL that answers with the bytes tools.lock names (docs/releases.md: the store's copy, then the forge's,
    /// then where it came from). Written beside and renamed in, so a broken download is never taken for the archive.
    async Task<bool> FetchAsync(HttpClient http, BuildTool tool, string archive, Action<double> progress, CancellationToken cancel)
    {
        foreach (var url in tool.Urls)
        {
            cancel.ThrowIfCancellationRequested();
            var part = archive + ".part";
            try
            {
                using var answer = await http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, cancel);
                if (!answer.IsSuccessStatusCode)
                {
                    line("  " + tool.Name + ": " + url + " → HTTP " + (int)answer.StatusCode);
                    continue;
                }
                var expected = answer.Content.Headers.ContentLength ?? tool.Size;
                await using (var source = await answer.Content.ReadAsStreamAsync(cancel))
                await using (var target = new FileStream(part, FileMode.Create, FileAccess.Write, FileShare.None, 1 << 16, true))
                {
                    var buffer = new byte[1 << 16];
                    long read = 0;
                    int n;
                    while ((n = await source.ReadAsync(buffer, cancel)) > 0)
                    {
                        cancel.ThrowIfCancellationRequested();
                        await target.WriteAsync(buffer.AsMemory(0, n), cancel);
                        read += n;
                        progress(expected <= 0 ? 0 : Math.Min(1.0, read / (double)expected));
                    }
                }
                if (new FileInfo(part).Length != tool.Size || await HashAsync(part, cancel) != tool.Sha256)
                {
                    line("  " + tool.Name + ": the file at " + url + " is not the one tools.lock names (size or SHA-256)");
                    File.Delete(part);
                    continue;
                }
                File.Move(part, archive, overwrite: true);
                return true;
            }
            catch (HttpRequestException e)
            {
                line("  " + tool.Name + ": " + url + " → " + e.Message);
                try { File.Delete(part); } catch (IOException) { }
            }
            catch (IOException e)
            {
                line("  " + tool.Name + ": " + url + " → " + e.Message);
                try { File.Delete(part); } catch (IOException) { }
            }
        }
        return false;
    }

    /// Unpacks the tool's <prefix> folder as <name>\: only what is inside, never a path that leaves the install.
    void Unpack(string archive, BuildTool tool)
    {
        var folder = FolderOf(tool);
        Directory.CreateDirectory(folder);
        var prefix = tool.Prefix == "-" ? "" : tool.Prefix.Trim('/').Replace('\\', '/') + "/";
        var rootFull = Path.GetFullPath(folder) + Path.DirectorySeparatorChar;
        using var zip = ZipFile.OpenRead(archive);
        foreach (var entry in zip.Entries)
        {
            var name = entry.FullName.Replace('\\', '/');
            if (prefix.Length > 0 && !name.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) continue;
            var relative = name[prefix.Length..];
            if (relative.Length == 0 || relative.EndsWith('/')) continue;
            if (relative.Split('/').Any(part => part is ".." or ".") || Path.IsPathRooted(relative))
                throw new InvalidDataException(tool.Name + "'s archive holds a path outside it: " + name);
            var target = Path.GetFullPath(Path.Combine(folder, relative.Replace('/', Path.DirectorySeparatorChar)));
            if (!target.StartsWith(rootFull, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException(tool.Name + "'s archive holds a path outside it: " + name);
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            entry.ExtractToFile(target, overwrite: true);
        }
    }

    void WriteStamp(BuildTool tool)
    {
        Directory.CreateDirectory(FolderOf(tool));
        File.WriteAllText(StampPath(tool), tool.Sha256 + "\n");
    }

    static void CopyTree(string from, string to)
    {
        Directory.CreateDirectory(to);
        foreach (var file in Directory.EnumerateFiles(from, "*", SearchOption.AllDirectories))
        {
            var target = Path.Combine(to, Path.GetRelativePath(from, file));
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            File.Copy(file, target, overwrite: true);
        }
    }

    public static async Task<string> HashAsync(string path, CancellationToken cancel)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20, true);
        var hash = await SHA256.HashDataAsync(stream, cancel);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    public static string Hash(string path)
    {
        using var stream = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
    }

}
