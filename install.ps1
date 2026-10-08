<#
.SYNOPSIS
    Installs WinKeySymb Special Character Picker on Windows.
#>

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Installing WinKeySymb Character Picker... " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$CurrentDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Look for WinKeySymb.exe in current dir (release zip) or in dist\ (source repo)
$SourceExe = $null
if (Test-Path (Join-Path $CurrentDir "WinKeySymb.exe")) {
    $SourceExe = Join-Path $CurrentDir "WinKeySymb.exe"
} elseif (Test-Path (Join-Path $CurrentDir "dist\WinKeySymb.exe")) {
    $SourceExe = Join-Path $CurrentDir "dist\WinKeySymb.exe"
} else {
    Write-Host "[*] Executable not found locally. Attempting build with uv..." -ForegroundColor Yellow
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv run python "$CurrentDir\build.py"
        if (Test-Path (Join-Path $CurrentDir "dist\WinKeySymb.exe")) {
            $SourceExe = Join-Path $CurrentDir "dist\WinKeySymb.exe"
        }
    }
}

if (-not $SourceExe -or -not (Test-Path $SourceExe)) {
    Write-Error "Could not find WinKeySymb.exe. Please download it from GitHub Releases or run 'uv run python build.py'."
    exit 1
}

# Terminate any running instances of WinKeySymb
Write-Host "[*] Stopping any running WinKeySymb processes..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -match "winkeysymb" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 1000

# Target Install Directory: %LOCALAPPDATA%\Programs\WinKeySymb
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\WinKeySymb"
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$TargetExe = Join-Path $InstallDir "WinKeySymb.exe"

# Copy fresh executable
Write-Host "[*] Copying binary to: $TargetExe" -ForegroundColor Green
Copy-Item -Path $SourceExe -Destination $TargetExe -Force

# Create Start Menu Shortcut
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$StartShortcut = Join-Path $StartMenuDir "WinKeySymb.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($StartShortcut)
$Shortcut.TargetPath = $TargetExe
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description = "WinKeySymb - Fast Special Character Picker (Win+Alt+C)"
$Shortcut.Save()
Write-Host "[*] Start Menu shortcut created: $StartShortcut" -ForegroundColor Green

# Create Desktop Shortcut
$DesktopDir = [Environment]::GetFolderPath("Desktop")
$DesktopShortcut = Join-Path $DesktopDir "WinKeySymb.lnk"
$ShortcutDesk = $WshShell.CreateShortcut($DesktopShortcut)
$ShortcutDesk.TargetPath = $TargetExe
$ShortcutDesk.WorkingDirectory = $InstallDir
$ShortcutDesk.Description = "WinKeySymb - Fast Special Character Picker (Win+Alt+C)"
$ShortcutDesk.Save()
Write-Host "[*] Desktop shortcut created: $DesktopShortcut" -ForegroundColor Green

# Create Uninstaller script in install directory
$UninstallScript = Join-Path $InstallDir "uninstall.ps1"
@"
Write-Host "Uninstalling WinKeySymb..." -ForegroundColor Yellow
Get-Process | Where-Object { `$_.ProcessName -match "winkeysymb" } | Stop-Process -Force -ErrorAction SilentlyContinue
`$StartShortcut = Join-Path `$env:APPDATA "Microsoft\Windows\Start Menu\Programs\WinKeySymb.lnk"
if (Test-Path `$StartShortcut) { Remove-Item `$StartShortcut -Force }
`$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "WinKeySymb.lnk"
if (Test-Path `$DesktopShortcut) { Remove-Item `$DesktopShortcut -Force }
`$StartupShortcut = Join-Path `$env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\WinKeySymb.lnk"
if (Test-Path `$StartupShortcut) { Remove-Item `$StartupShortcut -Force }
`$InstallDir = Join-Path `$env:LOCALAPPDATA "Programs\WinKeySymb"
if (Test-Path `$InstallDir) { Remove-Item -Path `$InstallDir -Recurse -Force -ErrorAction SilentlyContinue }
Write-Host "WinKeySymb has been uninstalled." -ForegroundColor Green
"@ | Out-File -FilePath $UninstallScript -Encoding utf8

# Launch newly installed WinKeySymb
Write-Host "`n[*] Starting WinKeySymb..." -ForegroundColor Cyan
Start-Process -FilePath $TargetExe

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " Installation Complete! " -ForegroundColor Green
Write-Host " - Global Hotkey: Win + Alt + C" -ForegroundColor White
Write-Host " - Alternative Hotkeys: Tray icon menu -> Hotkey options" -ForegroundColor White
Write-Host " - Type e.g.: alpha, approx, ->, euro, 1/2, star, inf..." -ForegroundColor White
Write-Host " - Hit Enter or Click any character to insert it!" -ForegroundColor White
Write-Host "============================================================`n" -ForegroundColor Green
