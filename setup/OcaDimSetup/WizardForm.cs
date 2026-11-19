using System.Reflection;

namespace OcaDimSetup;

/// The wizard (docs/SETUP-OCADIM-DESIGN.md): welcome, the player's copy, the folder, the build, done — and, once
/// installed, the same program's Jouer / Mettre à jour / Désinstaller screen.
sealed class WizardForm : Form
{
    static readonly Color Ink = Color.FromArgb(0x17, 0x13, 0x10);
    static readonly Color Card = Color.FromArgb(0x22, 0x1C, 0x17);
    static readonly Color Paper = Color.FromArgb(0xF4, 0xEF, 0xE7);
    static readonly Color Muted = Color.FromArgb(0xA9, 0x9E, 0x90);
    static readonly Color Gold = Color.FromArgb(0xD9, 0xB3, 0x4C);
    static readonly Color Alarm = Color.FromArgb(0xE8, 0x7B, 0x66);

    enum Page { Welcome, Game, Folder, Build, Done, Launcher }

    readonly Setup setup = new();
    readonly Panel body;
    readonly Label status, step;
    readonly Button back, next;
    readonly System.Windows.Forms.Timer clock = new() { Interval = 500 };
    readonly DateTime started = DateTime.Now;

    CancellationTokenSource? cancel;
    Task? running;
    Page current = Page.Welcome;
    bool building;
    bool closing;
    bool desktop = true, startMenu = true;
    string? verification;
    double shown;
    TextBox? logBox;
    ProgressBar? bar;
    Label? stageLabel, percentLabel, elapsedLabel, chosenLabel, verifyLabel, errorLabel;

    int ContentWidth => Math.Max(560, ClientSize.Width - 96);

    public WizardForm()
    {
        Text = Setup.Name + " Setup " + Setup.Version;
        var area = Screen.PrimaryScreen?.WorkingArea ?? new Rectangle(0, 0, 1280, 800);
        var width = Math.Min(900, area.Width - 40);
        var height = Math.Min(660, area.Height - 40);
        ClientSize = new Size(width, height);
        FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false;
        StartPosition = FormStartPosition.Manual;
        Location = new Point(area.Left + Math.Max(0, (area.Width - (width + 16)) / 2),
                             area.Top + Math.Max(0, (area.Height - (height + 39)) / 2));
        BackColor = Ink;
        ForeColor = Paper;
        Font = new Font("Segoe UI", 9.75f);
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath) ?? SystemIcons.Application; }
        catch (Exception) { }

        var header = new Panel { Dock = DockStyle.Top, Height = 118, BackColor = Ink };
        var emblem = new PictureBox { Left = 32, Top = 14, Width = 72, Height = 72, SizeMode = PictureBoxSizeMode.Zoom, Image = Emblem() };
        var wordmark = new Label
        {
            Text = "OcaDim", Left = 124, Top = 18, AutoSize = true, ForeColor = Gold,
            Font = new Font("Segoe UI Semibold", 26f, FontStyle.Bold),
        };
        var sub = new Label
        {
            Text = "le port natif · v" + Setup.Version, Left = 128, Top = 76, AutoSize = true, ForeColor = Muted,
            Font = new Font("Segoe UI", 10f),
        };
        header.Controls.AddRange(new Control[] { emblem, wordmark, sub });

        var footer = new Panel { Dock = DockStyle.Bottom, Height = 68, BackColor = Card };
        status = new Label { Left = 32, Top = 26, AutoSize = true, ForeColor = Muted, MaximumSize = new Size(470, 0) };
        step = new Label { Left = 32, Top = 8, AutoSize = true, ForeColor = Gold, Font = new Font("Segoe UI Semibold", 9f) };
        next = GoldButton("Continuer");
        next.Left = 740; next.Top = 16; next.Width = 128;
        next.Click += (_, _) => NextClicked();
        back = QuietButton("Retour");
        back.Left = 620; back.Top = 16; back.Width = 104;
        back.Click += (_, _) => BackClicked();
        footer.Controls.AddRange(new Control[] { step, status, back, next });

        body = new Panel { Dock = DockStyle.Fill, BackColor = Ink, AutoScroll = true };
        Controls.Add(body);
        Controls.Add(header);
        Controls.Add(footer);

        clock.Tick += (_, _) => Tick();
        PlaceFooter();
        ShowLauncherOrWelcome();
    }

    void PlaceFooter()
    {
        next.Left = ClientSize.Width - 32 - next.Width;
        back.Left = next.Left - 12 - back.Width;
        status.MaximumSize = new Size(Math.Max(200, back.Left - 48), 0);
    }

    protected override void OnResize(EventArgs e)
    {
        base.OnResize(e);
        if (next != null && back != null && status != null) PlaceFooter();
    }

    static Image? Emblem()
    {
        try
        {
            using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("OcaDimSetup.ocadim.ico");
            if (stream != null) return new Icon(stream, 64, 64).ToBitmap();
        }
        catch (Exception) { }
        try { return Icon.ExtractAssociatedIcon(Application.ExecutablePath)?.ToBitmap(); }
        catch (Exception) { return null; }
    }

    static Image? Artwork()
    {
        try
        {
            using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("OcaDimSetup.artwork.png");
            return stream == null ? null : Image.FromStream(stream);
        }
        catch (Exception) { return null; }
    }

    // ---------------------------------------------------------------- pages

    /// A page by name, for --shot (Program.cs): welcome, game, folder, launcher.
    public void ShowPreview(string page)
    {
        switch (page)
        {
            case "game": ShowGame(); break;
            case "folder": ShowFolder(); break;
            case "launcher": ShowLauncher(); break;
            default: ShowWelcome(); break;
        }
    }

    internal IEnumerable<string> BoundsDump() => body.Controls.Cast<Control>()
        .Select(c => string.Format("{0} L={1} T={2} W={3} H={4} B={5} : {6}",
            c.GetType().Name, c.Left, c.Top, c.Width, c.Height, c.Bottom, c.Text.Replace('\n', ' ')));

    void ShowLauncherOrWelcome()
    {
        if (setup.Installed) ShowLauncher();
        else ShowWelcome();
    }

    void ShowWelcome()
    {
        Begin(Page.Welcome, "Bienvenue");
        var hero = Artwork();
        var bannerWidth = Math.Min(ContentWidth, 460);
        Add(new PictureBox
        {
            Image = hero, SizeMode = PictureBoxSizeMode.Zoom, Width = bannerWidth,
            Height = hero == null ? 200 : (int)(bannerWidth * hero.Height / (double)hero.Width),
        });
        Add(Heading("OcaDim " + Setup.Version));
        Add(Paragraph(
            "Ocarina of Time, porté nativement en Vulkan. Ce programme ne contient aucun fichier du jeu : il prend votre " +
            "propre copie, récupère les outils de compilation, et compile le jeu sur votre machine."));
        Add(Bullet("Votre copie du jeu en .nup — programme 0400486024DEC000, build e0f3ccfa."));
        Add(Bullet("Environ 33 Go libres au maximum sur le disque (le build les rend ensuite), et Windows 10 ou 11 en 64 bits."));
        Add(Bullet("Environ 40 minutes la première fois (la compilation et la préparation des shaders)."));
        SetFooter("", "Continuer", true, false);
    }

    void ShowGame()
    {
        Begin(Page.Game, "Le jeu");
        Add(Heading("Le jeu"));
        Add(Paragraph("Choisissez votre fichier .nup, ou les deux dossiers romfs et exefs. OcaDim lit le programme et le " +
                      "build avant de compiler, et refuse tout autre jeu sans rien créer."));
        var nup = GoldButton("Choisir un .nup…");
        nup.Width = 190; nup.Height = 38;
        nup.Click += (_, _) => ChooseNup();
        var folders = QuietButton("Choisir romfs + exefs…");
        folders.Width = 210; folders.Height = 38;
        folders.Click += (_, _) => ChooseFolders();
        Add(Row(nup, folders));

        chosenLabel = Paragraph(setup.HasGame ? setup.GameLabel : "Aucun jeu choisi.");
        chosenLabel.ForeColor = Gold;
        Add(chosenLabel);
        verifyLabel = Paragraph(verification ?? "");
        verifyLabel.ForeColor = Muted;
        Add(verifyLabel);
        errorLabel = Paragraph("");
        errorLabel.ForeColor = Alarm;
        Add(errorLabel);
        SetFooter("Étape 1 sur 3 — le jeu", "Continuer", setup.HasGame, true);
    }

    void ShowFolder()
    {
        Begin(Page.Folder, "Le dossier");
        Add(Heading("Le dossier"));
        Add(Paragraph("Le jeu compilé et ses outils vont dans ce dossier. Les outils y restent d'une mise à jour à l'autre."));
        var label = Paragraph("Dossier d'installation");
        label.ForeColor = Muted;
        Add(label);
        var box = new TextBox
        {
            Text = setup.InstallDir, Width = ContentWidth - 160, BackColor = Card, ForeColor = Paper,
            BorderStyle = BorderStyle.FixedSingle, Font = new Font("Consolas", 9.5f),
        };
        box.TextChanged += (_, _) => setup.InstallDir = box.Text.Trim();
        var browse = QuietButton("Parcourir…");
        browse.Width = 132;
        browse.Click += (_, _) =>
        {
            using var d = new FolderBrowserDialog { Description = "Dossier où installer OcaDim", SelectedPath = setup.InstallDir };
            if (d.ShowDialog(this) == DialogResult.OK) box.Text = d.SelectedPath;
        };
        Add(Row(box, browse));
        var tools = Paragraph("Outils : " + Path.Combine(setup.InstallDir, "tools") + "   (~250 Mo, téléchargés une fois)");
        tools.ForeColor = Muted;
        Add(tools);

        var desktopBox = Check("Raccourci sur le Bureau", desktop);
        desktopBox.CheckedChanged += (_, _) => desktop = desktopBox.Checked;
        Add(desktopBox);
        var menuBox = Check("Entrée dans le menu Démarrer", startMenu);
        menuBox.CheckedChanged += (_, _) => startMenu = menuBox.Checked;
        Add(menuBox);
        var fsrBox = Check("Compiler avec AMD FSR 4 (cartes RDNA 4 ; sinon, la mise à l'échelle du pilote)", setup.Fsr);
        fsrBox.CheckedChanged += (_, _) => setup.Fsr = fsrBox.Checked;
        Add(fsrBox);
        // (OcaDim) Without NVIDIA's DLSS SDK the renderer is built without DLSS and without DLSS Frame Generation: an RTX
        // card then finds neither, and the F1 menu has no NVIDIA page at all. The tick fetches the SDK (NVIDIA's licence is
        // accepted here, by ticking it) and ships ngx/ beside the game.
        var ngxBox = Check("Compiler avec NVIDIA DLSS et la frame generation (cartes RTX : DLSS, DLAA, DLSS-G)", setup.Ngx);
        ngxBox.CheckedChanged += (_, _) => setup.Ngx = ngxBox.Checked;
        Add(ngxBox);
        var ngxNote = Paragraph("Télécharge le SDK NVIDIA au premier build et livre le dossier ngx/ avec le jeu. Sans cette case, " +
                                "le jeu compile sans DLSS : l'onglet NVIDIA n'existe pas et la frame generation de NVIDIA non plus. " +
                                "Sur AMD, la case ne change rien.");
        ngxNote.ForeColor = Muted;
        Add(ngxNote);
        var hotBox = Check("Optimisations CPU maximales — recommandé (chunk chaud à -O2, profil de jeu)", setup.HotCode);
        hotBox.CheckedChanged += (_, _) => setup.HotCode = hotBox.Checked;
        Add(hotBox);
        var hotNote = Paragraph("Décochez si le jeu plante au démarrage ou en jeu : le build standard est plus lent, mais c'est " +
                                "celui qu'on teste le plus. Le choix ne change pas le contenu du jeu, seulement la compilation.");
        hotNote.ForeColor = Muted;
        Add(hotNote);
        // (OcaDim) a small PC that ran out of memory during the build: one compiler at a time
        var lightBox = Check("Compilation légère (petit PC : beaucoup plus lente, mais ne sature pas la mémoire)", Setup.Light);
        lightBox.CheckedChanged += (_, _) => Setup.Light = lightBox.Checked;
        Add(lightBox);
        var credit = Paragraph("Fonctions les plus chaudes compilées à -O2 et le renderer avec son profil de jeu : c'est le CPU " +
                               "qui limite ce jeu. Plus long à compiler, aucune contrepartie en jeu.  Ajouté par Dimi42FR.");
        credit.ForeColor = Muted;
        Add(credit);
        Add(Paragraph("Le dossier du jeu fait une soixantaine de gigaoctets une fois compilé. Rien n'est écrit dans le jeu " +
                      "avant que votre copie soit reconnue."));
        SetFooter("Étape 2 sur 3 — le dossier", setup.Installed ? "Mettre à jour" : "Installer", true, true);
    }

    void ShowBuild(bool update)
    {
        Begin(Page.Build, update ? "Mise à jour" : "Installation");
        Add(Heading(update ? "Mise à jour du jeu" : "Compilation du jeu"));
        stageLabel = Heading("Préparation…");
        stageLabel.Font = new Font("Segoe UI Semibold", 12f, FontStyle.Bold);
        stageLabel.ForeColor = Gold;
        Add(stageLabel);
        bar = new ProgressBar { Minimum = 0, Maximum = 1000, Value = 0, Width = ContentWidth, Height = 22 };
        Add(bar);
        percentLabel = Paragraph("0 %");
        Add(percentLabel);
        elapsedLabel = Paragraph("Temps écoulé : 0 s · la première compilation prend environ 40 minutes");
        elapsedLabel.ForeColor = Muted;
        Add(elapsedLabel);
        logBox = new TextBox
        {
            Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Width = ContentWidth, Height = 262,
            BackColor = Color.FromArgb(0x10, 0x0D, 0x0B), ForeColor = Color.FromArgb(0xC9, 0xC0, 0xB2),
            BorderStyle = BorderStyle.FixedSingle, Font = new Font("Consolas", 8.25f), WordWrap = false,
        };
        Add(logBox);
        SetFooter("Étape 3 sur 3 — la compilation ; le dossier reste reprenable", "Annuler", true, false);
        building = true;
        shown = 0;
        clock.Start();
        running = RunAsync(update);
    }

    void ShowDone()
    {
        building = false;
        clock.Stop();
        Begin(Page.Done, "Terminé");
        Add(Heading("C'est prêt."));
        Add(Paragraph(Setup.Name + " " + setup.InstalledVersion() + " est installé dans " + setup.InstallDir + "."));
        Add(Paragraph("Le jeu se lance par le raccourci, ou par le bouton ci-dessous. Vos réglages (ocadim_options.ini) et " +
                      "vos sauvegardes vivent dans le dossier du jeu."));
        var play = GoldButton("Jouer");
        play.Width = 150; play.Height = 40;
        play.Click += (_, _) => Shell.Play(setup);
        var open = QuietButton("Ouvrir le dossier");
        open.Width = 180; open.Height = 40;
        open.Click += (_, _) => Shell.OpenFolder(setup.InstallDir);
        var close = QuietButton("Fermer");
        close.Width = 110; close.Height = 40;
        close.Click += (_, _) => Close();
        Add(Row(play, open, close));
        SetFooter("", "Jouer", false, false);
    }

    void ShowLauncher()
    {
        Begin(Page.Launcher, "Déjà installé");
        Add(Heading("OcaDim " + setup.InstalledVersion()));
        Add(Paragraph("Le jeu est installé dans " + setup.InstallDir + "."));
        Add(Paragraph("Mettre à jour recompile le jeu dans le même dossier, à partir des fichiers qu'il garde : vos réglages " +
                      "et vos sauvegardes ne sont pas touchés."));
        var play = GoldButton("Jouer");
        play.Width = 150; play.Height = 40;
        play.Click += (_, _) => Shell.Play(setup);
        var update = QuietButton("Mettre à jour");
        update.Width = 170; update.Height = 40;
        update.Click += (_, _) =>
        {
            if (setup.GameIsRunning())
            {
                MessageBox.Show(this, "Fermez OcaDim avant de le mettre à jour.", Setup.Name, MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            if (!setup.HasGame)
            {
                ShowGame();
                return;
            }
            ShowBuild(true);
        };
        var open = QuietButton("Ouvrir le dossier");
        open.Width = 170; open.Height = 40;
        open.Click += (_, _) => Shell.OpenFolder(setup.InstallDir);
        Add(Row(play, update, open));
        var uninstall = QuietButton("Désinstaller OcaDim");
        uninstall.ForeColor = Alarm;
        uninstall.Width = 210;
        uninstall.Click += (_, _) => Uninstall();
        Add(uninstall);
        Add(Paragraph("Désinstaller retire le jeu, ses outils et les raccourcis. Vos sauvegardes sont dans le dossier du jeu : " +
                      "copiez-les avant si vous y tenez."));
        SetFooter("", "", false, false);
    }

    // ---------------------------------------------------------------- the build

    async Task RunAsync(bool update)
    {
        cancel = new CancellationTokenSource();
        var token = cancel.Token;
        BuildLock? guard = null;
        try
        {
            var source = await Task.Run(() => setup.EnsureSource(Line), token);
            setup.EnsureInstallFolder();
            guard = BuildLock.Take(setup.ToolsDir);
            var tools = setup.Tools(source, Line);
            if (setup.ToolsFrom != null) tools.Seed(setup.ToolsFrom);
            // (OcaDim) outils livrés avec le Setup : <dossier du Setup>\tools-seed, copiés au lieu d'être téléchargés
            var bundled = Path.Combine(AppContext.BaseDirectory, "tools-seed");
            if (Directory.Exists(bundled)) tools.Seed(bundled);
            Stage("Outils de compilation", 0.02);
            await tools.InstallAsync((fraction, text) =>
            {
                if (!token.IsCancellationRequested) Stage("Outils · " + text, 0.02 + 0.13 * fraction);
            }, token);

            Stage("Vérification de votre copie", 0.16);
            var check = await setup.CheckAsync(source, setup.WorkDir, Line, token);
            verification = (check.Ok ? "Reconnu : " : "Refusé : ") + check.Text;
            if (!check.Ok)
            {
                Ui(() => Fail(check.Text, "Ce n'est pas la copie que " + Setup.Name + " sait construire. Aucun fichier du jeu " +
                                          "n'a été créé."));
                return;
            }
            Line(verification);

            Stage(update ? "Mise à jour" : "Compilation", 0.18);
            setup.MakeIcon(source, Line);
            var built = await setup.BuildAsync(source, update, (fraction, text) =>
            {
                if (!token.IsCancellationRequested) Stage(text.Length > 0 ? text : "Compilation", 0.18 + 0.82 * fraction);
            }, Line, token);
            if (built.Code != 0)
            {
                Ui(() => Fail(built.Error ?? "Le build s'est arrêté (code " + built.Code + ").", built.Tail));
                return;
            }
            if (!setup.Installed) throw new InvalidOperationException("Le build a rendu 0 mais " + Setup.GameExe + " n'est pas là.");
            setup.WriteVersion(source);
            Shell.MakeShortcuts(setup, desktop, startMenu);
            Ui(() =>
            {
                clock.Stop();
                ShowDone();
            });
        }
        catch (OperationCanceledException)
        {
            Ui(Cancelled);
        }
        catch (Exception e) when (e is IOException or InvalidOperationException or UnauthorizedAccessException or ArgumentException)
        {
            Ui(() => Fail(e.Message, ""));
        }
        finally
        {
            guard?.Dispose();
            if (IsHandleCreated && !IsDisposed) Ui(() => clock.Stop());
        }
    }

    void Fail(string why, string detail)
    {
        building = false;
        clock.Stop();
        Line("error " + why);
        var said = why;
        if (detail.Length > 0)
        {
            var lines = detail.Split('\n', StringSplitOptions.RemoveEmptyEntries);
            if (lines.Length > 0) said += "\n\n" + string.Join("\n", lines.TakeLast(5));
        }
        MessageBox.Show(this, said, Setup.Name + " — le build s'est arrêté", MessageBoxButtons.OK, MessageBoxIcon.Error);
        ShowGame();
        if (errorLabel != null) errorLabel.Text = why;
        if (verifyLabel != null) verifyLabel.Text = verification ?? "";
        if (next != null) next.Enabled = setup.HasGame;
    }

    void Cancelled()
    {
        building = false;
        clock.Stop();
        Line("(annulé : ce qui est déjà compilé est gardé, le build reprend)");
        if (closing) return;
        MessageBox.Show(this,
            "Le build est annulé. Ce qui a déjà été lu et compilé est gardé dans le dossier : le relancer reprend là où il " +
            "s'est arrêté.", Setup.Name, MessageBoxButtons.OK, MessageBoxIcon.Information);
        if (setup.Installed) ShowLauncher();
        else ShowGame();
    }

    // ---------------------------------------------------------------- footer actions

    void NextClicked()
    {
        switch (current)
        {
            case Page.Welcome: ShowGame(); break;
            case Page.Game: if (setup.HasGame) ShowFolder(); break;
            case Page.Folder:
                if (setup.Installed)
                {
                    if (setup.GameIsRunning())
                    {
                        MessageBox.Show(this, "Fermez OcaDim avant de le mettre à jour.", Setup.Name, MessageBoxButtons.OK, MessageBoxIcon.Information);
                        return;
                    }
                    ShowBuild(true);
                }
                else ShowBuild(false);
                break;
            case Page.Build: AskCancel(); break;
            case Page.Done: Shell.Play(setup); break;
            case Page.Launcher: Shell.Play(setup); break;
        }
    }

    void BackClicked()
    {
        if (building) return;
        switch (current)
        {
            case Page.Game: ShowWelcome(); break;
            case Page.Folder: ShowGame(); break;
            case Page.Build: break;
            case Page.Done: ShowLauncherOrWelcome(); break;
            case Page.Launcher: break;
            default: ShowWelcome(); break;
        }
    }

    void AskCancel()
    {
        if (!building) return;
        var answer = MessageBox.Show(this,
            "Arrêter la compilation ? Ce qui est déjà fait est gardé (le build reprendra), mais la préparation des shaders en " +
            "cours sera perdue.", Setup.Name, MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
        if (answer != DialogResult.Yes) return;
        status.Text = "Arrêt en cours…";
        next.Enabled = false;
        cancel?.Cancel();
    }

    void Uninstall()
    {
        var answer = MessageBox.Show(this, "Désinstaller OcaDim et supprimer " + setup.InstallDir + " (jeu, outils, réglages et " +
                                          "sauvegardes) ?", Setup.Name, MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
        if (answer != DialogResult.Yes) return;
        try
        {
            Shell.Uninstall(setup);
            MessageBox.Show(this, Setup.Name + " a été désinstallé.", Setup.Name, MessageBoxButtons.OK, MessageBoxIcon.Information);
            Close();
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or InvalidOperationException)
        {
            MessageBox.Show(this, e.Message, Setup.Name, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    void ChooseNup()
    {
        using var d = new OpenFileDialog
        {
            Title = "Votre copie du jeu (.nup)",
            Filter = "Votre copie du jeu (*.nup)|*.nup|Tous les fichiers (*.*)|*.*",
            CheckFileExists = true,
        };
        if (d.ShowDialog(this) != DialogResult.OK) return;
        try
        {
            setup.Choose(d.FileName);
            verification = null;
            ShowGame();
        }
        catch (Exception e) when (e is IOException or ArgumentException or FileNotFoundException) { Complain(e); }
    }

    void ChooseFolders()
    {
        using var romfs = new FolderBrowserDialog { Description = "Le dossier romfs de votre copie" };
        if (romfs.ShowDialog(this) != DialogResult.OK) return;
        using var exefs = new FolderBrowserDialog { Description = "Le dossier exefs de votre copie" };
        if (exefs.ShowDialog(this) != DialogResult.OK) return;
        try
        {
            setup.ChooseFolders(romfs.SelectedPath, exefs.SelectedPath);
            verification = null;
            ShowGame();
        }
        catch (Exception e) when (e is IOException or ArgumentException or DirectoryNotFoundException) { Complain(e); }
    }

    void Complain(Exception e) =>
        MessageBox.Show(this, e.Message, Setup.Name, MessageBoxButtons.OK, MessageBoxIcon.Warning);

    // ---------------------------------------------------------------- moving parts

    void Begin(Page page, string stepText)
    {
        current = page;
        body.SuspendLayout();
        body.Controls.Clear();
        body.AutoScrollPosition = new Point(0, 0);
        body.ResumeLayout();
        step.Text = stepText;
        status.Text = "";
        next.Visible = true;
        back.Visible = true;
        next.Enabled = true;
    }

    void Add(Control control)
    {
        if (control is Label { AutoSize: true } label) label.MaximumSize = new Size(ContentWidth, 0);
        if (!control.AutoSize) control.Width = Math.Min(control.Width, ContentWidth);
        var top = body.Controls.Count == 0 ? 6 : body.Controls.Cast<Control>().Max(c => c.Bottom) + 8;
        body.Controls.Add(control);
        control.Left = 36;
        control.Top = top;
    }

    /// A row of controls side by side (a Panel, not a FlowLayoutPanel: that one kept its default 100 px height and
    /// left a hole under each row of buttons)
    Panel Row(params Control[] items)
    {
        var row = new Panel { Height = items.Max(c => c.Height) + 2, BackColor = Color.Transparent };
        var x = 0;
        foreach (var item in items)
        {
            item.Left = x;
            item.Top = 0;
            row.Controls.Add(item);
            x += item.Width + 12;
        }
        row.Width = Math.Max(0, x - 12);
        return row;
    }

    Label Heading(string text) => new()
    {
        Text = text, AutoSize = true, ForeColor = Paper, Font = new Font("Segoe UI Semibold", 16f, FontStyle.Bold),
    };

    Label Paragraph(string text) => new()
    {
        Text = text, AutoSize = true, ForeColor = Paper, MaximumSize = new Size(ContentWidth, 0),
        Font = new Font("Segoe UI", 10f),
    };

    Label Bullet(string text) => new()
    {
        Text = "•   " + text, AutoSize = true, ForeColor = Paper, MaximumSize = new Size(ContentWidth, 0),
        Font = new Font("Segoe UI", 10f),
    };

    CheckBox Check(string text, bool value) => new()
    {
        Text = text, AutoSize = true, Checked = value, ForeColor = Paper,
        MaximumSize = new Size(ContentWidth, 0),
    };

    Button GoldButton(string text)
    {
        var b = new Button
        {
            Text = text, Width = 128, Height = 36, FlatStyle = FlatStyle.Flat, BackColor = Gold, ForeColor = Ink,
            Font = new Font("Segoe UI Semibold", 10f, FontStyle.Bold), Cursor = Cursors.Hand,
        };
        b.FlatAppearance.BorderSize = 0;
        return b;
    }

    Button QuietButton(string text)
    {
        var b = new Button
        {
            Text = text, Width = 150, Height = 36, FlatStyle = FlatStyle.Flat, BackColor = Card, ForeColor = Paper,
            Font = new Font("Segoe UI", 10f), Cursor = Cursors.Hand,
        };
        b.FlatAppearance.BorderColor = Color.FromArgb(0x45, 0x3B, 0x32);
        return b;
    }

    void SetFooter(string said, string button, bool showNext, bool showBack)
    {
        status.Text = said;
        next.Text = button;
        next.Visible = showNext && button.Length > 0;
        back.Visible = showBack;
    }

    void Stage(string text, double fraction)
    {
        shown = Math.Clamp(fraction, 0, 1);
        Ui(() =>
        {
            if (stageLabel != null) stageLabel.Text = text;
            if (bar != null) bar.Value = (int)(shown * 1000);
            if (percentLabel != null) percentLabel.Text = string.Format(System.Globalization.CultureInfo.InvariantCulture,
                "{0:0} %", shown * 100);
        });
    }

    void Line(string text)
    {
        Ui(() =>
        {
            if (logBox == null) return;
            logBox.AppendText(text + Environment.NewLine);
            if (logBox.TextLength > 60000) logBox.Text = logBox.Text[^40000..];
        });
    }

    void Ui(Action action)
    {
        if (!IsHandleCreated || IsDisposed) return;
        if (InvokeRequired)
        {
            try { BeginInvoke(action); }
            catch (InvalidOperationException) { }
        }
        else action();
    }

    void Tick()
    {
        if (elapsedLabel == null) return;
        var span = DateTime.Now - started;
        elapsedLabel.Text = string.Format("Temps écoulé : {0} · la première compilation prend environ 40 minutes",
            span.TotalHours >= 1
                ? string.Format("{0:0} h {1:00} min", span.TotalHours, span.Minutes)
                : string.Format("{0:0} min {1:00} s", span.TotalMinutes, span.Seconds));
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        if (building)
        {
            var answer = MessageBox.Show(this, "Une compilation est en cours. Quitter l'arrête (le dossier restera " +
                                               "reprenable). Quitter ?", Setup.Name, MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
            if (answer != DialogResult.Yes) { e.Cancel = true; return; }
            closing = true;
            cancel?.Cancel();
            try { running?.Wait(TimeSpan.FromSeconds(20)); } catch (AggregateException) { }
        }
        base.OnFormClosing(e);
    }
}
