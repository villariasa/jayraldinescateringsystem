[Setup]
AppName=Jayraldines Catering
AppVersion=4.1.8
AppPublisher=Jayraldines Catering
DefaultDirName={autopf}\JayraldinesCatering
DefaultGroupName=Jayraldines Catering
OutputDir=installer_output
OutputBaseFilename=Jayraldines_Catering_Setup_v4.1.8
SetupIconFile=assets\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\JayraldinesCatering\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "jayraldines_catering_clean.sql"; DestDir: "{app}"; Flags: ignoreversion
Source: "cebu_address_migration.sql"; DestDir: "{app}"; Flags: ignoreversion
Source: "occasions_migration.sql"; DestDir: "{app}"; Flags: ignoreversion
Source: "confirmed_only_views_migration.sql"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Jayraldines Catering"; Filename: "{app}\JayraldinesCatering.exe"
Name: "{commondesktop}\Jayraldines Catering"; Filename: "{app}\JayraldinesCatering.exe"; Tasks: desktopicon
Name: "{group}\Setup Database"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\setup.ps1"""; WorkingDir: "{app}"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\JayraldinesCatering.exe"; Description: "Launch Jayraldines Catering"; Flags: postinstall nowait skipifsilent
