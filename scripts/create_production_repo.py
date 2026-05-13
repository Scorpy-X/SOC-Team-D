"""Safe helper for creating a disposable production-style staging copy.

This script used to delete and recreate the sibling ``SOC Team D`` folder while
excluding the exploratory backend and Chainlit app. That behavior is now stale:
``SOC Team D`` is a curated submission repository, and the Chainlit/backend
advisor is part of the current delivery story.

By default, this script is guidance-only and copies nothing. If a teammate wants
a throwaway staging copy for inspection, they must provide an explicit target
folder with ``--staging-copy --target <path>``. Existing targets are never
overwritten unless ``--allow-overwrite`` is also passed.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Sequence


ROOT_DIR = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
    "third_party",
    "tmp",
}

EXCLUDED_PATH_PREFIXES = {
    "data/reports",
    "data/validation",
}

EXCLUDED_FILES = {
    ".env",
    "data/soc_advisor.db",
}


def should_skip(path: Path) -> bool:
    """Return whether a source path should be excluded from a staging copy."""

    relative_path = path.resolve().relative_to(ROOT_DIR)
    relative_text = relative_path.as_posix()

    if relative_text in EXCLUDED_FILES:
        return True

    if any(
        relative_text == prefix or relative_text.startswith(f"{prefix}/")
        for prefix in EXCLUDED_PATH_PREFIXES
    ):
        return True

    return any(part in EXCLUDED_DIRS for part in relative_path.parts)


def build_guidance_message() -> str:
    """Explain the current safe production-repo workflow."""

    return "\n".join(
        [
            "No files were copied.",
            "",
            "Current repo truth:",
            "- SOC exp is the working superset.",
            "- SOC Team D is updated through curated snapshot promotion, not a blind copy.",
            "- Current snapshots should preserve Team D history and promote only reviewed files.",
            "",
            "If you only need a disposable staging copy for inspection, run:",
            "  python scripts/create_production_repo.py --staging-copy --target <new-folder>",
            "",
            "The staging copy keeps the current advisor stack, including backend/soc_advisor,",
            "config, Chainlit experiment files, public Chainlit UI assets, and report templates.",
            "It excludes secrets, virtualenvs, git metadata, generated reports, validation logs,",
            "temporary files, third-party source checkouts, and node_modules.",
        ]
    )


def copy_staging_repo(target_dir: Path, *, allow_overwrite: bool = False) -> None:
    """Create a non-authoritative staging copy at an explicit target path."""

    target_dir = target_dir.resolve()
    if target_dir == ROOT_DIR:
        raise ValueError("Target directory cannot be the source repo.")

    if target_dir.exists():
        if not allow_overwrite:
            raise FileExistsError(
                f"Target already exists: {target_dir}. "
                "Pass --allow-overwrite only for a disposable staging folder."
            )
        shutil.rmtree(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    for source_path in ROOT_DIR.rglob("*"):
        if should_skip(source_path):
            continue

        relative_path = source_path.relative_to(ROOT_DIR)
        target_path = target_dir / relative_path

        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Show current SOC Team D snapshot guidance or create a disposable "
            "production-style staging copy."
        )
    )
    parser.add_argument(
        "--staging-copy",
        action="store_true",
        help="Create a disposable staging copy instead of printing guidance only.",
    )
    parser.add_argument(
        "--target",
        type=Path,
        help="Explicit target folder for --staging-copy.",
    )
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow deleting and recreating the explicit staging target.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.staging_copy:
        print(build_guidance_message())
        return 0

    if args.target is None:
        parser.error("--staging-copy requires --target <folder>")

    copy_staging_repo(args.target, allow_overwrite=args.allow_overwrite)
    print(f"Created disposable staging copy at {args.target.resolve()}")
    print("This is not a replacement for the curated SOC Team D snapshot workflow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
