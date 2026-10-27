$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectRoot

try {
    if (-not $IsWindows -and $env:OS -ne "Windows_NT") {
        throw "Run this build script on Windows. It cannot produce a native Windows installer on Linux or macOS."
    }

    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonLauncher) {
        $pythonCommand = "py"
        $pythonArguments = @("-3")
    } else {
        $pythonLauncher = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonLauncher) {
            throw "Python 3 was not found. Install Python 3 with Tcl/Tk and add it to PATH."
        }
        $pythonCommand = $pythonLauncher.Source
        $pythonArguments = @()
    }

    & $pythonCommand @pythonArguments -c "import tkinter, sqlite3; print('Tkinter and SQLite are available.')"
    if ($LASTEXITCODE -ne 0) {
        throw "The selected Python installation is missing Tkinter or SQLite. Install Python for Windows with Tcl/Tk enabled."
    }

    & $pythonCommand @pythonArguments -c "import struct, sys; sys.exit('Python 3.10 or newer is required.') if sys.version_info < (3, 10) else None; sys.exit('Use 64-bit Python to build the Windows app.') if struct.calcsize('P') != 8 else print('Python 3.10+ (64-bit) selected.')"
    if ($LASTEXITCODE -ne 0) {
        throw "Use Python 3.10 or newer, 64-bit, with Tcl/Tk enabled to build the Windows app."
    }

    & $pythonCommand @pythonArguments -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install the PyInstaller and application dependencies."
    }
    if (-not (Test-Path "assets\trackright_logo.png") -or
        -not (Test-Path "assets\trackright.ico")) {
        throw "The KPMTECH logo or application icon is missing from the assets folder."
    }

    & $pythonCommand @pythonArguments -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name TrackRight `
        --add-data "assets\trackright_logo.png;assets" `
        --icon "assets\trackright.ico" `
        --collect-all openpyxl `
        --collect-all PIL `
        trackright.py
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed to build TrackRight.exe."
    }
    if (-not (Test-Path "dist\TrackRight.exe")) {
        throw "PyInstaller completed without producing dist\TrackRight.exe."
    }

    $innoCompiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($innoCompiler) {
        $innoPath = $innoCompiler.Source
    } else {
        $innoCandidates = @()
        $programFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
        $programFiles = [Environment]::GetFolderPath("ProgramFiles")
        if ($programFilesX86) {
            $innoCandidates += Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe"
        }
        if ($programFiles) {
            $innoCandidates += Join-Path $programFiles "Inno Setup 6\ISCC.exe"
        }
        $innoPath = $innoCandidates |
            Where-Object { Test-Path $_ } |
            Select-Object -First 1
    }

    if (-not $innoPath -or -not (Test-Path $innoPath)) {
        throw "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isinfo.php and run this script again."
    }

    & $innoPath "/DAppVersion=1.0.0" "trackright.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed to create the installer."
    }
    $installerPath = "dist\installer\TrackRight-Setup-1.0.0.exe"
    if (-not (Test-Path $installerPath)) {
        throw "Inno Setup completed without producing $installerPath."
    }

    Write-Host ""
    Write-Host "Build complete."
    Write-Host "Standalone app: dist\TrackRight.exe"
    Write-Host "Installer: $installerPath"
} finally {
    Pop-Location
}
