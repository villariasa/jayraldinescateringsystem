[Setup]
AppName=Jayraldine's Catering Kiosk Server
AppVersion=1.0.2
AppPublisher=Jayraldine's Catering Services
DefaultDirName={autopf}\JayraldinesCateringKioskServer
DefaultGroupName=Jayraldine's Catering Kiosk Server
OutputDir=/home/villarias/Projects/jayraldinescateringsystem/Tablet_PWA/installer_output
OutputBaseFilename=Jayraldines_Kiosk_Server_Setup_v1.0.2
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Start the kiosk server automatically when this PC turns on (recommended)"; GroupDescription: "Startup:"; Flags: checkedonce

[Files]
Source: "/home/villarias/Projects/jayraldinescateringsystem/Tablet_PWA/backend/dist/JayraldinesCateringKioskServer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Jayraldine's Catering Kiosk Server"; Filename: "{app}\JayraldinesCateringKioskServer.exe"
Name: "{autodesktop}\Jayraldine's Catering Kiosk Server"; Filename: "{app}\JayraldinesCateringKioskServer.exe"; Tasks: desktopicon
Name: "{userstartup}\Jayraldine's Catering Kiosk Server"; Filename: "{app}\JayraldinesCateringKioskServer.exe"; Tasks: autostart

[Run]
Filename: "{app}\JayraldinesCateringKioskServer.exe"; Description: "Start the kiosk server now"; Flags: nowait postinstall skipifsilent
