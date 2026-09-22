; drawl installer - Inno Setup 6
; Compiled by tools/build.ps1, which first produces dist/drawl/ with PyInstaller.

#define AppName "drawl"
#define AppVersion "0.1.0"
#define AppPublisher "Gabriele Portente"
#define AppExe "drawl.exe"

[Setup]
AppId={{7C3A1E62-4F8D-4C2B-9A1E-2D5B8F0A6E31}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
OutputDir=..\dist
OutputBaseFilename=drawl-{#AppVersion}-setup
SetupIconFile=..\drawl\ui\drawl.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Installs for the current user: no administrator elevation needed.
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startup"; Description: "{cm:StartWithWindows}"; GroupDescription: "{cm:StartupGroup}"

[CustomMessages]
english.StartWithWindows=Start drawl when you sign in to Windows
italian.StartWithWindows=Avvia drawl all'accesso a Windows
english.StartupGroup=Startup
italian.StartupGroup=Avvio

[Files]
Source: "..\dist\drawl\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Downloaded models and settings are left alone: reinstalling should not mean
; downloading 490 MB again. To remove them for good, delete %LOCALAPPDATA%\drawl
; by hand.
Type: dirifempty; Name: "{app}"

[Messages]
english.WelcomeLabel2=This will install [name/ver] on your computer.%n%nOn first launch drawl downloads the speech recognition model (about 490 MB) into %localappdata%\drawl. An internet connection is needed only for that step: everything works offline afterwards.
italian.WelcomeLabel2=Verra' installato [name/ver] sul computer.%n%nAl primo avvio drawl scarica il modello di riconoscimento vocale (circa 490 MB) in %localappdata%\drawl. Serve una connessione a Internet solo per quel passaggio: dopo, tutto funziona offline.
