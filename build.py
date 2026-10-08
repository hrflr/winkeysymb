"""Build standalone Windows executable and release package for WinKeySymb using PyInstaller."""

import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path


def build():
    root = Path(__file__).parent.resolve()
    main_py = root / "main.py"
    dist_dir = root / "dist"
    build_dir = root / "build"

    print("========================================")
    print(" Building WinKeySymb Standalone Executable ")
    print("========================================")

    # PyInstaller command
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=WinKeySymb",
        "--windowed",          # No console window
        "--onefile",           # Single-file standalone executable
        f"--icon={root / 'assets' / 'icon.ico'}",
        "--clean",
        "--noconfirm",
        f"--add-data={root / 'winkeysymb'}:winkeysymb",
        str(main_py),
    ]

    print("Running command:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=root)
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(result.returncode)

    exe_path = dist_dir / "WinKeySymb.exe"
    if not exe_path.exists():
        print("\nBuild completed but executable was not found.")
        sys.exit(1)

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"\nSUCCESS: Built standalone executable at:\n  {exe_path} ({size_mb:.1f} MB)")

    # Create release zip archive for GitHub Releases
    zip_name = "WinKeySymb-windows-x64.zip"
    zip_path = dist_dir / zip_name
    print(f"\nCreating release archive: {zip_path.name}...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, arcname="WinKeySymb.exe")
        if (root / "install.ps1").exists():
            zf.write(root / "install.ps1", arcname="install.ps1")
        if (root / "README.md").exists():
            zf.write(root / "README.md", arcname="README.md")
        if (root / "LICENSE").exists():
            zf.write(root / "LICENSE", arcname="LICENSE")

    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"SUCCESS: Created release package:\n  {zip_path} ({zip_size_mb:.1f} MB)\n")


if __name__ == "__main__":
    build()
