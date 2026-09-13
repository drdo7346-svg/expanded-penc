"""Build in a clean Windows venv, preserving assertions and all Pillow plugins."""
from pathlib import Path
import json
import os
import subprocess
import sys


root = Path(__file__).resolve().parents[1]
os.chdir(root)
assert sys.platform == "win32", "Build Windows binaries on Windows."
assert sys.flags.optimize == 0, "ROM validation assertions must remain enabled."
args = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean", "--onefile", "--windowed",
    "--optimize", "0",
    "--name", "PenC_Expansion_Editor",
    "--collect-submodules", "PIL",
    "--collect-data", "PIL",
    "--collect-binaries", "PIL",
    "--copy-metadata", "pillow",
    "--hidden-import", "tkinter.filedialog",
    "--hidden-import", "tkinter.simpledialog",
    "--hidden-import", "tkinter.messagebox",
    "--hidden-import", "tkinter.ttk",
    "--distpath", "dist", "--workpath", "work", "--specpath", ".",
    "scripts/launcher.py",
]
upx = os.environ.get("PENC_UPX_DIR")
args[3:3] = ["--upx-dir", upx] if upx else ["--noupx"]
subprocess.run(args, check=True)
(root / "build-command.json").write_text(json.dumps(args, indent=2))

