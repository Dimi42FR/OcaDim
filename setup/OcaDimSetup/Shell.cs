using System.Diagnostics;
using System.Reflection;

namespace OcaDimSetup;

/// What the wizard does outside the build: the shortcuts (WScript.Shell, as setup/OcaDim-Setup.ps1), starting the game,
/// opening the folder, and taking the install away again.
static class Shell
{
    public static string DesktopShortcut => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), Setup.Name + " " + Setup.Version + ".lnk");

    public static string StartMenuFolder => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "Microsoft", "Windows", "Start Menu", "Programs", Setup.Name);

    public static string StartMenuShortcut => Path.Combine(StartMenuFolder, Setup.Name + " " + Setup.Version + ".lnk");

    public static void Shortcut(string lnk, string target, string workingDirectory, string icon, string description)
    {
        var type = Type.GetTypeFromProgID("WScript.Shell")
                   ?? throw new InvalidOperationException("WScript.Shell n'est pas disponible sur ce système.");
        var ws = Activator.CreateInstance(type)!;
        var link = type.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, ws, new object[] { lnk })!;
        var t = link.GetType();
        t.InvokeMember("TargetPath", BindingFlags.SetProperty, null, link, new object[] { target });
        t.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, link, new object[] { workingDirectory });
        t.InvokeMember("IconLocation", BindingFlags.SetProperty, null, link, new object[] { icon + ",0" });
        t.InvokeMember("Description", BindingFlags.SetProperty, null, link, new object[] { description });
        t.InvokeMember("Save", BindingFlags.InvokeMethod, null, link, null);
    }

    public static void MakeShortcuts(Setup setup, bool desktop, bool startMenu)
    {
        var exe = Path.Combine(setup.InstallDir, Setup.GameExe);
        var icon = exe;
        if (desktop)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(DesktopShortcut)!);
            Shortcut(DesktopShortcut, exe, setup.InstallDir, icon, Setup.Name + " " + Setup.Version);
        }
        if (startMenu)
        {
            Directory.CreateDirectory(StartMenuFolder);
            Shortcut(StartMenuShortcut, exe, setup.InstallDir, icon, Setup.Name + " " + Setup.Version);
        }
    }

    public static void RemoveShortcuts()
    {
        TryDelete(DesktopShortcut);
        try { if (Directory.Exists(StartMenuFolder)) Directory.Delete(StartMenuFolder, recursive: true); }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }

    static void TryDelete(string path)
    {
        if (File.Exists(path)) File.Delete(path);
    }

    public static void Play(Setup setup) => Start(Path.Combine(setup.InstallDir, Setup.GameExe), setup.InstallDir);

    static void Start(string exe, string folder)
    {
        if (!File.Exists(exe)) throw new FileNotFoundException("Le jeu n'est pas installé : " + exe);
        Process.Start(new ProcessStartInfo(exe) { WorkingDirectory = folder, UseShellExecute = true });
    }

    public static void OpenFolder(string folder)
    {
        Directory.CreateDirectory(folder);
        Process.Start(new ProcessStartInfo("explorer.exe", "\"" + folder + "\"") { UseShellExecute = true });
    }

    /// Removes the install, its shortcuts and its version file. A game still in play is refused first (its files are
    /// locked), and this program itself may be running from the install (a developer's run): Windows keeps the exe, so
    /// the folder is removed by a short-lived command once this program has ended.
    public static void Uninstall(Setup setup)
    {
        if (setup.GameIsRunning())
            throw new InvalidOperationException("Fermez OcaDim avant de le désinstaller.");
        RemoveShortcuts();
        var inside = AppContext.BaseDirectory.StartsWith(
            Path.GetFullPath(setup.InstallDir) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
        try
        {
            if (Directory.Exists(setup.InstallDir)) Directory.Delete(setup.InstallDir, recursive: true);
        }
        catch (IOException) when (inside)
        {
            // (this program's own exe and DLLs are in the folder)
            var info = new ProcessStartInfo("cmd.exe",
                "/c ping 127.0.0.1 -n 3 >nul & rmdir /s /q \"" + setup.InstallDir + "\"")
            { CreateNoWindow = true, UseShellExecute = false };
            Process.Start(info);
        }
    }
}
