; Aqua Focus — Inno Setup installer
; Requires: Inno Setup 6
; Build exe first:  .\scripts\build_exe.ps1
; Target OS: Windows 11 / Windows 10 (same binary)
; Also supported (other installers): macOS · Ubuntu · Linux — see docs/platforms.md
; Bundled with PyInstaller: imageio-ffmpeg binaries (no separate ffmpeg install)
; App UI language (JA/EN) is chosen inside Aqua Focus, not only by this wizard.

#define MyAppName "Aqua Focus"
#define MyAppVersion "2.1.5"
#define MyAppPublisher "Kokona"
#define MyAppExeName "AquaFocus.exe"

[Setup]
AppId={{8F3C2A91-7B4E-4D6A-9C1F-AQUAFOCUS2026}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AquaFocus
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=AquaFocusSetup-{#MyAppVersion}
SetupIconFile=..\assets\icons\aqua-focus.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\AquaFocus\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
