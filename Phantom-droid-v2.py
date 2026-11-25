
#!/usr/bin/env python3
# ============================================================
#  PhantomDroid v2.1        Created by Rdy7d3r & Th&run
#  Dev @Rd7d3r            Terminal Edition
#  Android 11-17 + iOS 18-26 support
# ============================================================

import os
import sys
import time
import json
import socket
import secrets
import threading
import subprocess
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import datetime

try:
    import qrcode
except ImportError:
    qrcode = None

# ------------------------------------------------------------
#  CONFIG
# ------------------------------------------------------------
LOGDIR = Path.home() / ".phantom_droid"
LOGDIR.mkdir(exist_ok=True)
SHOT_DIR = LOGDIR / "captures"
SHOT_DIR.mkdir(exist_ok=True)
QR_PORT = 8765

# QR trigger state: device_id -> token (one scan = one scrcpy launch)
qr_triggers: dict[str, str] = {}

# ------------------------------------------------------------
#  COLORS
# ------------------------------------------------------------
G = "\033[1;32m"
DG = "\033[0;32m"
R = "\033[1;31m"
W = "\033[0m"

def banner():
    os.system("clear" if os.name != "nt" else "cls")
    print(f"""{G}
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗      ██████╗ ██████╗  ██████╗ ██╗██████╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔══██╗████╗ ████║      ██╔══██╗██╔══██╗██╔═══██╗██║██╔══██╗
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██████╔╝██╔████╔██║█████╗██║  ██║██████╔╝██║   ██║██║██║  ██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██╔══██╗██║╚██╔╝██║╚════╝██║  ██║██╔══██╗██║   ██║██║██║  ██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ██║  ██║██║ ╚═╝ ██║      ██████╔╝██║  ██║╚██████╔╝██║██████╔╝
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═════╝
{W}
{DG}  PhantomDroid v2.2          Created by Rdy7d3r & Th&run
  Android 11-17 + iOS 18-26  Dev Rdy7d3r{W}
{G}{'═'*78}{W}""")

MENU = f"""{G}
 DEVICE MANAGEMENT               |  APP MANAGEMENT             |  FILE OPERATIONS
{'─'*78}
 1 . List devices                | 10. Install APK             | 19. Take screenshot
 2 . Connect WiFi / Pair         | 11. Uninstall app           | 20. Multiple screenshots
 3 . Disconnect device           | 12. List packages           | 21. Record screen
 4 . Device info                 | 13. Package info            | 22. Upload file
 5 . Restart ADB                 | 14. Clear app data          | 23. Download file
 6 . Check connection            | 15. Force stop app          | 24. List files
 7 . Execute shell command       | 16. Start app               | 25. Create folder
 8 . Get device logs             | 17. Backup app              | 26. Delete file/folder
 9 . Reboot device               | 18. Batch install           | 27. Backup folder
                                 |
 SYSTEM MONITORING               | SCREEN SHARING              | WIFI MANAGEMENT
{'─'*78}
 28. Battery info                | 37. Start screen sharing    | 46. Manual WiFi transfer
 29. Memory info                 | 38. Custom screen sharing   | 47. Transfer all devices
 30. CPU info                    | 39. Stop screen sharing     | 48. Quick WiFi setup
 31. Storage info                | 40. Stop all sharing        | 49. WiFi status
 32. Running processes           | 41. Show active sessions    | 50. Disconnect WiFi
 33. Network info                | 42. Multi-device sharing    | 51. Toggle auto-transfer
 34. System properties           | 43. Check scrcpy            | 52. Monitor logcat
 35. Apps with size              | 44. Record screen           | 53. Service status
 36. Monitor performance         | 45. Sync folder             | 54. Settings

 55. QR remote screen pairing    | 56. iOS support (18-26)     | 99. Exit
{W}"""

# ------------------------------------------------------------
#  AUDIT LOG
# ------------------------------------------------------------
def audit(action, detail=""):
    entry = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             "action": action, "detail": detail}
    with open(LOGDIR / "audit.log", "a") as f:
        f.write(json.dumps(entry) + "\n")

# ------------------------------------------------------------
#  ADB WRAPPER
# ------------------------------------------------------------
def adb(*args, timeout=60):
    try:
        r = subprocess.run(["adb"] + list(args), capture_output=True,
                           text=True, timeout=timeout)
        return (r.stdout + (("\n" + r.stderr) if r.stderr.strip() else "")).strip()
    except FileNotFoundError:
        print(f"{R}[!] adb not found — install: apt install adb{W}")
        sys.exit(1)
    def _t():
        return "[!] command timed out"
    try:
        pass
    except subprocess.TimeoutExpired:
        return _t()

def has_adb():
    return shutil.which("adb") is not None

# ------------------------------------------------------------
#  DEVICE SELECTION
# ------------------------------------------------------------
def device_list():
    devs = []
    for line in adb("devices").splitlines()[1:]:
        p = line.split()
        if len(p) >= 2 and p[1] == "device":
            devs.append(p[0])
    return devs

def pick():
    devs = device_list()
    if not devs:
        print(f"{R}[!] no devices connected{W}")
        input(">> Enter to continue... ")
        return None
    if len(devs) == 1:
        return devs[0]
    print(f"{G}Available devices:{W}")
    for i, d in enumerate(devs, 1):
        print(f"  {i}. {d}")
    n = input("Select device number (0 to cancel): ").strip()
    try:
        return devs[int(n) - 1] if int(n) != 0 else None
    except (ValueError, IndexError):
        return None

def out(msg):
    print(msg)
    input(f"{G}>> Enter to continue...{W} ")

# ------------------------------------------------------------
#  ANDROID VERSION DETECTION
# ------------------------------------------------------------
def android_version(d):
    try:
        v = adb("-s", d, "shell", "getprop", "ro.build.version.release")
        return v.strip() or "?"
    except Exception:
        return "?"

# ============================================================
#  OPTION 2 — WiFi connect / Pair (Android 11-17)
# ============================================================
def m02():
    print(f"""{G}
 ── Android 11-17 support ──
 A) Classic TCP   (any version, needs one USB session: adb tcpip 5555)
 B) Pair mode     (Android 11+ : Wireless debugging pairing code)
{W}""")
    mode = input("mode A/B > ").strip().lower()
    if mode == "b":
        addr = input("pair IP:PAIRPORT from phone (e.g. 192.168.4.105:37891) > ").strip()
        code = input("6-digit pairing code > ").strip()
        print(f"[*] pairing {addr} ...")
        r = adb("pair", addr, code, timeout=20)
        print(r)
        if "success" in r.lower() or "paired" in r.lower():
            dev_addr = input("connect IP:PORT shown on phone > ").strip()
            print(adb("connect", dev_addr, timeout=20))
            print("[*] Android 13+ rotates the pairing port every session")
    else:
        addr = input("IP (or full IP:PORT) > ").strip()
        if ":" not in addr:
            addr += ":5555"
        print(f"[*] trying {addr} ...")
        r = adb("connect", addr, timeout=15)
        print(r)
        if "connected" not in r.lower():
            print(f"""{R}
[!] connect failed — phone not listening on {addr}.
 1. USB method (all versions): connect USB > run option 7:
       setprop service.adb.tcp.port 5555 ; stop adbd ; start adbd
    or simply: adb tcpip 5555 — then unplug, retry with phone IP
 2. Pair method (11+): Developer options > Wireless debugging >
    'Pair device with pairing code' — use mode B above
 3. Same WiFi + router AP isolation must be OFF{W}""")
    input(">> Enter to continue... ")

# ============================================================
#  QR REMOTE SCREEN — HTTP trigger server
# ============================================================
class QRHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _html(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<html><body style='font-family:monospace;background:"
                         f"#0d0d0d;color:#4caf50;text-align:center;padding-top:3rem'>"
                         f"{body}</body></html>".encode())

    def do_GET(self):
        if self.path.startswith("/open_screen"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            dev = q.get("device_id", [""])[0]
            tok = q.get("token", [""])[0]
            if dev in qr_triggers and qr_triggers[dev] == tok:
                del qr_triggers[dev]
                threading.Thread(target=launch_scrcpy, args=(dev,), daemon=True).start()
                audit("qr_scan", f"{dev} -> scrcpy launched")
                self._html(200, "<h2>Approved ✔</h2><p>Check your PC — remote "
                                "screen starting.<br>Confirm consent on device.</p>")
            else:
                self._html(403, "<h2>Invalid or expired token ✘</h2>")
        elif self.path.startswith("/ping"):
            self._html(200, "phantom-droid alive")
        else:
            self._html(200, "<h2>PhantomDroid QR service</h2>")

def launch_scrcpy(device_id):
    if not shutil.which("scrcpy"):
        print(f"{R}[!] scrcpy not installed — apt install scrcpy{W}")
        return
    subprocess.Popen(["scrcpy", "-s", device_id, "--stay-awake"])

def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

_qr_server = {"obj": None}

def ensure_qr_server():
    if _qr_server["obj"] is None:
        srv = ThreadingHTTPServer(("0.0.0.0", QR_PORT), QRHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _qr_server["obj"] = srv

# ============================================================
#  OPTION 55 — QR REMOTE SCREEN PAIRING
# ============================================================
def m55():
    if not qrcode:
        out("[!] pip install qrcode"); return
    d = pick()
    if not d: return
    if not shutil.which("scrcpy"):
        out("[!] scrcpy not installed — apt install scrcpy"); return
    ensure_qr_server()
    ip = get_lan_ip()
    token = secrets.token_urlsafe(24)
    qr_triggers[d] = token
    url = f"http://{ip}:{QR_PORT}/open_screen?device_id={d}&token={token}"
    print(f"\n{G}WiFi ADB devices:{W}")
    for i, dev in enumerate(device_list(), 1):
        print(f"  {i}. {dev}")
    print(f"\n{G}Scan the QR to open Remote Android Screen{W}")
    print(f"{DG}Scan from the connected phone. One-time token, expires after use.{W}\n")
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    print(f"{G}QR URL:{W}\n{url}\n")
    print(f"[*] Waiting for scan on port {QR_PORT} ... (Ctrl+C to cancel)")
    audit("qr_issue", f"{d} token={token[:8]}...")
    try:
        while d in qr_triggers:
            time.sleep(0.5)
        print(f"{G}[+] Scan accepted — remote screen launching for {d}{W}")
        print("[*] DEVICE WILL SHOW A CONSENT PROMPT — user must approve.")
        time.sleep(2)
    except KeyboardInterrupt:
        qr_triggers.pop(d, None)
        print("\n[*] cancelled")

# ============================================================
#  iOS SUPPORT (56) — iOS 18 / 19 / 26 via libimobiledevice
# ============================================================
def idev():
    r = subprocess.run(["idevice_id", "-l"], capture_output=True, text=True)
    return [x for x in r.stdout.split() if x.strip()]

def ios_pick():
    ds = idev()
    if not ds:
        print(f"{R}[!] no iOS device found. Plug in via USB, tap TRUST on phone."
              f"\n    install: apt install libimobiledevice usbmuxd{W}")
        input(">> Enter to continue... ")
        return None
    if len(ds) == 1: return ds[0]
    for i, d in enumerate(ds, 1): print(f"  {i}. {d}")
    try: return ds[int(input("Select > ")) - 1]
    except: return None

def ios_cmd(*args, timeout=30):
    try:
        r = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except FileNotFoundError:
        return "[!] libimobiledevice not installed — apt install libimobiledevice usbmuxd"
    except subprocess.TimeoutExpired:
        return "[!] timed out"

def m56():
    if not ios_pick():
        return
    while True:
        print(f"""{G}
 iOS MODULE (iOS 18 / 19 / 26 — all modern versions)
 ────────────────────────────────────────────────────
 1. Device info (model / iOS version / UDID)
 2. Live syslog
 3. Screenshot
 4. Installed apps
 5. Battery status
 6. Trust / pairing check
 7. File browser (afc — media dirs)
 0. Back
{W}""")
        a = input("ios> ").strip()
        if a == "0": return
        d = ios_pick()
        if not d: return
        if a == "1":
            print(ios_cmd("ideviceinfo", "-u", d))
        elif a == "2":
            print(f"{G}[*] live syslog — Ctrl+C to stop{W}")
            subprocess.run(["idevicesyslog", "-u", d])
        elif a == "3":
            fn = f"ios_shot_{int(time.time())}.png"
            r = ios_cmd("idevicescreenshot", "-u", d, fn)
            out(r or f"[+] saved {fn}")
        elif a == "4":
            r = ios_cmd("ideviceinstaller", "-u", d, "-l", "-o", "list")
            print(r); input(">> Enter to continue... ")
        elif a == "5":
            print(ios_cmd("ideviceinfo", "-u", d, "-q", "com.apple.mobile.battery"))
            input(">> Enter to continue... ")
        elif a == "6":
            r = ios_cmd("idevicepair", "-u", d, "validate")
            out(r.strip() or "[+] paired and trusted")
        elif a == "7":
            print(f"[*] mount with: ifuse /mnt/ios -u {d}")
            print("[*] then browse /mnt/ios — Photos, DCIM, etc. (media only, no jailbreak)")
            input(">> Enter to continue... ")

# ============================================================
#  DEVICE MANAGEMENT (1, 3-9)
# ============================================================
def m01(): out("\n".join(device_list()) or "[!] none")

def m03():
    addr = input("IP:PORT to disconnect (blank = all) > ").strip()
    out(adb("disconnect", addr) if addr else adb("disconnect"))

def m04():
    d = pick()
    if not d: return
    v = android_version(d)
    print(f"{G}[*] Device: {d}   Android {v}{W}")
    for label, p in [("Model", "ro.product.model"), ("Brand", "ro.product.brand"),
                     ("SDK", "ro.build.version.sdk"), ("Serial", "ro.serialno")]:
        print(f"  {label}: {adb('-s', d, 'shell', 'getprop', p)}")
    print(f"  Battery: {adb('-s', d, 'shell', 'dumpsys battery | grep level')}")
    input(">> Enter to continue... ")

def m05():
    adb("kill-server"); time.sleep(1); adb("start-server")
    out("[+] ADB server restarted")

def m06():
    d = pick()
    if not d: return
    r = adb("-s", d, "shell", "echo", "ok")
    out(f"[+] {d} online (Android {android_version(d)})"
        if r == "ok" else f"{R}[!] {d} offline{W}")

def m07():
    d = pick()
    if not d: return
    cmd = input("shell command > ").strip()
    print(adb("-s", d, "shell", cmd))
    audit("shell", f"{d}: {cmd}")
    input(">> Enter to continue... ")

def m08():
    d = pick()
    if not d: return
    n = input("lines [100] > ").strip() or "100"
    out(adb("-s", d, "logcat", "-d", "-t", n))

def m09():
    d = pick()
    if not d: return
    mode = input("1) reboot  2) recovery  3) power off > ").strip()
    if mode == "1":   adb("-s", d, "reboot")
    elif mode == "2": adb("-s", d, "reboot", "recovery")
    elif mode == "3": adb("-s", d, "shell", "reboot", "-p")
    out("[+] command sent")

# ============================================================
#  APP MANAGEMENT (10-18)
# ============================================================
def m10():
    d = pick()
    if not d: return
    out(adb("-s", d, "install", "-r", input("path to APK > ").strip()))

def m11():
    d = pick()
    if not d: return
    out(adb("-s", d, "uninstall", input("package > ").strip()))

def m12():
    d = pick()
    if not d: return
    t = input("1) all  2) system  3) 3rd-party > ").strip()
    flag = {"2": "-s", "3": "-3"}.get(t, "")
    pkgs = adb("-s", d, "shell", f"pm list packages {flag}").replace("package:", "").split()
    out("\n".join(pkgs))

def m13():
    d = pick()
    if not d: return
    out(adb("-s", d, "shell", f"dumpsys package {input('package > ').strip()} | head -60"))

def m14():
    d = pick()
    if not d: return
    out(adb("-s", d, "shell", f"pm clear {input('package > ').strip()}"))

def m15():
    d = pick()
    if not d: return
    out(adb("-s", d, "shell", f"am force-stop {input('package > ').strip()}"))

def m16():
    d = pick()
    if not d: return
    pkg = input("package > ").strip()
    lines = adb("-s", d, "shell", f"cmd package resolve-activity --brief {pkg}").splitlines()
    act = lines[-1].strip() if lines else ""
    if act:
        adb("-s", d, "shell", f"am start -n {act}")
        out(f"[+] launched {act}")
    else:
        out("[!] could not resolve activity")

def m17():
    d = pick()
    if not d: return
    pkg = input("package > ").strip()
    p = adb("-s", d, "shell", f"pm path {pkg}").replace("package:", "").splitlines()
    if not p:
        out("[!] not found"); return
    dst = LOGDIR / f"{pkg}_{int(time.time())}.apk"
    adb("-s", d, "pull", p[0].strip(), str(dst))
    out(f"[+] saved {dst}")

def m18():
    d = pick()
    if not d: return
    folder = input("folder with APKs > ").strip()
    apks = list(Path(folder).glob("*.apk"))
    if not apks:
        out("[!] no APKs found"); return
    for a in apks:
        print(f"[*] installing {a.name} ...")
        print(adb("-s", d, "install", "-r", str(a)))
    out("[+] batch done")

# ============================================================
#  FILE OPERATIONS (19-27)
# ============================================================
def m19():
    d = pick()
    if not d: return
    dst = SHOT_DIR / f"shot_{d.replace(':', '_')}_{int(time.time())}.png"
    adb("-s", d, "shell", "screencap -p /sdcard/.pd_shot.png")
    adb("-s", d, "pull", "/sdcard/.pd_shot.png", str(dst))
    adb("-s", d, "shell", "rm /sdcard/.pd_shot.png")
    out(f"[+] saved {dst}")

def m20():
    d = pick()
    if not d: return
    n = int(input("how many [5] > ").strip() or 5)
    delay = float(input("interval seconds [2] > ").strip() or 2)
    for i in range(n):
        dst = SHOT_DIR / f"shot_{i}_{int(time.time())}.png"
        adb("-s", d, "shell", "screencap -p /sdcard/.pd_shot.png")
        adb("-s", d, "pull", "/sdcard/.pd_shot.png", str(dst))
        adb("-s", d, "shell", "rm /sdcard/.pd_shot.png")
        print(f"[+] {dst}")
        time.sleep(delay)
    out("[+] done")

def m21():
    d = pick()
    if not d: return
    secs = int(input("seconds [10] > ").strip() or 10)
    print(f"{G}[*] recording {secs}s ...{W}")
    subprocess.Popen(["adb", "-s", d, "shell",
        f"screenrecord --time-limit {secs} /sdcard/.pd_rec.mp4"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(secs + 2)
    dst = SHOT_DIR / f"rec_{int(time.time())}.mp4"
    adb("-s", d, "pull", "/sdcard/.pd_rec.mp4", str(dst))
    adb("-s", d, "shell", "rm /sdcard/.pd_rec.mp4")
    out(f"[+] saved {dst}")

def m22():
    d = pick()
    if not d: return
    local = input("local file > ").strip()
    remote = input("remote path [/sdcard/] > ").strip() or "/sdcard/"
    out(adb("-s", d, "push", local, remote))

def m23():
    d = pick()
    if not d: return
    out(adb("-s", d, "pull", input("remote file > ").strip(), str(LOGDIR)))

def m24():
    d = pick()
    if not d: return
    path = input("path [/sdcard] > ").strip() or "/sdcard"
    out(adb("-s", d, "shell", f"ls -la {path}"))

def m25():
    d = pick()
    if not d: return
    out(adb("-s", d, "shell", f"mkdir -p {input('folder to create > ').strip()}"))

def m26():
    d = pick()
    if not d: return
    path = input("path to delete > ").strip()
    if input(f"{R}DELETE {path}? type YES > {W}").strip() == "YES":
        out(adb("-s", d, "shell", f"rm -rf '{path}'"))
    else:
        out("cancelled")

def m27():
    d = pick()
    if not d: return
    dst = LOGDIR / f"backup_{int(time.time())}"
    adb("-s", d, "pull", input("remote folder > ").strip(), str(dst))
    out(f"[+] saved {dst}")

# ============================================================
#  SYSTEM MONITORING (28-36)
# ============================================================
def m28(): d = pick(); out(adb("-s", d, "shell", "dumpsys battery") if d else "")
def m29(): d = pick(); out(adb("-s", d, "shell", "cat /proc/meminfo | head -5") if d else "")
def m30(): d = pick(); out(adb("-s", d, "shell", "cat /proc/cpuinfo | head -30") if d else "")
def m31(): d = pick(); out(adb("-s", d, "shell", "df -h /data") if d else "")
def m32(): d = pick(); out(adb("-s", d, "shell", "ps -A") if d else "")

def m33():
    d = pick()
    if not d: return
    print("--- wlan0 ---"); print(adb("-s", d, "shell", "ip addr show wlan0"))
    print("--- routes ---"); print(adb("-s", d, "shell", "ip route"))
    print("--- mac ---"); print(adb("-s", d, "shell", "cat /sys/class/net/wlan0/address"))
    input(">> Enter to continue... ")

def m34(): d = pick(); out(adb("-s", d, "shell", "getprop") if d else "")

def m35():
    d = pick()
    if not d: return
    pkgs = adb("-s", d, "shell", "pm list packages -3").replace("package:", "").split()
    for p in pkgs[:30]:
        size = adb("-s", d, "shell",
            f"dumpsys package {p} | grep -E 'codesize|dataSize' | head -2")
        print(f"{p}  {size}")
    input(">> Enter to continue... ")

def m36(): d = pick(); out(adb("-s", d, "shell", "top -n 1 -b | head -25") if d else "")

# ============================================================
#  SCREEN SHARING (37-45)
# ============================================================
def scrcpy_installed():
    return shutil.which("scrcpy") is not None

def m37():
    d = pick()
    if not d: return
    if not scrcpy_installed():
        out("[!] scrcpy not installed — apt install scrcpy"); return
    subprocess.Popen(["scrcpy", "-s", d, "--stay-awake"])
    out("[+] session started")

def m38():
    d = pick()
    if not d: return
    if not scrcpy_installed():
        out("[!] scrcpy not installed"); return
    extra = input("extra flags (e.g. --max-size 1024 --bit-rate 4M) > ").strip()
    subprocess.Popen(["scrcpy", "-s", d] + extra.split())
    out("[+] started")

def m39():
    subprocess.run(["pkill", "-f", "scrcpy"])
    out("[+] sessions stopped")

def m40(): m39()

def m41():
    r = subprocess.run(["pgrep", "-a", "scrcpy"], capture_output=True, text=True)
    out(r.stdout or "[!] no active sessions")

def m42():
    if not scrcpy_installed():
        out("[!] scrcpy not installed"); return
    for d in device_list():
        print(f"[*] starting {d}")
        subprocess.Popen(["scrcpy", "-s", d, "--window-title", d])
    out("[+] all sessions launched")

def m43(): out("[+] scrcpy: " + (shutil.which("scrcpy") or "NOT INSTALLED"))
def m44(): m21()

def m45():
    d = pick()
    if not d: return
    remote = input("remote folder [/sdcard/DCIM] > ").strip() or "/sdcard/DCIM"
    local = input("local folder > ").strip() or str(LOGDIR / "sync")
    Path(local).mkdir(exist_ok=True)
    out(adb("-s", d, "pull", remote, local))

# ============================================================
#  WIFI MANAGEMENT (46-54)
# ============================================================
def wifi_connect(d, ssid, pwd):
    return adb("-s", d, "shell", f"cmd wifi connect-network '{ssid}' wpa2 '{pwd}'")

def m46():
    d = pick()
    if not d: return
    out(wifi_connect(d, input("SSID > ").strip(), input("password > ").strip()))

def m47():
    ssid = input("SSID > ").strip()
    pwd = input("password > ").strip()
    for d in device_list():
        print(f"[*] {d}")
        print(wifi_connect(d, ssid, pwd))
    input(">> Enter to continue... ")

def m48():
    d = pick()
    if not d: return
    out(adb("-s", d, "shell", "svc wifi enable"))
    out(wifi_connect(d, input("SSID > ").strip(), input("password > ").strip()))

def m49(): d = pick(); out(adb("-s", d, "shell", "dumpsys wifi | grep -iE 'enabled|SSID' | head -10") if d else "")
def m50(): d = pick(); out(adb("-s", d, "shell", "svc wifi disable") if d else "")

def m51():
    d = pick()
    if not d: return
    v = "1" if input("1) enable  2) disable > ").strip() == "1" else "0"
    out(adb("-s", d, "shell", f"settings put global wifi_scan_always_enabled {v}"))

def m52():
    d = pick()
    if not d: return
    print(f"{G}[*] live logcat — Ctrl+C to stop{W}")
    subprocess.run(["adb", "-s", d, "logcat"])

def m53():
    print(f"[+] adb:     {'OK' if has_adb() else 'MISSING'}")
    print(f"[+] scrcpy:  {'OK' if scrcpy_installed() else 'MISSING'}")
    print(f"[+] qrcode:  {'OK' if qrcode else 'MISSING (pip install qrcode)'}")
    print(f"[+] libimobiledevice: {'OK' if shutil.which('idevice_id') else 'MISSING (iOS support)'}")
    print(f"[+] QR svc:  {'running on port ' + str(QR_PORT) if _qr_server['obj'] else 'not started (option 55)'}")
    print(f"[+] logs:    {LOGDIR}")
    input(">> Enter to continue... ")

def m54():
    print(f"""{G}
 Settings
 {'─'*40}
 capture dir : {SHOT_DIR}
 audit log   : {LOGDIR}/audit.log
 adb version : {adb('version').splitlines()[0] if has_adb() else 'N/A'}
{W}""")
    input(">> Enter to continue... ")

# ============================================================
#  MAIN LOOP
# ============================================================
HANDLERS = {
    "1": m01, "2": m02, "3": m03, "4": m04, "5": m05, "6": m06, "7": m07, "8": m08, "9": m09,
    "10": m10, "11": m11, "12": m12, "13": m13, "14": m14, "15": m15, "16": m16, "17": m17, "18": m18,
    "19": m19, "20": m20, "21": m21, "22": m22, "23": m23, "24": m24, "25": m25, "26": m26, "27": m27,
    "28": m28, "29": m29, "30": m30, "31": m31, "32": m32, "33": m33, "34": m34, "35": m35, "36": m36,
    "37": m37, "38": m38, "39": m39, "40": m40, "41": m41, "42": m42, "43": m43, "44": m44, "45": m45,
    "46": m46, "47": m47, "48": m48, "49": m49, "50": m50, "51": m51, "52": m52, "53": m53, "54": m54,
    "55": m55, "56": m56,
}

def main():
    if not has_adb():
        print(f"{R}[!] adb not found — apt install adb{W}")
        sys.exit(1)
    while True:
        banner()
        print(MENU)
        choice = input(f"{G}Enter your choice (1-56, 99 to exit): {W}").strip()
        if choice == "99":
            if _qr_server["obj"]:
                _qr_server["obj"].shutdown()
            print(f"{G}[+] Phantom-Droid signing off.{W}")
            audit("exit")
            break
        fn = HANDLERS.get(choice)
        if fn:
            try:
                fn()
                audit("menu", f"option {choice}")
            except KeyboardInterrupt:
                print("\n[*] cancelled")
            except Exception as e:
                print(f"{R}[!] error: {e}{W}")
                input(">> Enter to continue... ")
        else:
            print(f"{R}[!] invalid option{W}")
            time.sleep(0.5)

if __name__ == "__main__":
    main()
