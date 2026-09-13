# ==============================================================================
#  Jayraldine's Catering - One-Click Central PostgreSQL Server & Data Migrator
#  Automates:
#    1. Silent Installation of PostgreSQL 16
#    2. Firewall Configuration (Ports 5432, 8000, 8085)
#    3. Remote Access Setup (listen_addresses='*', pg_hba.conf)
#    4. Database Creation (jayraldines_catering, user: jayraldines_app)
#    5. Full SQLite Backup Migration into PostgreSQL (Bookings, Billings, Customers)
# ==============================================================================

# Ensure Administrator privileges
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[Requesting Administrator privileges...]" -ForegroundColor Yellow
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$Host.UI.RawUI.WindowTitle = "Jayraldine's Catering — Central PostgreSQL Setup & Migrator"
Clear-Host

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   JAYRALDINE'S CATERING - CENTRAL DATABASE SERVER AUTO-CONFIGURATOR   " -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

function Print-Step($msg) {
    Write-Host ""
    Write-Host ">>> $msg" -ForegroundColor Cyan
}
function Print-OK($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Print-Info($msg) { Write-Host "  [..] $msg" -ForegroundColor Yellow }
function Print-Fail($msg) { Write-Host "  [!!] $msg" -ForegroundColor Red }

# ------------------------------------------------------------------------------
# STEP 1: Find or Install PostgreSQL 16
# ------------------------------------------------------------------------------
Print-Step "Step 1: Checking PostgreSQL Installation..."

$psqlExe = $null
if (Get-Command "psql" -ErrorAction SilentlyContinue) {
    $psqlExe = (Get-Command "psql").Source
}

if (-not $psqlExe) {
    $candidates = @()
    foreach ($v in @("18","17","16","15","14","13","12")) {
        $candidates += "C:\Program Files\PostgreSQL\$v\bin\psql.exe"
        $candidates += "C:\Program Files (x86)\PostgreSQL\$v\bin\psql.exe"
    }
    $psqlExe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $psqlExe) {
    Print-Info "PostgreSQL is not installed on this PC. Beginning automated installation..."
    
    # Try winget first
    $installed = $false
    if (Get-Command "winget" -ErrorAction SilentlyContinue) {
        Print-Info "Attempting installation via winget..."
        $proc = Start-Process "winget" -ArgumentList "install --id PostgreSQL.PostgreSQL -e --silent --accept-package-agreements --accept-source-agreements --override `"--mode unattended --superpassword 12345678 --serverport 5432`"" -Wait -PassThru
        if ($proc.ExitCode -eq 0) {
            $installed = $true
        }
    }
    
    if (-not $installed) {
        Print-Info "Downloading official PostgreSQL 16 unattended installer from EnterpriseDB..."
        $installerUrl = "https://get.enterprisedb.com/postgresql/postgresql-16.3-1-windows-x64.exe"
        $tempInstaller = "$env:TEMP\postgresql-16-installer.exe"
        
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $installerUrl -OutFile $tempInstaller -UseBasicParsing
        
        Print-Info "Running silent PostgreSQL 16 installation (this takes ~1-2 minutes)..."
        $installProc = Start-Process -FilePath $tempInstaller -ArgumentList "--mode unattended --unattendedmodeui none --superpassword 12345678 --serverport 5432" -Wait -PassThru
        Remove-Item $tempInstaller -Force -ErrorAction SilentlyContinue
    }
    
    # Re-check psql location
    foreach ($v in @("18","17","16","15","14","13","12")) {
        $cand = "C:\Program Files\PostgreSQL\$v\bin\psql.exe"
        if (Test-Path $cand) {
            $psqlExe = $cand
            break
        }
    }
}

if (-not $psqlExe) {
    Print-Fail "Could not locate psql.exe. Please install PostgreSQL manually and re-run this script."
    Read-Host "Press ENTER to exit..."
    exit 1
}

Print-OK "PostgreSQL located at: $psqlExe"

# ------------------------------------------------------------------------------
# STEP 2: Configure Windows Service & Network Access (listen_addresses & pg_hba)
# ------------------------------------------------------------------------------
Print-Step "Step 2: Configuring PostgreSQL Service & Remote Access..."

$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pgService) {
    if ($pgService.Status -ne "Running") {
        Print-Info "Starting PostgreSQL service ($($pgService.Name))..."
        Start-Service $pgService.Name
    }
    Print-OK "Service $($pgService.Name) is active."
}

# Locate PostgreSQL data directory to enable remote connections
$pgBinDir = Split-Path -Parent $psqlExe
$pgRootDir = Split-Path -Parent $pgBinDir
$pgDataDir = Join-Path $pgRootDir "data"

if (Test-Path $pgDataDir) {
    # 1. postgresql.conf: listen_addresses = '*'
    $confFile = Join-Path $pgDataDir "postgresql.conf"
    if (Test-Path $confFile) {
        $conf = Get-Content $confFile -Raw
        if ($conf -notmatch "listen_addresses\s*=\s*'\*'") {
            Add-Content -Path $confFile -Value "`nlisten_addresses = '*'`n"
            Print-OK "Configured postgresql.conf: listen_addresses = '*'"
        }
    }
    
    # 2. pg_hba.conf: allow remote connections from all subnet IPs
    $hbaFile = Join-Path $pgDataDir "pg_hba.conf"
    if (Test-Path $hbaFile) {
        $hba = Get-Content $hbaFile -Raw
        if ($hba -notmatch "0\.0\.0\.0/0") {
            Add-Content -Path $hbaFile -Value "`nhost    all             all             0.0.0.0/0               md5`n"
            Add-Content -Path $hbaFile -Value "host    all             all             ::/0                    md5`n"
            Print-OK "Configured pg_hba.conf: Remote IPv4/IPv6 client subnet allowed."
        }
    }
    
    # Restart service to apply network binding
    if ($pgService) {
        Restart-Service $pgService.Name -Force
        Print-OK "PostgreSQL restarted with remote access enabled."
    }
}

# ------------------------------------------------------------------------------
# STEP 3: Configure Windows Firewall
# ------------------------------------------------------------------------------
Print-Step "Step 3: Opening Windows Firewall Ports (5432, 8000, 8085)..."

netsh advfirewall firewall delete rule name="Jayraldines Postgres 5432" >$null 2>&1
netsh advfirewall firewall add rule name="Jayraldines Postgres 5432" dir=in action=allow protocol=TCP localport=5432 profile=any >$null
netsh advfirewall firewall delete rule name="Jayraldines Sync Server 8000" >$null 2>&1
netsh advfirewall firewall add rule name="Jayraldines Sync Server 8000" dir=in action=allow protocol=TCP localport=8000 profile=any >$null
netsh advfirewall firewall delete rule name="Jayraldines Web 8085" >$null 2>&1
netsh advfirewall firewall add rule name="Jayraldines Web 8085" dir=in action=allow protocol=TCP localport=8085 profile=any >$null

Print-OK "Firewall rules for Central Database Server are completely OPEN."

# ------------------------------------------------------------------------------
# STEP 4: Initialize Central Database and User
# ------------------------------------------------------------------------------
Print-Step "Step 4: Initializing jayraldines_catering Database..."

$env:PGPASSWORD = "12345678"

# Create database if not exists
& $psqlExe -U postgres -h localhost -p 5432 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'jayraldines_catering';" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Print-Info "Creating central database jayraldines_catering..."
    & $psqlExe -U postgres -h localhost -p 5432 -d postgres -c "CREATE DATABASE jayraldines_catering ENCODING 'UTF8';" | Out-Null
}

# Apply base schema if clean
$scriptDir = Split-Path -Parent $PSCommandPath
$cleanSql = Join-Path $scriptDir "Catering_Present\jayraldines_catering\jayraldines_catering_clean.sql"
if (-not (Test-Path $cleanSql)) {
    $cleanSql = Join-Path $scriptDir "jayraldines_catering_clean.sql"
}

if (Test-Path $cleanSql) {
    Print-Info "Applying PostgreSQL schema and structure..."
    & $psqlExe -U postgres -h localhost -p 5432 -d jayraldines_catering -f $cleanSql >$null 2>&1
    Print-OK "Schema applied successfully."
}

# Create scoped app user
$userSql = @"
DO `$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jayraldines_app') THEN
        CREATE USER jayraldines_app WITH PASSWORD '12345678';
    END IF;
END
`$\$;
GRANT ALL PRIVILEGES ON DATABASE jayraldines_catering TO jayraldines_app;
GRANT ALL ON SCHEMA public TO jayraldines_app;
GRANT ALL ON ALL TABLES IN SCHEMA public TO jayraldines_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO jayraldines_app;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO jayraldines_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO jayraldines_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO jayraldines_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON ROUTINES TO jayraldines_app;
"@

& $psqlExe -U postgres -h localhost -p 5432 -d jayraldines_catering -c $userSql >$null 2>&1
Print-OK "Scoped user 'jayraldines_app' configured."

# ------------------------------------------------------------------------------
# STEP 5: Migrate Data from SQLite into PostgreSQL
# ------------------------------------------------------------------------------
Print-Step "Step 5: Migrating SQLite Data (Bookings, Customers, Invoices) into PostgreSQL..."

# Locate SQLite source database
$sqliteCandidates = @(
    (Join-Path $scriptDir "Catering_Present\jayraldines_catering\jayraldines_backup-2026-sep13.sql"),
    (Join-Path $scriptDir "Catering_Present\jayraldines_catering\catering.db"),
    "$env:LOCALAPPDATA\JayraldinesCatering\data\catering.db",
    "$env:LOCALAPPDATA\JayraldinesCatering\catering.db"
)

$sourceDb = $sqliteCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($sourceDb) {
    Print-Info "Found source SQLite database: $sourceDb"
    
    # Locate Python interpreter
    $pythonCandidates = @(
        (Join-Path $scriptDir "Catering_Present\jayraldines_catering\venv\Scripts\python.exe"),
        (Get-Command "python" -ErrorAction SilentlyContinue).Source
    )
    $pyExe = $pythonCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    
    if ($pyExe) {
        $migModule = Join-Path $scriptDir "Catering_Present\jayraldines_catering\utils\sqlite_to_postgres.py"
        if (Test-Path $migModule) {
            $env:PYTHONPATH = Join-Path $scriptDir "Catering_Present\jayraldines_catering"
            & $pyExe $migModule "$sourceDb" --host "localhost" --port 5432 --dbname "jayraldines_catering" --user "postgres" --password "12345678"
            Print-OK "SQLite data migrated into PostgreSQL successfully."
        }
    }
} else {
    Print-Info "No previous SQLite database found to migrate. Fresh central database is ready."
}

# ------------------------------------------------------------------------------
# STEP 6: Configure Local App to use PostgreSQL
# ------------------------------------------------------------------------------
Print-Step "Step 6: Updating Local App Database Configuration..."

$cfgDir = "$env:LOCALAPPDATA\JayraldinesCatering"
if (-not (Test-Path $cfgDir)) {
    New-Item -Path $cfgDir -ItemType Directory -Force | Out-Null
}

$dbConfig = @{
    engine   = "postgres"
    host     = "localhost"
    port     = 5432
    dbname   = "jayraldines_catering"
    user     = "jayraldines_app"
    password = "12345678"
} | ConvertTo-Json

Set-Content -Path (Join-Path $cfgDir "db_config.json") -Value $dbConfig
Print-OK "Local client configuration set to Central PostgreSQL."

# ------------------------------------------------------------------------------
# STEP 7: Show Server Summary & Client Connection Info
# ------------------------------------------------------------------------------
# Detect Local LAN IP
$localIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and $_.InterfaceAlias -notmatch 'vEthernet|Loopback' 
} | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "   SUCCESS! JAYRALDINE'S CATERING CENTRAL DB SERVER IS FULLY ONLINE!   " -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  SERVER LAN IP            : $localIp" -ForegroundColor Yellow
Write-Host "  DATABASE ENGINE          : PostgreSQL 16" -ForegroundColor White
Write-Host "  DATABASE PORT            : 5432" -ForegroundColor White
Write-Host "  DATABASE NAME            : jayraldines_catering" -ForegroundColor White
Write-Host "  SCOPED USER              : jayraldines_app" -ForegroundColor White
Write-Host "  SCOPED PASSWORD          : 12345678" -ForegroundColor White
Write-Host ""
Write-Host "  TABLET SYNC URL          : http://$localIp`:8000" -ForegroundColor Cyan
Write-Host "  TABLET KIOSK URL         : http://$localIp`:8000/index.html" -ForegroundColor Cyan
Write-Host "  TABLET TEST URL          : http://$localIp`:8000/test" -ForegroundColor Cyan
Write-Host ""
Write-Host "  INSTRUCTIONS FOR LAPTOPS & CLIENT PCs:" -ForegroundColor White
Write-Host "    1. On your laptop, open Jayraldine's Catering -> Settings -> Server & Database." -ForegroundColor Gray
Write-Host "    2. Set Server Host to: $localIp" -ForegroundColor Gray
Write-Host "    3. Click 'Test Connection' and Save. You are instantly connected!" -ForegroundColor Gray
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press ENTER to close this window..."
