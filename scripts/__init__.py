"""Shared utilities for CLI scripts."""

import sys
from pathlib import Path

# Setup path once
sys.path.insert(0, str(Path(__file__).parent.parent))
