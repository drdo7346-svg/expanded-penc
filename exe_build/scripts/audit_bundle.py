"""Verify the actual one-file archive contains the complete original code."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import types

from PyInstaller.archive.readers import CArchiveReader


root = Path(__file__).resolve().parents[1]
exe = root / "dist" / "PenC_Expansion_Editor.exe"
reader = CArchiveReader(str(exe))
archive = reader.open_embedded_archive("PYZ.pyz")
frozen = archive.extract("penc_editor")
source = (root / "scripts" / "penc_editor.py").read_bytes()
manifest = json.loads((root / "manifest.json").read_text())
assert hashlib.sha256(source).hexdigest() == manifest["source_sha256"]
original = compile(source, "penc_editor.py", "exec", optimize=0)
count = [0]


def compare(left, right, where="module"):
    assert type(left) is type(right), where
    if isinstance(left, types.CodeType):
        count[0] += 1
        # Only the compiler's filesystem path may differ. Compare bytecode,
        # constants/docstrings, assertions, exception tables and debug lines.
        for name in (
            "co_argcount", "co_posonlyargcount", "co_kwonlyargcount", "co_nlocals",
            "co_stacksize", "co_flags", "co_code", "co_names", "co_varnames",
            "co_freevars", "co_cellvars", "co_name", "co_qualname",
            "co_firstlineno", "co_linetable", "co_exceptiontable", "co_consts",
        ):
            compare(getattr(left, name), getattr(right, name), where + "/" + name)
    elif isinstance(left, (tuple, list)):
        assert len(left) == len(right), where
        for i, (a, b) in enumerate(zip(left, right)):
            compare(a, b, f"{where}[{i}]")
    else:
        assert left == right, where


compare(original, frozen)
entries = list(reader.toc)
for required in ("python312.dll", "_tkinter.pyd", "tcl86t.dll", "tk86t.dll"):
    assert any(Path(p).name.lower() == required for p in entries), required
for required in ("tkinter", "tkinter.filedialog", "tkinter.simpledialog",
                 "tkinter.messagebox", "tkinter.ttk", "PIL.Image", "PIL.ImageTk",
                 "PIL.PngImagePlugin", "PIL.BmpImagePlugin", "PIL.GifImagePlugin"):
    assert required in archive.toc, required
assert any(p.replace("\\", "/").endswith("/encoding/cp949.enc") for p in entries)
data = exe.read_bytes()
assert data[:2] == b"MZ"
pe = struct.unpack_from("<I", data, 0x3C)[0]
assert data[pe:pe+4] == b"PE\0\0"
assert struct.unpack_from("<H", data, pe+4)[0] == 0x8664
assert struct.unpack_from("<H", data, pe+24+68)[0] == 2  # GUI subsystem
result = {
    "source_sha256": manifest["source_sha256"],
    "source_bytes": len(source),
    "exe_bytes": len(data),
    "exe_sha256": hashlib.sha256(data).hexdigest(),
    "architecture": "Windows x64",
    "original_code_objects_preserved": count[0],
    "bytecode_docstrings_assertions_and_exception_tables_identical": True,
    "tk_tcl_korean_encoding_present": True,
    "pillow_modules": sorted(p for p in archive.toc if p.startswith("PIL.")),
    "archive_members": entries,
    "archive_sizes": {name: list(row) for name, row in reader.toc.items()},
    "optimization_level": 0,
    "external_python_installation_required": False,
}
(root / "bundle-audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print("PASS complete source retained:", count[0], "code objects")
print("EXE:", len(data), "bytes; SHA256:", result["exe_sha256"])

