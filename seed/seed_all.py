# Author: Sarala Biswal
"""Seed all local mock data."""

from __future__ import annotations

from seed.seed_models import main as seed_models


def main() -> None:
    """Run this module as a command-line entry point."""
    seed_models()
    print("Seed JSON files are available under seed/{domain}/.")


if __name__ == "__main__":
    main()
