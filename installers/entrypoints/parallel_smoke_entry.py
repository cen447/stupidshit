#!/usr/bin/env python3
"""PyInstaller entrypoint for the parallel-smoke command."""

from parallel_smoke.cli import parallel_smoke_main


if __name__ == "__main__":
    parallel_smoke_main()

