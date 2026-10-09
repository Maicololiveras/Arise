#define AppVersion "0.3.0"
[Setup]
AppId={{E99B270E-3F4F-421C-9D9F-705E523F3ED6}
AppName=ARISE
AppVersion={#AppVersion}
AppPublisher=PRAXISGENAI
AppPublisherURL=https://github.com/Maicololiveras/Arise
DefaultDirName={localappdata}\Programs\ARISE
DefaultGroupName=ARISE
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=ARISE-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\ARISE.exe
[Files]
Source: "..\dist\ARISE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\ARISE"; Filename: "{app}\ARISE.exe"
Name: "{group}\Configurar ARISE"; Filename: "{app}\ARISE.exe"; Parameters: "--settings"
Name: "{autodesktop}\ARISE"; Filename: "{app}\ARISE.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Crear acceso directo en el escritorio"; Flags: unchecked
[Run]
Filename: "{app}\ARISE.exe"; Description: "Configurar ARISE"; Flags: nowait postinstall skipifsilent
