#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{B5DE1DA2-5F2A-4EB2-B719-CC1B8B502CA6}
AppName=TrackRight
AppVersion={#AppVersion}
AppPublisher=TrackRight
SetupIconFile=assets\trackright.ico
DefaultDirName={localappdata}\Programs\TrackRight
DefaultGroupName=TrackRight
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist\installer
OutputBaseFilename=TrackRight-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
Uninstallable=yes
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\TrackRight.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\TrackRight"; Filename: "{app}\TrackRight.exe"
Name: "{autodesktop}\TrackRight"; Filename: "{app}\TrackRight.exe"

[Run]
Filename: "{app}\TrackRight.exe"; Description: "Launch TrackRight"; \
    Flags: postinstall nowait skipifsilent
