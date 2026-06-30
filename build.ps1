<#
.SYNOPSIS
    Builds the Mail Lead Gen Controller into a standalone Windows executable.
.DESCRIPTION
    This script installs necessary Python dependencies including PyInstaller,
    then packages controller.py (along with search.py and extract_emails.py)
    into a single standalone .exe file inside the \dist\ directory.
    This allows the program to be copied and run on another computer without
    requiring Python to be installed.
#>

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  Building Mail Lead Gen Controller" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Cyan
} catch {
    Write-Host "[-] Python is not installed or not in PATH. Please install Python first." -ForegroundColor Red
    exit 1
}

Write-Host "`n[*] Installing required dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install pyinstaller duckduckgo-search requests beautifulsoup4

if ($LASTEXITCODE -ne 0) {
    Write-Host "[-] Failed to install dependencies." -ForegroundColor Red
    exit 1
}

Write-Host "`n[*] Compiling into a standalone executable using PyInstaller..." -ForegroundColor Yellow
# Use --onefile to generate a single .exe
# Use --clean to clear PyInstaller cache and remove temporary files before building
python -m PyInstaller --onefile --clean --icon=app_icon.ico --name MailLeadGen controller.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "[-] PyInstaller build failed." -ForegroundColor Red
    exit 1
}

Write-Host "`n[+] Build completed successfully!" -ForegroundColor Green
Write-Host "[+] Your standalone executable is located at: .\dist\MailLeadGen.exe" -ForegroundColor Green
Write-Host "[+] You can copy MailLeadGen.exe to any Windows computer and run it without installing Python." -ForegroundColor Cyan

Write-Host "`nPress any key to exit..."
$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null
