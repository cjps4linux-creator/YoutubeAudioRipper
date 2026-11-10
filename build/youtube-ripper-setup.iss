; Inno Setup script for YouTube Audio Ripper
; Compile with: ISCC.exe build/youtube-ripper-setup.iss
; Download Inno Setup: https://jrsoftware.org/isinfo.php

#define MyAppName "YouTube Audio Ripper"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "Conrad CJ Wilson"
#define MyAppURL "https://github.com/cjps4linux-creator/Youtube-Audio-Ripper"
#define MyAppExeName "YouTube Audio Ripper.exe"

[Setup]
AppId={{{E1A2B3C4-D5E6-4F7A-8B9C-0D1E2F3A4B5C}}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=YouTube-Audio-Ripper-{#MyAppVersion}-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Source: The PyInstaller dist folder
Source: "dist\YouTube Audio Ripper\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; FFmpeg binary (bundled with the app)
Source: "dist\YouTube Audio Ripper\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\YouTube Audio Ripper\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesanddirs; Name: "{app}\ripped_music"
Type: filesanddirs; Name: "{app}\downloads.json"
Type: filesanddirs; Name: "{app}\settings.json"
Type: filesanddirs; Name: "{app}\youtube_ripper.log"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
