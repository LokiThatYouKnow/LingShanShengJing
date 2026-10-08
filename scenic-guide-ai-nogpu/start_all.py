"""一键启动所有服务（后端 + 两个前端）"""
import subprocess
import sys
import os
import time

os.chdir(r"d:\TALKING\scenic-guide-ai")

services = [
    {
        "name": "Backend (FastAPI)",
        "args": f'"{sys.executable}" "backend\\main.py"',
        "cwd": os.path.abspath("backend"),
        "wait": 3,
    },
    {
        "name": "Web Kiosk (Vite)",
        "args": 'cmd /c "npm run dev"',
        "cwd": os.path.abspath("web-kiosk"),
        "wait": 5,
    },
    {
        "name": "Web Admin (Vite)",
        "args": 'cmd /c "npm run dev"',
        "cwd": os.path.abspath("web-admin"),
        "wait": 5,
    },
]

procs = []
for svc in services:
    print(f"[LAUNCH] {svc['name']} ...")
    p = subprocess.Popen(
        svc["args"],
        cwd=svc["cwd"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True,
    )
    procs.append((svc["name"], p))
    time.sleep(svc["wait"])

print("\n=== Service Status ===")
for name, p in procs:
    status = "RUNNING" if p.poll() is None else "EXITED"
    print(f"  {name}: {status}")

print("\n=== URLs ===")
print("  Backend API:  http://localhost:8000/api/docs")
print("  Kiosk Web:    http://localhost:5174")
print("  Admin Web:    http://localhost:5175")

