#!/usr/bin/env python3
"""Samy TV entry point; the existing main.py backend remains compatible."""
from main import main

if __name__ == '__main__':
    raise SystemExit(main() or 0)
