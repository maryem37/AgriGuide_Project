# AgriMent — Full Setup Guide (Mobile App)

This guide will take you from zero to a running app on your phone.

---

## What You Need

| Tool | Download | Version |
|---|---|---|
| Node.js | https://nodejs.org | 18+ |
| Python | https://python.org/downloads | 3.11+ |
| Git | https://git-scm.com | Any |
| Expo Go | App Store / Google Play | Latest |
| A phone + WiFi | Phone and computer on the same network | — |

---

## Step 1 — Install Python (with py launcher)

1. Download Python from https://python.org/downloads
2. Run the installer
3. **IMPORTANT: Check the box "Add python.exe to PATH"** at the bottom of the installer
4. Click "Install Now"
5. Restart your terminal / PowerShell

Verify it works:
```powershell
py --version
```
You should see something like `Python 3.13.x`

---

## Step 2 — Install Node.js

1. Download from https://nodejs.org
2. Run the installer (default settings are fine)
3. Restart your terminal / PowerShell

Verify it works:
```powershell
node --version
npm --version
```

---

## Step 3 — Clone the Repository

```powershell
git clone https://github.com/Azizzbarhoumi/Mobile-AgriMent.git
cd Mobile-AgriMent
```

---

## Step 4 — Find Your Computer's IP Address

Your phone and computer must be on the **same WiFi network**. You need your computer's local IP.

**Windows PowerShell:**
```powershell
ipconfig
```
Look for **"IPv4 Address"** under your WiFi adapter. It looks like `192.168.1.X` or `10.0.0.X`.

Write it down — you'll need it in the next steps.

---

## Step 5 — Setup the Backend (Python/FastAPI)

Open a **new terminal** and run:

```powershell
cd Mobile-AgriMent\backend
```

Install Python dependencies:
```powershell
py -m pip install -r requirements.txt
```

Start the backend server:
```powershell
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8080
INFO:     Started reloader process
```

**Leave this terminal open.** The backend must stay running.

---

## Step 6 — Setup the Frontend (React Native/Expo)

Open a **second terminal** and run:

```powershell
cd Mobile-AgriMent\frontend
```

### 6a. Install dependencies
```powershell
npm install
```

### 6b. Configure your IP address

**Create or edit the `.env` file** in the `frontend/` folder:

```powershell
echo EXPO_PUBLIC_API_HOST=YOUR_IP:8080 > .env
```

**Replace `YOUR_IP`** with the IP you found in Step 4.

For example, if your IP is `192.168.1.50`:
```powershell
echo EXPO_PUBLIC_API_HOST=192.168.1.50:8080 > .env
```

### 6c. Update app.json

Open `frontend/app.json` in any text editor. Find this line:
```json
"apiHost": "192.168.1.4:8080",
```
Change it to your IP:
```json
"apiHost": "192.168.1.50:8080",
```

### 6d. Start Expo

```powershell
npx expo start --lan
```

You should see a QR code in the terminal.

---

## Step 7 — Run on Your Phone

1. Install **Expo Go** from the App Store (iOS) or Google Play (Android)
2. Make sure your phone is connected to the **same WiFi** as your computer
3. Open your phone's camera and **scan the QR code** from the terminal
4. Expo Go opens and the app loads

If the QR code doesn't work, try:
```
Press "s" in the terminal to switch to Expo Go mode
```

---

## Quick Reference — All Commands

```powershell
# Terminal 1 — Backend
cd Mobile-AgriMent\backend
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8080

# Terminal 2 — Frontend
cd Mobile-AgriMent\frontend
npm install
npx expo start --lan
```

---

## Files You Must Change

Only **3 files** need your IP address. Everything else reads from these automatically.

| File | What to change |
|---|---|
| `frontend/.env` | `EXPO_PUBLIC_API_HOST=YOUR_IP:8080` |
| `frontend/app.json` | `"apiHost": "YOUR_IP:8080"` |
| `frontend/server.js` | `http://YOUR_IP:${EXPRESS_PORT}` (line 30, optional — only if you run the Express proxy) |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `py is not recognized` | Reinstall Python with "Add to PATH" checked |
| `pip is not recognized` | Use `py -m pip install ...` instead of `pip install` |
| `No module named uvicorn` | Run `py -m pip install -r requirements.txt` inside `backend/` |
| `npm is not recognized` | Install Node.js from nodejs.org |
| Phone can't connect | Make sure phone and computer are on the **same WiFi** |
| QR code doesn't open | Run `npx expo start --lan` (not just `npx expo start`) |
| `Port 8081 is being used` | Close old Expo terminals or run `npx expo start --lan --clear` |
| App shows "Network Error" | Check that `.env` has the correct IP and backend is running |
| Backend crashes on start | Check if port 8080 is already in use: close other terminals |

---

## How It Works

```
Phone (Expo Go)          Computer                Internet
     |                      |                        |
     |--- scan QR -------->|                        |
     |<-- app loads --------|                        |
     |                      |                        |
     |--- take photo ------>|                        |
     |                      |--- sends to AI model ->|
     |                      |<-- insect result ------|
     |<-- shows result -----|                        |
     |                      |                        |
     |--- saves detection ->| (backend :8080)        |
     |                      |--- stored in SQLite    |
```

The backend runs on your computer at `http://YOUR_IP:8080`. The phone app connects to it over WiFi to send photos and receive detection results.
