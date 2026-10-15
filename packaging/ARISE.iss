#define AppVersion "0.4.16"
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
SetupIconFile=..\artifacts\arise.ico
UsePreviousAppDir=yes
CloseApplications=yes
RestartApplications=no
SetupMutex=ARISE-Setup
VersionInfoVersion={#AppVersion}
UninstallDisplayIcon={app}\arise-{#AppVersion}.ico
[Files]
Source: "..\artifacts\arise.ico"; DestDir: "{app}"; DestName: "arise-{#AppVersion}.ico"; Flags: ignoreversion
Source: "..\arise_app\resources\stop-arise.ps1"; Flags: dontcopy
Source: "..\dist\ARISE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\bundle\node"
[Icons]
Name: "{group}\ARISE"; Filename: "{app}\ARISE.exe"; IconFilename: "{app}\arise-{#AppVersion}.ico"; AppUserModelID: "PRAXISGENAI.ARISE"
Name: "{group}\Configurar ARISE"; Filename: "{app}\ARISE.exe"; Parameters: "--settings"; IconFilename: "{app}\arise-{#AppVersion}.ico"
Name: "{autodesktop}\ARISE"; Filename: "{app}\ARISE.exe"; IconFilename: "{app}\arise-{#AppVersion}.ico"; AppUserModelID: "PRAXISGENAI.ARISE"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Crear acceso directo en el escritorio"; Flags: unchecked
[Run]
Filename: "{app}\ARISE.exe"; Parameters: "{code:LaunchParameters}"; Description: "Abrir ARISE Assistant"; Flags: nowait postinstall

[Code]
procedure SHChangeNotify(EventId: Integer; Flags: Cardinal; Item1, Item2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    SHChangeNotify($08000000, 0, 0, 0);
end;

function DataDirectory(): String;
begin
  Result := ExpandConstant('{param:ARISE-DATA}');
  if Result = '' then Result := ExpandConstant('{localappdata}\ARISE-Orb');
end;

function LaunchParameters(Param: String): String;
var
  Models: String;
begin
  Result := '--data-dir "' + DataDirectory() + '"';
  Models := ExpandConstant('{param:ARISE-MODELS}');
  if Models <> '' then Result := Result + ' --setup-pack "' + Models + '"'
  else if ExpandConstant('{param:ARISE-SETUP|1}') <> '0' then
    Result := Result + ' --setup';
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode: Integer;
  Args: String;
begin
  Result := '';
  ExtractTemporaryFile('stop-arise.ps1');
  Args := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{tmp}\stop-arise.ps1') + '" -InstallDir "' + ExpandConstant('{app}') + '" -DataDir "' + DataDirectory() + '"';
  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Args, '', SW_HIDE, ewWaitUntilTerminated, ExitCode) or (ExitCode <> 0) then
    Result := 'No se pudieron cerrar los procesos de ARISE. Cierra ARISE y vuelve a intentar; no se reemplazaron archivos.';
end;
