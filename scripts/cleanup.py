#!/usr/bin/env python3
"""Clean up presentation workspace, preserving only final PPTX files."""

import argparse, shutil
from pathlib import Path


def clean_output_dir(output_dir, dry_run, removed):
    """Keep only .pptx files in output dir; remove everything else."""
    if not output_dir.exists():
        return
    for entry in output_dir.iterdir():
        if entry.is_dir():
            clean_output_dir(entry, dry_run, removed)
            try:
                if not list(entry.iterdir()):
                    removed.append(str(entry))
                    if not dry_run:
                        entry.rmdir()
            except OSError:
                pass
        elif entry.suffix.lower() != ".pptx":
            removed.append(str(entry))
            if not dry_run:
                entry.unlink()


def clean_workspace(workspace, output_dir, dry_run, removed):
    """Remove everything in workspace except the output dir subtree."""
    if not workspace.exists():
        return
    output_resolved = output_dir.resolve()

    for entry in workspace.iterdir():
        entry_resolved = entry.resolve()
        # Check if entry is within output_dir subtree
        try:
            entry_resolved.relative_to(output_resolved)
            # It's inside output dir — only clean non-pptx inside
            if entry_resolved == output_resolved:
                clean_output_dir(entry, dry_run, removed)
            else:
                clean_workspace(entry, output_dir, dry_run, removed)
        except ValueError:
            # Not in output dir — remove entirely
            removed.append(str(entry))
            if not dry_run:
                if entry.is_dir():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    output_dir = Path(args.output_dir).resolve()
    removed = []

    dry_run = args.dry_run

    # Safety check: workspace must be under "presentations" path
    parts = workspace.parts
    if "presentations" not in parts:
        print("ERROR: workspace must be under a 'presentations' directory")
        return 1

    try:
        output_dir.relative_to(workspace)
        # output_dir is within workspace
        if output_dir == workspace:
            clean_output_dir(output_dir, dry_run, removed)
        else:
            clean_workspace(workspace, output_dir, dry_run, removed)
    except ValueError:
        # output_dir is outside workspace — remove entire workspace
        removed.append(str(workspace))
        if not dry_run:
            shutil.rmtree(workspace)

    import json
    print(json.dumps({"workspace": str(workspace), "output_dir": str(output_dir),
                       "dry_run": dry_run, "removed": removed}, indent=2))


if __name__ == "__main__":
    main()
