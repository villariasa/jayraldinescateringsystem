[Setup]
AppName=Jayraldines Catering
AppVersion=4.0.6
AppPublisher=Jayraldine's Catering Services
AppPublisherURL=https://jayraldinescatering.com
AppSupportURL=https://jayraldinescatering.com/support
AppUpdatesURL=https://jayraldinescatering.com/updates
DefaultDirName={autopf}\JayraldinesCatering
DefaultGroupName=Jayraldines Catering
OutputDir=installer_output
OutputBaseFilename=JayraldinesSetup_v4.0.6
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
Source: "analytics_functions_migration.sql"; DestDir: "{app}"; Flags: ignoreversion
Source: "fix_customer_ledger_view.sql"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Jayraldines Catering"; Filename: "{app}\JayraldinesCatering.exe"
Name: "{commondesktop}\Jayraldines Catering"; Filename: "{app}\JayraldinesCatering.exe"; Tasks: desktopicon
Name: "{group}\Setup Database"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\setup.ps1"""; WorkingDir: "{app}"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\JayraldinesCatering.exe"; Description: "Launch Jayraldines Catering"; Flags: postinstall nowait skipifsilent
