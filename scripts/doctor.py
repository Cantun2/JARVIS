#!/usr/bin/env python3
"""Entrée fine : `make doctor` → diagnostic (logique dans jarvis.doctor)."""

from __future__ import annotations

import sys

from jarvis.doctor import main

if __name__ == "__main__":
    sys.exit(main())
