using System.Runtime.InteropServices;
using System.Text;

namespace OcaDimSetup;

static class Program
{
    [DllImport("kernel32.dll")]
    static extern bool AttachConsole(int processId);

    [STAThread]
    static int Main(string[] args)
    {
        if (args.Length > 0 && (args[0] == "--version" || args[0] == "-v"))
        {
            AttachConsole(-1);
            Console.WriteLine(Setup.Name + " " + "Setup" + " " + Setup.Version);
            return 0;
        }
        if (args.Length > 0 && args[0] == "--cli")
        {
            AttachConsole(-1);
            return Cli.Run(args.Skip(1).ToArray());
        }
        Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        if (args.Length > 1 && args[0] == "--shot")
        {
            // (a page of the wizard as a PNG, without a window: the README's pictures and a look before shipping)
            using var form = new WizardForm { Opacity = 0, ShowInTaskbar = false };
            if (args.Length > 2) form.ShowPreview(args[2]);
            form.Show();
            Application.DoEvents();
            using var shot = new Bitmap(form.Width, form.Height);
            form.DrawToBitmap(shot, new Rectangle(0, 0, form.Width, form.Height));
            shot.Save(args[1], System.Drawing.Imaging.ImageFormat.Png);
            File.WriteAllLines(args[1] + ".txt", form.BoundsDump());
            form.Hide();
            return 0;
        }
        Application.Run(new WizardForm());
        return 0;
    }
}

/// The same install without a window: scripts, the six tests, and a player who prefers a command line.
/// OcaDimSetup.exe --cli --nup <file> --out <folder> [--fsr] [--no-ngx] [--check] [--update] [--tools-from <folder>] [--log <file>]
static class Cli
{
    public static int Run(string[] args)
    {
        var setup = new Setup();
        bool check = false, update = false, desktop = true, startMenu = true, fsr = false, keepShortcuts = true;
        string? log = null, game = null, romfs = null, exefs = null, outDir = null;
        for (int i = 0; i < args.Length; i++)
        {
            string Next() => i + 1 < args.Length ? args[++i] : throw new ArgumentException(args[i] + " demande une valeur");
            switch (args[i])
            {
                case "--nup": setup.Choose(Next()); break;
                case "--game": game = Next(); break;
                case "--romfs": romfs = Next(); break;
                case "--exefs": exefs = Next(); break;
                case "--out": outDir = Next(); break;
                case "--update": update = true; break;
                case "--check": check = true; break;
                case "--fsr": fsr = true; break;
                case "--no-fsr": fsr = false; break;
                case "--ngx": setup.Ngx = true; break;
                case "--no-ngx": setup.Ngx = false; break;
                case "--no-hot": setup.HotCode = false; break;
                case "--hot": setup.HotCode = true; break;
                case "--tools-from": setup.ToolsFrom = Next(); break;
                case "--log": log = Next(); break;
                case "--no-shortcuts": keepShortcuts = desktop = startMenu = false; break;
                case "--no-desktop": desktop = false; break;
                case "--no-start-menu": startMenu = false; break;
                case "--help": case "-h": Usage(); return 0;
                default: Console.Error.WriteLine("Option inconnue : " + args[i]); Usage(); return 2;
            }
        }
        setup.Fsr = fsr;
        if (outDir != null) setup.InstallDir = Path.GetFullPath(outDir);
        var writer = new Say(log);
        try
        {
            if (game != null) setup.Choose(game);
            if (romfs != null || exefs != null)
            {
                if (romfs == null || exefs == null) throw new ArgumentException("--romfs et --exefs vont ensemble");
                setup.ChooseFolders(romfs, exefs);
            }
            if (!check && !update && !setup.HasGame) throw new ArgumentException("--nup, ou --game <fichier|dossier>, ou --romfs et --exefs");
            if (update && !setup.Installed)
                throw new InvalidOperationException("Rien n'est installé dans " + setup.InstallDir + " : pas de mise à jour possible.");

            writer.Info("OcaDim Setup " + Setup.Version);
            writer.Info("dossier : " + setup.InstallDir);
            var source = setup.EnsureSource(writer.Line);
            var tools = setup.Tools(source, writer.Line);
            if (setup.ToolsFrom != null) tools.Seed(setup.ToolsFrom);

            var cancel = new CancellationTokenSource();
            Console.CancelKeyPress += (_, e) => { e.Cancel = true; cancel.Cancel(); };

            int lastTenth = -1;
            tools.InstallAsync((fraction, text) =>
            {
                var tenth = (int)(fraction * 100) / 5;
                if (tenth != lastTenth) { lastTenth = tenth; writer.Progress(fraction, text); }
            }, cancel.Token).GetAwaiter().GetResult();

            if (check)
            {
                var work = Path.Combine(Path.GetTempPath(), "ocadim-check-" + Environment.ProcessId);
                try
                {
                    var result = setup.CheckAsync(source, work, writer.Line, cancel.Token).GetAwaiter().GetResult();
                    writer.Info("check " + (result.Ok ? "ok" : "bad") + " : " + result.Text);
                    return result.Ok ? 0 : 1;
                }
                finally { TryRemove(work); }
            }

            if (!update && setup.Installed)
            {
                // (a build into a folder that holds a game: its saves and settings stay, the update path is the safe one)
                if (setup.GameIsRunning()) throw new InvalidOperationException("Fermez OcaDim avant de le mettre à jour.");
                update = true;
            }
            setup.EnsureInstallFolder();
            using var guard = BuildLock.Take(setup.ToolsDir);
            writer.Info("build : " + (update ? "mise à jour" : "installation"));
            setup.MakeIcon(source, writer.Line);
            var built = setup.BuildAsync(source, update, (fraction, text) => writer.Progress(fraction, text), writer.Line, cancel.Token)
                              .GetAwaiter().GetResult();
            if (built.Code != 0)
            {
                writer.Info("échec : " + (built.Error ?? "le build s'est arrêté (code " + built.Code + ")"));
                return built.Code == 0 ? 1 : built.Code;
            }
            if (!setup.Installed) throw new InvalidOperationException("Le build a rendu 0 mais longshot.exe n'est pas là.");
            setup.WriteVersion(source);
            if (keepShortcuts) Shell.MakeShortcuts(setup, desktop, startMenu);
            writer.Info("installé : " + Path.Combine(setup.InstallDir, Setup.GameExe));
            return 0;
        }
        catch (Exception e) when (e is IOException or InvalidOperationException or ArgumentException or FileNotFoundException)
        {
            writer.Info("error " + e.Message);
            return 1;
        }
        finally
        {
            writer.Close();
        }
    }

    static void TryRemove(string folder)
    {
        try { if (Directory.Exists(folder)) Directory.Delete(folder, recursive: true); }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }

    static void Usage()
    {
        Console.WriteLine("OcaDimSetup.exe [--cli] --nup <fichier> --out <dossier> [--fsr] [--no-ngx] [--no-hot] [--check] [--update]");
        Console.WriteLine("               [--game <fichier|dossier>] [--romfs <dossier> --exefs <dossier>]");
        Console.WriteLine("               [--tools-from <dossier>] [--log <fichier>] [--no-shortcuts]");
    }

    /// Console output plus, when asked, a UTF-8 log: a test reads the log when the console is another window's.
    sealed class Say
    {
        readonly StreamWriter? file;
        readonly object gate = new();

        public Say(string? log)
        {
            if (log == null) return;
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(log))!);
            file = new StreamWriter(log, append: false, new UTF8Encoding(false)) { AutoFlush = true };
        }

        public void Line(string text)
        {
            lock (gate)
            {
                Console.WriteLine(text);
                file?.WriteLine(text);
            }
        }

        public void Info(string text) => Line("[ocadim] " + text);

        public void Progress(double fraction, string text)
        {
            lock (gate)
            {
                var line = string.Format(System.Globalization.CultureInfo.InvariantCulture,
                    "[ocadim] {0:0}% {1}", fraction * 100, text);
                Console.WriteLine(line);
                file?.WriteLine(line);
            }
        }

        public void Close()
        {
            lock (gate) file?.Dispose();
        }
    }
}
