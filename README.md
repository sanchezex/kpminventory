# TrackRight Inventory

TrackRight is a lightweight, offline desktop application for recording purchased
electronic assets and their subsequent location, company, handler, and condition
history. It uses Python's Tkinter interface and a local SQLite database; it does
not require an account, server, or network connection.

## Windows users

Do not open `trackright.py` on the target PC. Install TrackRight by running
`TrackRight-Setup-1.0.0.exe`; setup installs the bundled app and adds a desktop
shortcut named **TrackRight**. The installed application runs on 64-bit
Windows 10 and 11 and does not require Python, Tkinter, or an internet
connection.

The installer must first be built on a Windows machine. See **Build a Windows
installer** below. The build output is
`dist\installer\TrackRight-Setup-1.0.0.exe`.

## Run from source

```sh
python3 -m pip install -r requirements.txt
python3 trackright.py
```

## Build a Windows installer

Build the installer on Windows (the build creates a native Windows executable).
Install 64-bit Python 3.10 or later with Tcl/Tk enabled and Inno Setup 6, then
open PowerShell in the project folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

The script installs PyInstaller and the Excel/PNG export dependencies, bundles
the KPMTECH logo and export libraries, and creates two Windows executables:

- `dist\TrackRight.exe` is the standalone app.
- `dist\installer\TrackRight-Setup-1.0.0.exe` is the installer.

Run the installer on the target 64-bit Windows 10 or 11 PC. It installs
TrackRight to `%LOCALAPPDATA%\Programs\TrackRight\TrackRight.exe`, adds a Start
Menu entry, and creates a desktop shortcut with the KPMTECH app icon. The
installed app shows the KPMTECH logo in its branded header and does not need
Python, Tkinter, or network access at runtime. The installer
does not remove the local database when the app is uninstalled.

The database is created in the current user's application-data directory:

- Windows: `%LOCALAPPDATA%/TrackRight/trackright_data.db`
- macOS: `~/Library/Application Support/TrackRight/trackright_data.db`
- Linux: `$XDG_DATA_HOME/TrackRight/trackright_data.db`, or
  `~/.local/share/TrackRight/trackright_data.db`

## Workflow

1. Use **Purchase Intake** to create an asset. Select a model from the device
   catalog (JC270, KL100, SAFARICOM SIM, AIRTEL SIM, or MEM CARDS), enter its
   serial/asset tag and purchase date, and save it. The purchase also creates
   its first history event from the supplier to Samar.
2. Use **Movement & Transfer** to add each later transfer. The app derives the
   origin location from the latest saved event so history remains connected.
   Record the destination company and, when applicable, the vehicle
   registration where the device is installed.
3. Use **Inventory** to search the current inventory by asset tag, model,
   location, company, or condition, and filter by product, company, and current
   location. Select an asset to record a movement or open its history. Use
   **Download Excel** or **Download PNG** to save the matching inventory.
4. Use **History** to filter events by device/serial, product, company, and
   location. Use **Download filtered history (Excel)** or
   **Download filtered history (PNG)** to save the matching movement events.
   Leaving the filters set to their “All” options downloads the complete
   inventory or movement history, including initial purchase events.

Every movement is appended to history; earlier events are not overwritten.
Purchase and initial-history writes are committed together, as are movement and
current-status updates. Existing databases are upgraded automatically to store
vehicle registrations without discarding previous inventory or movement data.

## Backups and security

The database is stored on the computer, so protect it with your operating
system's account permissions and full-disk encryption. On POSIX systems, the
app restricts the database file to the current user. Make regular backups while
the app is closed, and keep at least one copy on a separate drive. The database
is not independently encrypted by this app.

## Tests

Run the tests with:

```sh
python3 -m unittest
```
