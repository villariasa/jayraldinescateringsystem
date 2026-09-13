# ==============================================================================
# JAYRALDINE'S CATERING - ENABLE PC SERVER REMOTE ACCESS
# Allows client workstations and tablets to connect to PostgreSQL & LAN Hub
# ==============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   CONFIGURING POSTGRESQL PC SERVER FOR REMOTE CLIENTS     " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Locate PostgreSQL Services and Data Directories
$pgServices = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\postgresql*" -ErrorAction SilentlyContinue

$dataDirs = @()

if ($pgServices) {
    foreach ($svc in $pgServices) {
        $img = $svc.ImagePath
        if ($img -match '-D\s+"([^"]+)"') {
            $dataDirs += $matches[1]
        } elseif ($img -match '-D\s+([^\s]+)') {
            $dataDirs += $matches[1]
        }
    }
}

# Also search standard PostgreSQL paths
$standardRoots = @(
    "C:\Program Files\PostgreSQL",
    "C:\Program Files (x86)\PostgreSQL"
)

foreach ($root in $standardRoots) {
    if (Test-Path $root) {
        $found = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $candidate = Join-Path $_.FullName "data"
            if (Test-Path (Join-Path $candidate "pg_hba.conf")) {
                $candidate
            }
        }
        if ($found) {
            $dataDirs += $found
        }
    }
}

# Remove duplicates
$dataDirs = $dataDirs | Select-Object -Unique

if ($dataDirs.Count -eq 0) {
    Write-Host "[WARNING] No PostgreSQL data directory automatically detected." -ForegroundColor Yellow
    Write-Host "Please ensure PostgreSQL is installed on this PC." -ForegroundColor Yellow
} else {
    foreach ($dir in $dataDirs) {
        Write-Host "[INFO] Processing PostgreSQL data dir: $dir" -ForegroundColor Green
        
        # A. Configure postgresql.conf
        $confPath = Join-Path $dir "postgresql.conf"
        if (Test-Path $confPath) {
            $confContent = Get-Content $confPath -Raw -Encoding UTF8
            if ($confContent -notmatch "listen_addresses\s*=\s*'\*'") {
                Add-Content -Path $confPath -Value "`n# Added by Jayraldine's Catering Server Setup`nlisten_addresses = '*'`n" -Encoding UTF8
                Write-Host "  [OK] Updated postgresql.conf: listen_addresses = '*'" -ForegroundColor Green
            } else {
                Write-Host "  [OK] postgresql.conf already configured to listen on all interfaces." -ForegroundColor Gray
            }
        }

        # B. Configure pg_hba.conf
        $hbaPath = Join-Path $dir "pg_hba.conf"
        if (Test-Path $hbaPath) {
            $hbaContent = Get-Content $hbaPath -Raw -Encoding UTF8
            
            $needsAdd = $false
            if ($hbaContent -notmatch "0\.0\.0\.0/0") {
                $needsAdd = $true
            }

            if ($needsAdd) {
                $remoteRules = @"

# ==============================================================================
# Jayraldine's Catering - Allow all LAN client workstations and tablets
# ==============================================================================
host    all             all             0.0.0.0/0               scram-sha-256
host    all             all             0.0.0.0/0               md5
host    all             all             0.0.0.0/0               trust
host    all             all             ::/0                    scram-sha-256
host    all             all             ::/0                    md5
host    all             all             ::/0                    trust
"@
                Add-Content -Path $hbaPath -Value $remoteRules -Encoding UTF8
                Write-Host "  [OK] Updated pg_hba.conf: Remote workstations and tablets allowed." -ForegroundColor Green
            } else {
                Write-Host "  [OK] pg_hba.conf already allows remote subnets (0.0.0.0/0)." -ForegroundColor Gray
            }
        }
    }
}

# 2. Configure Windows Firewall
Write-Host ""
Write-Host "[INFO] Opening Windows Firewall for Ports 5432, 8000, 8085..." -ForegroundColor Cyan

netsh advfirewall firewall delete rule name="Jayraldines Postgres 5432" >$null 2>&1
netsh advfirewall firewall add rule name="Jayraldines Postgres 5432" dir=in action=allow protocol=TCP localport=5432 profile=any >$null

netsh advfirewall firewall delete rule name="Jayraldines Sync Server 8000" >$null 2>&1
netsh advfirewall firewall add rule name="Jayraldines Sync Server 8000" dir=in action=allow protocol=TCP localport=8000 profile=any >$null

netsh advfirewall firewall delete rule name="Jayraldines Web 8085" >$null 2>&1
netsh advfirewall firewall add rule name="Jayraldines Web 8085" dir=in action=allow protocol=TCP localport=8085 profile=any >$null

netsh advfirewall firewall delete rule name="Allow ICMPv4-In (Ping)" >$null 2>&1
netsh advfirewall firewall add rule name="Allow ICMPv4-In (Ping)" protocol=icmpv4:8,any dir=in action=allow profile=any >$null

Write-Host "  [OK] Windows Firewall rules are completely OPEN." -ForegroundColor Green

# 3. Restart PostgreSQL Service
Write-Host ""
Write-Host "[INFO] Restarting PostgreSQL Windows Service..." -ForegroundColor Cyan
$servicesToRestart = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($servicesToRestart) {
    foreach ($svc in $servicesToRestart) {
        try {
            Restart-Service $svc.Name -Force -ErrorAction Stop
            Write-Host "  [OK] Restarted service: $($svc.Name)" -ForegroundColor Green
        } catch {
            Write-Host "  [WARNING] Could not restart $($svc.Name): $_" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  [NOTE] No postgresql* Windows service found to restart." -ForegroundColor Gray
}

# 4. Show summary
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\.' -and $_.IPAddress -notmatch '^127\.' } | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   SERVER PC IS NOW 100% READY FOR CLIENT WORKSTATIONS!    " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Server Host IP : $localIP (or 192.168.1.32)" -ForegroundColor White
Write-Host " Port           : 5432" -ForegroundColor White
Write-Host " Database       : jayraldines_catering" -ForegroundColor White
Write-Host " DB User        : jayraldines_app" -ForegroundColor White
Write-Host " DB Password    : 12345678" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
