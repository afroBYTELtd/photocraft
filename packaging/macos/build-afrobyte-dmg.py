#!/usr/bin/env python3
"""Create a local AFROBYTE Studio macOS DMG with license notices."""

import argparse
import platform
import plistlib
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "target/afrobyte-studio-build/AFROBYTE Studio.app"
DIST = ROOT / "target/afrobyte-studio-build"

LICENSE_FILES = [
    "LICENSE-MIT",
    "LICENSE-APACHE",
    "NOTICE",
    "ATTRIBUTION.md",
    "assets/dict/LICENSE-SCOWL.txt",
    "assets/fonts/OFL-Inter.txt",
    "assets/fonts/OFL-JetBrainsMono.txt",
    "assets/icons/LICENSE-lucide.txt",
    "assets/icons/LICENSE-noun-magnetic-lasso.txt",
    "assets/icons/LICENSE-symmetry-axes.txt",
    "crates/ui-egui/src/LICENSE-solarized.txt",
    "crates/ui-egui/src/i18n/LICENSE-translations.txt",
]

def run(*args):
    subprocess.run(args, check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace an existing local test DMG",
    )
    args = parser.parse_args()

    info_file = APP / "Contents/Info.plist"
    if not info_file.is_file():
        parser.error("AFROBYTE Studio.app is missing. Build it first.")

    with info_file.open("rb") as f:
        info = plistlib.load(f)

    if info.get("CFBundleIdentifier") != "io.afrobyte.studio":
        parser.error("Unexpected application bundle identifier.")

    if info.get("CFBundleDisplayName") != "AFROBYTE Studio":
        parser.error("Unexpected application display name.")

    missing = [
        name for name in LICENSE_FILES
        if not (ROOT / name).is_file()
    ]
    if missing:
        parser.error("Missing license files: " + ", ".join(missing))

    version = info["CFBundleShortVersionString"]
    arch = platform.machine()
    dmg = DIST / f"AFROBYTE Studio {version}-macos-{arch}.dmg"

    if dmg.exists() and not args.replace:
        parser.error("DMG already exists. Use --replace to rebuild it.")

    run("codesign", "--verify", "--strict", "--deep", str(APP))

    with tempfile.TemporaryDirectory(
        prefix="afrobyte-dmg-",
        dir=DIST,
    ) as tmp:
        tmp = Path(tmp)
        stage = tmp / "stage"
        stage.mkdir()

        run("ditto", str(APP), str(stage / APP.name))

        (stage / "Applications").symlink_to("/Applications")

        licenses = stage / "Licenses"
        for name in LICENSE_FILES:
            source = ROOT / name
            destination = licenses / name
            destination.parent.mkdir(
                parents=True, exist_ok=True
            )
            destination.write_bytes(source.read_bytes())

        (stage / "README - Installation.txt").write_text(
            "AFROBYTE Studio\n\n"
            "Drag AFROBYTE Studio.app into Applications "
            "to install.\n\n"
            "This is a local development test build. "
            "It is not Developer ID signed or notarized "
            "for public distribution.\n\n"
            "Licensing and original project attribution "
            "are provided in the Licenses folder.\n"
        )

        compressed = tmp / "AFROBYTE-Studio.dmg"

        run(
            "hdiutil", "create",
            "-srcfolder", str(stage),
            "-volname", "AFROBYTE Studio",
            "-format", "UDZO",
            str(compressed),
        )

        run("hdiutil", "verify", str(compressed))
        compressed.replace(dmg)

    print("SUCCESS: AFROBYTE Studio DMG created")
    print("SUCCESS: Installer image verified")
    print("SUCCESS: License and attribution files included")
    print(f"INSTALLER: {dmg}")

if __name__ == "__main__":
    main()
