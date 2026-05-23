# Wierdaglow Full Suite - LAN Enabled

This build runs on your local network so other devices on the same LAN can open it in a browser.

## Default login
- Username: `admin`
- Password: `Admin@123`

Change that immediately.

## Run on Windows
1. Extract the zip.
2. Double-click `start.bat`.
3. On the main PC, the app runs on port `5000`.
4. On other devices on the same network, open:
   - `http://YOUR-PC-IP:5000`

Example:
- `http://192.168.0.50:5000`

The batch file prints the detected network URLs when it starts.

## Important for LAN access
If another device cannot connect, the problem is almost never Flask. It is usually one of these:
- Windows Firewall is blocking Python or port 5000
- The device is on a different network or guest Wi-Fi
- Your antivirus is blocking inbound traffic

### Windows Firewall fix
Allow Python on Private networks, or create an inbound rule for TCP port 5000.

## Manual run
```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py app.py
```

## Data file
The database is stored locally in `wierdaglow_full_suite.db`.
Back it up.

## Security warning
This is reachable by devices on your local network.
Do not expose it directly to the internet.
Do not keep the default admin password.
