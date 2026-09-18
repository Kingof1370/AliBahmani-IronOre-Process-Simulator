; Inno Setup Script - AliBahmani_IronOre_Process_Simulator_Setup.exe
; Build on Windows with Inno Setup 6:  ISCC.exe AliBahmani_IronOre_Process_Simulator.iss
; Prerequisite: PyInstaller onefile build already produced dist\AliBahmani_IronOre_Process_Simulator.exe

#define MyAppName "AliBahmani IronOre Process Simulator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Ali Bahmani"
#define MyAppExeName "AliBahmani_IronOre_Process_Simulator.exe"

[Setup]
AppId={{8E4C2A61-9B7D-4F3A-B6E2-ALI0420558OK}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=""
DefaultDirName={autopf}\AliBahmani\IronOreProcessSimulator
DefaultGroupName={#MyAppName}
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputBaseFilename=AliBahmani_IronOre_Process_Simulator_Setup
OutputDir=SETUP_OUTPUT
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "farsi"; MessagesFile: "compiler:Languages\Farsi.isl"

[Files]
Source: "dist\AliBahmani_IronOre_Process_Simulator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\RELEASE\EXCEL_REPORTS\*"; DestDir: "{app}\Samples\ExcelReports"; Flags: ignoreversion recursesubdirs
Source: "..\RELEASE\CAD_OUTPUT\*"; DestDir: "{app}\Samples\CAD"; Flags: ignoreversion recursesubdirs
Source: "..\RELEASE\VIDEO_OUTPUT\*"; DestDir: "{app}\Samples\Video"; Flags: ignoreversion recursesubdirs
Source: "..\docs\*"; DestDir: "{app}\Docs"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringName(MyAppName)}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\Samples"
