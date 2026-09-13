[Setup]
AppName=Jayraldines Catering
AppVersion=4.1.25
AppPublisher=Jayraldines Catering
DefaultDirName={autopf}\JayraldinesCatering
DefaultGroupName=Jayraldines Catering
OutputDir=installer_output
OutputBaseFilename=Jayraldines_Catering_Setup_v4.1.25
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
Source: "device_monitoring_migration.sql"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "tools\ngrok.exe"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\Tablet_PWA\frontend\*"; DestDir: "{app}\Tablet_PWA\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\Jayraldines Catering"; Filename: "{app}\JayraldinesCatering.exe"
Name: "{commondesktop}\Jayraldines Catering"; Filename: "{app}\JayraldinesCatering.exe"; Tasks: desktopicon
Name: "{group}\Setup Database"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\setup.ps1"""; WorkingDir: "{app}"
Name: "{group}\Tablet Kiosk Web App"; Filename: "{app}\Tablet_PWA\frontend\index.html"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\JayraldinesCatering.exe"; Description: "Launch Jayraldines Catering"; Flags: postinstall nowait skipifsilent

[Code]
var
  NgrokPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  NgrokPage := CreateInputQueryPage(wpSelectTasks,
    'Online Remote Tablet Sync Setup',
    'Configure Ngrok to connect tablets & mobile devices online anywhere (Optional)',
    'To allow tablets and mobile phones to connect over the internet without being on the same local Wi-Fi, enter your free Ngrok Authtoken below.' + #13#10 + #13#10 +
    'Get your free token at: https://dashboard.ngrok.com/get-started/your-authtoken' + #13#10 + #13#10 +
    'Note: You can leave this blank to skip and configure it later in Settings.');
  NgrokPage.Add('Ngrok Authtoken (Optional):', False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Token: string;
  ResultCode: Integer;
  NgrokExe: string;
  EnvFile: string;
  EnvContent: string;
begin
  if CurStep = ssPostInstall then
  begin
    Token := Trim(NgrokPage.Values[0]);
    NgrokExe := ExpandConstant('{app}\tools\ngrok.exe');
    if (Token <> '') and FileExists(NgrokExe) then
    begin
      // Configure authtoken in ngrok.exe
      Exec(NgrokExe, 'config add-authtoken ' + Token, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);

      // Save to .env for application persistence
      EnvFile := ExpandConstant('{app}\.env');
      if FileExists(EnvFile) then
      begin
        LoadStringFromFile(EnvFile, EnvContent);
        EnvContent := EnvContent + #13#10 + 'NGROK_AUTHTOKEN=' + Token + #13#10 + 'NGROK_ENABLED=1' + #13#10;
        SaveStringToFile(EnvFile, EnvContent, False);
      end
      else
      begin
        EnvContent := 'NGROK_AUTHTOKEN=' + Token + #13#10 + 'NGROK_ENABLED=1' + #13#10;
        SaveStringToFile(EnvFile, EnvContent, False);
      end;
    end;
  end;
end;
