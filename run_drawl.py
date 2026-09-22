"""Entry point for PyInstaller.

The package uses relative imports, so a top-level script is needed;
`python -m drawl` remains the usual way to run it from source.
"""
import sys

from drawl.ui.app import main

if __name__ == "__main__":
    sys.exit(main())
