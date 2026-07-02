#!/usr/bin/env python3
"""Entrée fine : `make demo-phase3` → démo de la nuit (DAEDALUS + dry-run)."""

from __future__ import annotations

import sys

from jarvis.demo import main_phase3

if __name__ == "__main__":
    sys.exit(main_phase3())
