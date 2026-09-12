#!/usr/bin/env python3
"""drescue entry point — see ``python drescue_cli.py --help``."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from drescue.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
