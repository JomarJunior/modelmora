"""Runners: text (transformers), image (diffusers), and test-mode stand-ins.

All three implement the same `Runner` interface in `base.py`, so the worker (Phase 5)
and the API never need to know which one they are holding.
"""

from __future__ import annotations
