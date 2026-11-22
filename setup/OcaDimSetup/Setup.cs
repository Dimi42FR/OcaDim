using System.Diagnostics;
using System.Globalization;
using System.IO.Compression;
using System.Text;
using System.Text.RegularExpressions;

namespace OcaDimSetup;

sealed record CheckResult(bool Ok, string Text, string? Program, string? Build, string? Error);
sealed record BuildResult(int Code, string? Error, string Tail);

/// The wizard's state and the only three things it does: find the sources, fetch the tools, and run nx2/make_game.py.
/// No build logic lives here: if the script changes, the interface follows (docs/SETUP-OCADIM-DESIGN.md).
sealed class Setup
{
    public const string Name = "OcaDim";
    public const string Version = "0.0.6";
    public const string GameExe = "ocadim.exe";

    public string InstallDir { get; set; } = DefaultInstallDir;
    public string? Nup { get; private set; }
    public string? Romfs { get; private set; }
    public string? Exefs { get; private set; }
    public bool Fsr { get; set; } = true;   // (OcaDim) AMD FSR 4/3.1: on by default, it is the renderer's own upscaler and frame generation
    /// (OcaDim) NVIDIA's DLSS SDK, fetched before the build and shipped as ngx/ beside the game: DLSS, DLAA and DLSS Frame
    /// Generation live there. Without it the renderer is built without any of them, so an RTX card finds no DLSS and no
    /// NVIDIA frame generation at all — and the F1 menu shows no NVIDIA page.
    public bool Ngx { get; set; } = true;
    /// <summary>(OcaDim) "Compilation légère": one compiler at a time (Setup.cs JobsForPc). Slower, but a small PC with little
    /// RAM never runs out while it builds.</summary>
    public static bool Light;
    /// <summary>(OcaDim) "Télécharger les outils en ligne": skip the tools shipped with the Setup and fetch each one from
    /// tools.lock, as before. A way out when the local tools do not work on this PC.</summary>
    public static bool DownloadTools;
    /// (OcaDim) The hottest game functions compiled at -O2 with their callees inlined (nx2/make_game.py's hot list, from
    /// assets/profiles/), and the renderer built with its play profile: the CPU is this game's frame's wall. Off only if a
    /// build or the game misbehaves (the whole lifted code at -O1, as before). Added by Dimi42FR.
    public bool HotCode { get; set; } = true;
    public string? ToolsFrom { get; set; }          // (dev: take the tools from a folder that has them)

    public static string DefaultInstallDir =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), Name);

    public string ToolsDir => Path.Combine(InstallDir, "tools");
    public string WorkDir => Path.Combine(InstallDir, ".build");
    public string LogPath => Path.Combine(InstallDir, "build.log");
    public string VersionPath => Path.Combine(InstallDir, "version.txt");

    public bool Installed => File.Exists(Path.Combine(InstallDir, GameExe));
    public bool HasGame => Nup != null || (Romfs != null && Exefs != null);
    public string GameLabel => Nup != null ? Path.GetFileName(Nup) : "romfs + exefs";

    /// What the player chose: a .nup, or a folder holding romfs/ and exefs/ (or the two folders).
    public void Choose(string path)
    {
        if (Directory.Exists(path))
        {
            var romfs = Path.Combine(path, "romfs");
            var exefs = Path.Combine(path, "exefs");
            if (!Directory.Exists(romfs) || !Directory.Exists(exefs))
                throw new ArgumentException("Ce dossier n'a pas les deux sous-dossiers romfs et exefs.");
            Nup = null;
            Romfs = romfs;
            Exefs = exefs;
        }
        else if (File.Exists(path))
        {
            Nup = Path.GetFullPath(path);
            Romfs = Exefs = null;
        }
        else throw new FileNotFoundException("Fichier introuvable : " + path);
    }

    public void ChooseFolders(string romfs, string exefs)
    {
        if (!Directory.Exists(romfs)) throw new DirectoryNotFoundException("Dossier romfs introuvable : " + romfs);
        if (!Directory.Exists(exefs)) throw new DirectoryNotFoundException("Dossier exefs introuvable : " + exefs);
        Nup = null;
        Romfs = romfs;
        Exefs = exefs;
    }

    /// The folder with nx2/make_game.py: the parcel's own sources (source.zip beside the program), a checkout this
    /// program was built in, or the sources an earlier install unpacked. sources beside the program win, and are
    /// unpacked into <install>\tools\ once per source.zip (its SHA-256 is the stamp).
    public string EnsureSource(Action<string> line)
    {
        var inTools = Path.Combine(ToolsDir, "nx2", "make_game.py");
        var parcel = Path.Combine(AppContext.BaseDirectory, "source.zip");
        if (File.Exists(parcel))
        {
                Directory.CreateDirectory(ToolsDir);
            var stamp = Path.Combine(ToolsDir, ".source");
            var sha = ToolInstaller.Hash(parcel);
            var have = File.Exists(stamp) ? File.ReadAllText(stamp).Trim() : "";
            if (have != sha || !File.Exists(inTools))
            {
                line("Sources: " + parcel + " → " + ToolsDir);
                ZipFile.ExtractToDirectory(parcel, ToolsDir, true);
                File.WriteAllText(stamp, sha + "\n");
            }
            return ToolsDir;
        }
        if (File.Exists(inTools)) return ToolsDir;
        var dev = FindDevSource();
        if (dev != null)
        {
            line("Sources: " + dev + " (dépôt de développement)");
            return dev;
        }
        throw new InvalidOperationException(
            "Les sources du jeu manquent : le dossier source.zip doit être à côté de " + Name + "Setup.exe, " +
            "ou cette version doit tourner depuis le dépôt Longshot (" + Path.Combine("setup", "OcaDimSetup") + ").");
    }

    static string? FindDevSource()
    {
        // (like builder/LongshotBuilder/Runner.cs's Tools.Find: this program's own folder's parents, and a checkout only)
        for (var d = new DirectoryInfo(AppContext.BaseDirectory); d != null; d = d.Parent)
            if (File.Exists(Path.Combine(d.FullName, "nx2", "make_game.py")))
                return d.FullName;
        return null;
    }

    public ToolInstaller Tools(string source, Action<string> line)
    {
        var lockPath = Path.Combine(source, "tools.lock");
        if (!File.Exists(lockPath)) throw new FileNotFoundException("tools.lock manque dans les sources : " + lockPath);
        return new ToolInstaller(ToolsDir, ToolsLock.Read(lockPath), line);
    }

    public static string PythonIn(string toolsDir)
    {
        var py = Path.Combine(toolsDir, "python", "python.exe");
        return File.Exists(py) ? py : "python";
    }

    ProcessStartInfo StartInfo(string source, IEnumerable<string> args)
    {
        var mingw = Path.Combine(ToolsDir, "llvm-mingw");
        var pythonDir = Path.Combine(ToolsDir, "python");
        var si = new ProcessStartInfo(PythonIn(ToolsDir))
        {
            WorkingDirectory = source,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = new UTF8Encoding(false),
            StandardErrorEncoding = new UTF8Encoding(false),
        };
        foreach (var a in args) si.ArgumentList.Add(a);
        si.Environment["PYTHONIOENCODING"] = "utf-8";
        si.Environment["PYTHONUNBUFFERED"] = "1";
        // (OcaDim) the memory the build leaves free, by this PC's RAM: nx2/build.py reads it (LONGSHOT_MEM_RESERVE_GB)
        si.Environment["LONGSHOT_MEM_RESERVE_GB"] = ReserveGb;
        si.Environment["PATH"] = string.Join(Path.PathSeparator.ToString(),
            new[] { Path.Combine(mingw, "bin"), pythonDir, Environment.GetEnvironmentVariable("PATH") ?? "" });
        if (Directory.Exists(mingw)) si.Environment["LONGSHOT_MINGW"] = mingw;
        var sets = new[] { ("RX_CPM", "cpm"), ("WGPU_NATIVE", "wgpu-native"), ("EMSDK", "emsdk") };
        foreach (var (name, folder) in sets)
        {
            var path = Path.Combine(ToolsDir, folder);
            if (Directory.Exists(path)) si.Environment[name] = path;
        }
        // (a developer's machine may carry these: a build is with NVIDIA's or AMD's SDK only when its arguments ask)
        si.Environment.Remove("LONGSHOT_NGX_SDK");
        si.Environment.Remove("LONGSHOT_FFX_SDK");
        si.Environment.Remove("LONGSHOT_MSVC");
        if (!HotCode) si.Environment["LONGSHOT_NO_HOT"] = "1";
        return si;
    }

    IEnumerable<string> CommonArgs() => new[]
    {
        "-I", "nx2/make_game.py", "--prepare", "--work", WorkDir, "--log", LogPath,
    };

    /// <summary>(OcaDim) The compilers this PC gets. nx2/make_game.py on its own takes one per CPU thread but one (15 on
    /// 16 threads) and nx2/build.py starts each only when the memory free holds it, so the RAM is respected — but a small
    /// PC still sees that many threads. Here the count follows the RAM too: a quarter of the threads under 12 GB, half
    /// under 16, all but one above.</summary>
    static int JobsForPc()
    {
        if (Light) return 1;   // (OcaDim) "Compilation légère": one compiler at a time, slower but almost impossible to starve
        int cpus = Math.Max(1, Environment.ProcessorCount);
        double gb = TotalRamGb;
        int jobs = gb < 12 ? Math.Max(2, cpus / 4) : gb < 16 ? Math.Max(2, cpus / 2) : Math.Max(2, cpus - 1);
        return Math.Max(1, Math.Min(jobs, cpus));
    }

    /// <summary>(OcaDim) What the build leaves to the desktop, over nx2/build.py's 1.5 GB: 2 GB under 16 GB of RAM, so the
    /// browser that was open before the setup keeps working while it builds.</summary>
    static string ReserveGb => TotalRamGb < 16 ? "2" : "1.5";

    static double TotalRamGb
    {
        get
        {
            try { return GC.GetGCMemoryInfo().TotalAvailableMemoryBytes / (1024.0 * 1024 * 1024); }
            catch (Exception) { return 16; }
        }
    }

    /// <summary>(OcaDim) The driver's fault list, moved aside before an update: cache/ocadim_driver_faults.txt keeps, for
    /// good, every program the driver faulted on — keyed by vendor and driver version (gpu/vk/driver_faults.h). A program
    /// on it is never asked of the driver again, which is what a player sees as "the shaders do not compile": the game
    /// misses those shaders with no message. A new build may have fixed what faulted, so it gets one more try; if the
    /// driver faults again the file comes back with the same lines.</summary>
    public string? ForgetDriverFaults()
    {
        var path = Path.Combine(InstallDir, "cache", "ocadim_driver_faults.txt");
        try
        {
            if (!File.Exists(path)) return null;
            var old = path + ".old";
            File.Delete(old);
            File.Move(path, old);
            return old;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    /// The game exe's own icon: nx2/make_icon.py writes work's longshot.res from OcaDim's .ico, and nx2/build.py links
    /// it into ocadim.exe (the taskbar, Alt-Tab and the shortcut when it has no icon of its own). A missing Pillow or
    /// .ico only means the exe keeps its generic icon: the build goes on.
    public void MakeIcon(string source, Action<string> line)
    {
        var picture = Path.Combine(source, "assets", "branding", "ocadim.ico");
        if (!File.Exists(picture)) return;
        try
        {
            Directory.CreateDirectory(WorkDir);
            var si = StartInfo(source, new[] { "-I", "nx2/make_icon.py", picture, WorkDir });
            si.RedirectStandardOutput = true;
            si.RedirectStandardError = true;
            using var p = Process.Start(si);
            if (p == null) return;
            var said = p.StandardOutput.ReadToEnd() + p.StandardError.ReadToEnd();
            p.WaitForExit(30000);
            var res = Path.Combine(WorkDir, "longshot.res");
            if (File.Exists(res)) line("Icône d'OcaDim : " + res + " (" + new FileInfo(res).Length / 1024 + " Ko)");
            else line("Icône d'OcaDim : non faite (" + said.Trim().Split('\n').LastOrDefault() + ")");
        }
        catch (Exception e) when (e is IOException or InvalidOperationException or System.ComponentModel.Win32Exception)
        {
            line("Icône d'OcaDim : non faite (" + e.Message + ")");
        }
    }

    /// <summary>make_game.py --check: the program and the build read and refused before anything is built.</summary>
    public async Task<CheckResult> CheckAsync(string source, string work, Action<string> line, CancellationToken cancel)
    {
        var args = new List<string> { "-I", "nx2/make_game.py", "--prepare", "--work", work, "--check" };
        args.AddRange(Nup != null ? new[] { "--nup", Nup } : new[] { "--romfs", Romfs!, "--exefs", Exefs! });
        Directory.CreateDirectory(work);
        string? ok = null, bad = null, program = null, build = null, error = null;
        var tail = new List<string>();
        var code = await RunAsync(source, args, _ => { }, l =>
        {
            lock (tail)
            {
                tail.Add(l);
                if (l.StartsWith("check ", StringComparison.Ordinal) || l.StartsWith("@@check ", StringComparison.Ordinal))
                    line(l);
                if (l.StartsWith("check ok ", StringComparison.Ordinal)) ok = l[9..];
                else if (l.StartsWith("check bad ", StringComparison.Ordinal)) bad ??= l[10..];
                else if (l.StartsWith("@@check ok ", StringComparison.Ordinal)) ok = l[11..];
                else if (l.StartsWith("@@check bad ", StringComparison.Ordinal)) bad ??= l[12..];
                else if (l.StartsWith("error ", StringComparison.Ordinal)) error = l[6..];
                else if (l.StartsWith("@@error ", StringComparison.Ordinal)) error = l[8..];
                var m = Regex.Match(ok ?? bad ?? "", @"program ([0-9A-Fa-f]{16})");
                if (m.Success) program = m.Groups[1].Value.ToUpperInvariant();
                m = Regex.Match(ok ?? bad ?? "", @"build ([0-9a-f]{8})");
                if (m.Success) build = m.Groups[1].Value;
            }
        }, cancel, parseProgress: false);
        lock (tail)
        {
            var text = bad ?? ok ?? error ?? string.Join("\n", tail.TakeLast(5));
            return new CheckResult(code == 0 && bad == null && error == null, text, program, build, error);
        }
    }

    /// <summary>The build itself: the same script the builder app runs, its @@progress lines as the bar.</summary>
    public async Task<BuildResult> BuildAsync(string source, bool update, Action<double, string> progress, Action<string> line,
                                              CancellationToken cancel)
    {
        var args = new List<string>(CommonArgs());
        args.AddRange(new[] { "--jobs", JobsForPc().ToString(CultureInfo.InvariantCulture) });
        if (update)
        {
            args.AddRange(new[] { "--update", InstallDir });
            var moved = ForgetDriverFaults();
            if (moved != null) line("Shaders : liste des programmes que le pilote avait en échec mise de côté (" + moved + ")");
        }
        else
        {
            if (Nup != null) args.AddRange(new[] { "--nup", Nup });
            else args.AddRange(new[] { "--romfs", Romfs!, "--exefs", Exefs! });
            args.AddRange(new[] { "--out", InstallDir });
            if (Fsr) args.AddRange(new[] { "--fsr", "--fetch-fsr-runtime", "--accept-amd-license" });
        }
        // (OcaDim) NVIDIA's DLSS SDK, for an install and for an update alike: ngx/ is what DLSS and DLSS Frame Generation
        // read at run time, and a build made without it has neither. The tick in the wizard is the accepted licence.
        if (Ngx) args.AddRange(new[] { "--fetch-ngx-sdk", "--accept-nvidia-license" });
        string? error = null;
        var tail = new List<string>();
        var code = await RunAsync(source, args, p => progress(p.Item1, p.Item2), l =>
        {
            line(l);
            lock (tail)
            {
                if (l.StartsWith("error ", StringComparison.Ordinal)) error = l[6..];
                else if (l.StartsWith("@@error ", StringComparison.Ordinal)) error = l[8..];
                else if (!l.StartsWith("progress ", StringComparison.Ordinal) && !l.StartsWith("@@progress ", StringComparison.Ordinal))
                {
                    tail.Add(l);
                    if (tail.Count > 60) tail.RemoveAt(0);
                }
            }
        }, cancel, parseProgress: true);
        lock (tail)
        {
            return new BuildResult(code, error, string.Join("\n", tail.TakeLast(40)));
        }
    }

    static readonly Regex ProgressLine = new(@"^(@@)?progress\s+([0-9]*\.?[0-9]+)\s*(.*)$", RegexOptions.Compiled);
    static readonly Regex StageLine = new(@"^@@stage\s+\S+\s+(.*)$", RegexOptions.Compiled);

    async Task<int> RunAsync(string source, IEnumerable<string> args, Action<(double, string)> onProgress, Action<string> onLine,
                             CancellationToken cancel, bool parseProgress)
    {
        using var process = new Process { StartInfo = StartInfo(source, args), EnableRaisingEvents = true };
        var si = process.StartInfo;
        double last = 0;
        string stage = "";
        void Handle(string l)
        {
            if (parseProgress)
            {
                var m = ProgressLine.Match(l);
                if (m.Success)
                {
                    if (double.TryParse(m.Groups[2].Value, NumberStyles.Float, CultureInfo.InvariantCulture, out var value))
                    {
                        last = Math.Clamp(value, 0, 1);
                        if (m.Groups[3].Value.Length > 0) stage = m.Groups[3].Value;
                        onProgress((last, stage));
                        return;
                    }
                }
                var s = StageLine.Match(l);
                if (s.Success)
                {
                    stage = s.Groups[1].Value;
                    onProgress((last, stage));
                    return;
                }
            }
            onLine(l);
        }
        try
        {
            process.Start();
        }
        catch (Exception e)
        {
            throw new InvalidOperationException("Python n'a pas pu démarrer (" + si.FileName + ") : " + e.Message, e);
        }
        try { process.PriorityClass = ProcessPriorityClass.BelowNormal; } catch (Exception) { }
        var stdout = PumpAsync(process.StandardOutput, Handle);
        var stderr = PumpAsync(process.StandardError, Handle);
        try
        {
            await process.WaitForExitAsync(cancel).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try { process.Kill(entireProcessTree: true); } catch (Exception) { }
            await process.WaitForExitAsync().ConfigureAwait(false);
            throw;
        }
        finally
        {
            await Task.WhenAll(stdout, stderr).ConfigureAwait(false);
        }
        if (process.ExitCode == 0) onProgress((1.0, stage.Length > 0 ? stage : "Terminé"));
        return process.ExitCode;
    }

    static async Task PumpAsync(StreamReader reader, Action<string> handle)
    {
        string? line;
        while ((line = await reader.ReadLineAsync().ConfigureAwait(false)) != null)
        {
            try { handle(line); } catch (Exception) { }   // (a listener that throws must not stop the child's output)
        }
    }

    public void EnsureInstallFolder()
    {
        var probe = Path.Combine(InstallDir, ".write-check");
        try
        {
            Directory.CreateDirectory(InstallDir);
            File.WriteAllText(probe, "ok");
            File.Delete(probe);
        }
        catch (Exception e)
        {
            throw new InvalidOperationException("Le dossier " + InstallDir + " ne peut pas être écrit : " + e.Message, e);
        }
        Directory.CreateDirectory(ToolsDir);
        Directory.CreateDirectory(WorkDir);
    }

    /// A game in play: its files are locked. Asked before an update replaces them, and in plain words.
    public bool GameIsRunning()
    {
        var exe = Path.Combine(InstallDir, GameExe);
        if (!File.Exists(exe)) return false;
        try
        {
            using var probe = new FileStream(exe, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
            return false;
        }
        catch (IOException) { return true; }
        catch (UnauthorizedAccessException) { return true; }
    }

    public void WriteVersion(string from)
    {
        File.WriteAllText(VersionPath, string.Format(CultureInfo.InvariantCulture,
            "{0} {1}\ninstallé {2:yyyy-MM-dd HH:mm}\ndepuis {3}\n", Name, Version, DateTime.Now, from));
    }

    public string InstalledVersion()
    {
        try
        {
            var first = File.ReadLines(VersionPath).FirstOrDefault();
            return first != null && first.StartsWith(Name + " ", StringComparison.Ordinal) ? first[(Name.Length + 1)..] : Version;
        }
        catch (IOException) { return Version; }
    }
}

/// One build at a time in a tools folder (the lesson of #630): a .lock opened exclusively and held while the tools are
/// fetched and the game built. The file itself stays (harmless); the open handle is what excludes another build, and
/// Windows drops it when this program ends, however it ends.
sealed class BuildLock : IDisposable
{
    readonly FileStream stream;

    BuildLock(FileStream stream) => this.stream = stream;

    public static BuildLock Take(string toolsDir)
    {
        Directory.CreateDirectory(toolsDir);
        var path = Path.Combine(toolsDir, ".lock");
        try
        {
            var stream = new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
            try
            {
                stream.SetLength(0);
                var text = Encoding.UTF8.GetBytes(string.Format(CultureInfo.InvariantCulture,
                    "pid {0} ({1}) since {2:yyyy-MM-dd HH:mm:ss}\n", Environment.ProcessId, Setup.Name, DateTime.Now));
                stream.Write(text);
                stream.Flush();
            }
            catch (IOException) { }
            return new BuildLock(stream);
        }
        catch (IOException)
        {
            var said = "";
            try { said = File.ReadAllText(path).Trim(); } catch (Exception) { }
            throw new InvalidOperationException(
                "Une autre compilation utilise déjà ces outils" + (said.Length > 0 ? " (" + said + ")" : "") +
                ". Un seul build à la fois : attendez qu'elle finisse.");
        }
    }

    public void Dispose()
    {
        try { stream.Dispose(); } catch (Exception) { }
    }
}
