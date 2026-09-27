"""
SELORA One-Click Application Launcher
ISRO Smart India Hackathon 2026 (Problem Statement: 26166)

Usage:
    python run.py
    or
    python -m uvicorn main:app --reload --port 8000
"""

import sys
import webbrowser
from pathlib import Path
import uvicorn

ROOT = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    print("\n" + "=" * 70)
    print("  [*] SELORA - Sensor-Aware Lunar Image Registration System")
    print("  ISRO Smart India Hackathon 2026 (Problem Statement 26166)")
    print("=" * 70)
    print(f"  [+] Unified Web Interface: {url}")
    print(f"  [+] Interactive Workspace: {url}/workspace")
    print(f"  [+] Benchmark Suite:       {url}/benchmark")
    print(f"  [+] Comparative Matrix:    {url}/benchmark/compare")
    print(f"  [+] Swagger Documentation: {url}/docs")
    print("=" * 70)
    print("  Starting server... (Press CTRL+C to stop)\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    # Launch uvicorn server pointing to root main:app
    uvicorn.run("main:app", host=host, port=port, reload=True)
