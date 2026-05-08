#!/usr/bin/env python3
"""Validate an icon manifest JSON file against the allowed schema."""

import argparse, json, sys
from pathlib import Path

ALLOWED_SOURCE_TYPES = {
    "official_brand_or_source_asset",
    "native_editable_shape",
    "lucide_or_selected_icon_library",
    "editable_label_or_card",
    "approved_clean_official_source_crop",
    "imagegen_crop_last_resort",
}


def add_error(errors, message):
    errors.append(message)


def require_string(errors, value, path):
    if not isinstance(value, str) or not value.strip():
        add_error(errors, f"{path} must be a non-empty string")


def require_array(errors, value, path):
    if not isinstance(value, list) or len(value) == 0:
        add_error(errors, f"{path} must be a non-empty array")


def validate_item(errors, item, path):
    require_string(errors, item.get("id"), f"{path}.id")
    require_array(errors, item.get("slides"), f"{path}.slides")
    require_string(errors, item.get("role"), f"{path}.role")
    require_string(errors, item.get("source_type"), f"{path}.source_type")

    source_type = item.get("source_type", "")
    if source_type and source_type not in ALLOWED_SOURCE_TYPES:
        add_error(errors, f"{path}.source_type '{source_type}' is not allowed")

    if source_type == "lucide_or_selected_icon_library":
        require_string(errors, item.get("library"), f"{path}.library")
        require_string(errors, item.get("icon_name"), f"{path}.icon_name")

    if source_type in (
        "official_brand_or_source_asset",
        "approved_clean_official_source_crop",
        "imagegen_crop_last_resort",
    ):
        require_string(errors, item.get("asset_path"), f"{path}.asset_path")

    if source_type == "imagegen_crop_last_resort":
        if item.get("approval_status") != "approved_last_resort":
            add_error(errors, f"{path}.approval_status must be 'approved_last_resort'")
        if item.get("not_logo_brand_mark_generic_icon_chart_label_or_ui_symbol") is not True:
            add_error(errors, f"{path} must confirm it is not a logo, brand mark, generic icon, chart label, or UI symbol")
        require_string(errors, item.get("reason_no_better_source_exists"), f"{path}.reason_no_better_source_exists")


def validate_last_resort(errors, item, path):
    require_string(errors, item.get("id"), f"{path}.id")
    require_array(errors, item.get("slides"), f"{path}.slides")
    require_string(errors, item.get("asset_path"), f"{path}.asset_path")
    require_string(errors, item.get("reason_no_better_source_exists"), f"{path}.reason_no_better_source_exists")
    if item.get("approved_by_main_agent") is not True:
        add_error(errors, f"{path}.approved_by_main_agent must be true")
    if item.get("not_logo_brand_mark_generic_icon_chart_label_or_ui_symbol") is not True:
        add_error(errors, f"{path} must confirm it is not a logo, brand mark, generic icon, chart label, or UI symbol")


def main():
    parser = argparse.ArgumentParser(description="Validate icon manifest JSON")
    parser.add_argument("--manifest", required=True, help="Path to icon-manifest.json")
    args = parser.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    errors = []

    if not isinstance(manifest.get("items"), list):
        add_error(errors, "items must be an array")
    else:
        for i, item in enumerate(manifest["items"]):
            validate_item(errors, item, f"items[{i}]")

    if "last_resort_imagegen_crops" in manifest:
        if not isinstance(manifest["last_resort_imagegen_crops"], list):
            add_error(errors, "last_resort_imagegen_crops must be an array")
        else:
            for i, item in enumerate(manifest["last_resort_imagegen_crops"]):
                validate_last_resort(errors, item, f"last_resort_imagegen_crops[{i}]")

    if errors:
        print("Icon manifest check failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print(f"Icon manifest check passed: {args.manifest}")


if __name__ == "__main__":
    main()
