#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef TargetArch
  #error TargetArch is required
#endif
[Setup]
AppId=PRAXISGENAI.ARISE.NativePreview
AppName=ARISE Native Preview
AppVersion={#AppVersion}
AppPublisher=PRAXISGENAI
DefaultDirName={localappdata}\Programs\ARISE-Native-Preview
DefaultGroupName=ARISE Native Preview
PrivilegesRequired=lowest
ArchitecturesAllowed={#TargetArch}
ArchitecturesInstallIn64BitMode={#TargetArch}
MinVersion=10.0.22000
OutputDir=..\artifacts
OutputBaseFilename=ARISE-{#AppVersion}-windows-{#TargetName}-Setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\ARISE.exe
[Files]
Source: "..\dist\ARISE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\bundle"
[Icons]
Name: "{group}\ARISE Native Preview"; Filename: "{app}\ARISE.exe"
Name: "{group}\Uninstall ARISE Native Preview"; Filename: "{uninstallexe}"
[Run]
Filename: "{app}\ARISE.exe"; Description: "Open ARISE Native Preview"; Flags: nowait postinstall skipifsilent
