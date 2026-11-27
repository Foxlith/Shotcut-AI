; -- shotcut-ai.iss --
; The installer of Shotcut AI for Windows (Inno Setup 6), made by the workflow
; .github/workflows/build-windows-shotcut-ai.yml from the portable folder dist\Shotcut-AI:
;
;   ISCC.exe /DAppVersion=26.11.27 packaging\windows\shotcut-ai.iss
;
; It installs for the current user without asking for administrator rights (an
; administrator can choose all users), asks whether to put a shortcut on the desktop
; (checked by default) and adds Shotcut AI to the Start menu. The upstream installer of
; Shotcut (shotcut.iss) stays as it is.
;
; This program is free software: you can redistribute it and/or modify
; it under the terms of the GNU General Public License as published by
; the Free Software Foundation, either version 3 of the License, or
; (at your option) any later version.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\Shotcut-AI"
#endif

[Setup]
; Its own id, so it never replaces an installed Shotcut.
AppId={{6F1C2B7E-5A43-4C1D-9E2B-0B7A3C5D8E21}
AppName=Shotcut AI
AppVersion={#AppVersion}
AppVerName=Shotcut AI {#AppVersion}
AppPublisher=Foxlith
AppPublisherURL=https://github.com/Foxlith/Shotcut-AI
DefaultDirName={autopf}\Shotcut AI
DefaultGroupName=Shotcut AI
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\COPYING
SetupIconFile=shotcut-logo-64.ico
UninstallDisplayIcon={app}\bin\shotcut.exe
UninstallDisplayName=Shotcut AI
WizardStyle=modern
WizardSmallImageFile=shotcut-logo-64.bmp
Compression=lzma2/max
SolidCompression=yes
OutputDir=..\..\dist
OutputBaseFilename=Shotcut-AI-Setup
; Shotcut AI holds this mutex while it runs (src/main.cpp): close it before updating.
AppMutex="Meltytech Shotcut Running Mutex"
CloseApplications=yes
UsePreviousTasks=yes
ShowLanguageDialog=auto

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
; "Create a desktop shortcut", in the language of the installer; checked by default.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Shotcut AI"; Filename: "{app}\bin\shotcut.exe"; WorkingDir: "{userdocs}"
Name: "{autodesktop}\Shotcut AI"; Filename: "{app}\bin\shotcut.exe"; WorkingDir: "{userdocs}"; Tasks: desktopicon

[Run]
Filename: "{app}\bin\shotcut.exe"; Description: "{cm:LaunchProgram,Shotcut AI}"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
; Python writes its caches next to the scripts.
Type: filesandordirs; Name: "{app}\share\shotcut\mcp\__pycache__"
