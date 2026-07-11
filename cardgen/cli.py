"""Minimal CLI for rendering item-card YAML to a PDF (handy for local testing).

Usage: python -m cardgen.cli input.yaml -o out.pdf
"""
import argparse
import pathlib
import sys

import yaml

from .render import render_item_cards, RenderOptions


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render D&D item cards to PDF.")
    parser.add_argument("input", type=pathlib.Path, help="Path to input YAML file")
    parser.add_argument(
        "-o", "--out", type=pathlib.Path, default=pathlib.Path("cards.pdf")
    )
    parser.add_argument("-f", "--fonts", choices=["free", "accurate"], default="free")
    parser.add_argument("-b", "--bleed", type=float, default=0.0, help="Bleed in mm")
    args = parser.parse_args(argv)

    with open(args.input, "r") as stream:
        entries = yaml.load(stream, Loader=yaml.SafeLoader)

    # Resolve relative image paths against the YAML file's directory.
    for entry in entries:
        img = entry.get("image_path")
        if img and not pathlib.Path(img).is_absolute():
            entry["image_path"] = str((args.input.parent / img).absolute())

    options = RenderOptions(fonts=args.fonts, bleed_mm=args.bleed)
    pdf = render_item_cards(entries, options)
    args.out.write_bytes(pdf)
    if options.errors:
        print("Could not fit: " + ", ".join(options.errors), file=sys.stderr)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
