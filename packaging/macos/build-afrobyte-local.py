#!/usr/bin/env python3
"""Build a locally signed AFROBYTE Studio macOS app from the release binary."""

import json
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "target/afrobyte-studio-build/AFROBYTE Studio.app"
BINARY = ROOT / "target/release/photocraft"
ICON = ROOT / "assets/app-icon/afrobyte-studio.icns"
TEMPLATE = ROOT / "packaging/macos/Info.plist.in"

def run(*args):
    subprocess.run(args, check=True)

def main():
    if sys.argv[1:] not in ([], ["--replace"]):
        sys.exit("Usage: python3 packaging/macos/build-afrobyte-local.py [--replace]")

    for path in (BINARY, ICON, TEMPLATE):
        if not path.is_file():
            sys.exit(f"Missing required file: {path}")

    if APP.exists():
        if "--replace" not in sys.argv:
            sys.exit("App already exists. Close it and rerun with --replace.")
        shutil.rmtree(APP)

    metadata = json.loads(subprocess.check_output(
        ["cargo", "metadata", "--no-deps", "--format-version", "1"],
        cwd=ROOT, text=True
    ))
    manifest = (ROOT / "apps/photocraft/Cargo.toml").resolve()
    version = next(
        p["version"] for p in metadata["packages"]
        if Path(p["manifest_path"]).resolve() == manifest
    )
    sha = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT, text=True
    ).strip()

    macos = APP / "Contents/MacOS"
    resources = APP / "Contents/Resources"
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)

    shutil.copy2(BINARY, macos / "AFROBYTEStudio")
    shutil.copy2(ICON, resources / "AFROBYTEStudio.icns")

    xml = TEMPLATE.read_text()
    for marker, value in (
        ("@VERSION@", version),
        ("@SHORT_VERSION@", version.split("-")[0]),
        ("@BUILD_SHA@", sha),
    ):
        xml = xml.replace(marker, value)

    plist = plistlib.loads(xml.encode("utf-8"))
    plist["CFBundleDisplayName"] = "AFROBYTE Studio"
    plist["CFBundleName"] = "AFROBYTE Studio"
    plist["CFBundleExecutable"] = "AFROBYTEStudio"
    plist["CFBundleIdentifier"] = "io.afrobyte.studio"
    plist["CFBundleIconFile"] = "AFROBYTEStudio"
    plist["NSHumanReadableCopyright"] = (
        "AFROBYTE Studio is based on PhotoCraft. "
        "Original contributors retain their copyrights. MIT OR Apache-2.0."
    )

    for entry in plist.get("UTExportedTypeDeclarations", []):
        if entry.get("UTTypeIdentifier") == "ai.storyteller.photocraft.document":
            entry["UTTypeIdentifier"] = "io.afrobyte.studio.document"
            entry["UTTypeDescription"] = "AFROBYTE Studio Document"
        if entry.get("UTTypeIconFile") == "PhotoCraft":
            entry["UTTypeIconFile"] = "AFROBYTEStudio"

    for entry in plist.get("UTImportedTypeDeclarations", []):
        identifier = entry.get("UTTypeIdentifier", "")
        if identifier.startswith("ai.storyteller.photocraft."):
            entry["UTTypeIdentifier"] = identifier.replace(
                "ai.storyteller.photocraft.", "io.afrobyte.studio.", 1
            )

    for entry in plist.get("CFBundleDocumentTypes", []):
        if entry.get("CFBundleTypeName") == "PhotoCraft Document":
            entry["CFBundleTypeName"] = "AFROBYTE Studio Document"
            entry["LSHandlerRank"] = "Alternate"
        if entry.get("CFBundleTypeIconFile") == "PhotoCraft":
            entry["CFBundleTypeIconFile"] = "AFROBYTEStudio"
        entry["LSItemContentTypes"] = [
            x.replace("ai.storyteller.photocraft.", "io.afrobyte.studio.", 1)
            for x in entry.get("LSItemContentTypes", [])
        ]

    with (APP / "Contents/Info.plist").open("wb") as f:
        plistlib.dump(plist, f, sort_keys=False)

    (APP / "Contents/PkgInfo").write_bytes(b"APPL????")

    run("plutil", "-lint", str(APP / "Contents/Info.plist"))
    run("codesign", "--force", "--sign", "-", str(APP))
    run("codesign", "--verify", "--strict", "--deep", str(APP))

    print("SUCCESS: AFROBYTE Studio macOS application built")
    print("SUCCESS: Local code signature verified")
    print(f"APPLICATION: {APP}")

if __name__ == "__main__":
    main()
