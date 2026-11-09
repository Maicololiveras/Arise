#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef TargetArch
  #error TargetArch is required
#endif
#ifndef AppTitle
  #define AppTitle "ARISE Preview"
#endif
#ifndef AppIdentity
  #define AppIdentity "PRAXISGENAI.ARISE.NativePreview"
#endif
#ifndef AppFolder
  #define AppFolder "ARISE-Native-Preview"
#endif
[Setup]
AppId={#AppIdentity}
AppName={#AppTitle}
AppVersion={#AppVersion}
AppPublisher=PRAXISGENAI
DefaultDirName={localappdata}\Programs\{#AppFolder}
DefaultGroupName={#AppTitle}
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
Name: "{group}\{#AppTitle}"; Filename: "{app}\ARISE.exe"
Name: "{group}\Uninstall {#AppTitle}"; Filename: "{uninstallexe}"
[Run]
Filename: "{app}\ARISE.exe"; Description: "Open {#AppTitle}"; Flags: nowait postinstall skipifsilent
