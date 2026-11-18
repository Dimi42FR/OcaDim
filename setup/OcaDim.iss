; OcaDim ??? Inno Setup 6 script (https://jrsoftware.org/isdl.php)
; Build the payload first (the game folder as packaged: ocadim.exe, ocadim_vk.dll, SDL*.dll,
; wgpu_native.dll, romfs + .hookshot_exefs, the caches, prompts, the FSR DLLs), then:
;   iscc setup\OcaDim.iss /DPayload="D:\Emulateur\Longshot-main"
; It writes setup\dist\OcaDim-Setup-0.0.2.exe
;
; The name the player sees is OcaDim 0.0.1; the files keep the longshot_* names on purpose (the game, its
; options, its logs and its caches are named that way inside, and renaming them would lose a player's settings).

#define AppName "OcaDim"
#define AppVersion "0.0.3"
#define AppExe "ocadim.exe"
#define AppPublisher "Dimi42FR"
#ifndef Payload
  #define Payload "..\build-payload"
#endif

[Setup]
AppId={{7C1E2A64-9E4B-4A11-9E4B-0C0FFEE0CAD1}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=OcaDim-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
SetupIconFile=..\assets\branding\ocadim.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName} {#AppVersion}
WizardSmallImageFile=..\assets\branding\ocadim-wizard.bmp
LicenseFile=..\LICENSE

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; (everything the playable folder has: the game, the renderer, the shipped shaders, the caches, FSR's DLLs)
Source: "{#Payload}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName} {#AppVersion}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName} {#AppVersion}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
