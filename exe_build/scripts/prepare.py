from pathlib import Path
import base64
import hashlib
import json
import lzma


root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "manifest.json").read_text())
parts = []
for row in manifest["parts"]:
    data = base64.b64decode((root / row["path"]).read_bytes(), validate=True)
    assert len(data) == row["size"]
    assert hashlib.sha256(data).hexdigest() == row["sha256"]
    parts.append(data)
packed = b"".join(parts)
assert hashlib.sha256(packed).hexdigest() == manifest["packed_sha256"]
source = lzma.decompress(packed)
assert len(source) == manifest["source_size"]
assert hashlib.sha256(source).hexdigest() == manifest["source_sha256"]
(root / "scripts" / "penc_editor.py").write_bytes(source)
compile(source, "penc_editor.py", "exec", optimize=0)
print("Exact source verified:", manifest["source_sha256"], len(source), "bytes")

