"""Windows entry point; ROM/editor code is kept in the unmodified module."""
import sys
from pathlib import Path

import penc_editor


if getattr(sys, "frozen", False):
    # Presets and a base ROM beside the EXE must be resolved beside the EXE,
    # rather than in the temporary directory used by a one-file bundle.
    penc_editor.__file__ = str(Path(sys.executable).resolve().with_suffix(".py"))


if __name__ == "__main__":
    raise SystemExit(penc_editor.release__main())

