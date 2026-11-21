import os
from pathlib import Path
import struct
import subprocess
import tempfile
import pytest

from app.storage.database import DatabaseManager


def test_icon_assets_exist_and_valid():
    """Verify that TRIAD icon assets exist and contain all standard Windows resolutions."""
    root = Path(__file__).resolve().parent.parent
    ico_path = root / "assets" / "triad.ico"
    png_path = root / "assets" / "triad.png"

    assert ico_path.exists(), "assets/triad.ico must exist"
    assert png_path.exists(), "assets/triad.png must exist"
    assert ico_path.stat().st_size > 1000, "assets/triad.ico must not be empty"
    assert png_path.stat().st_size > 1000, "assets/triad.png must not be empty"

    # Inspect ICO binary header
    with open(ico_path, "rb") as f:
        data = f.read()

    assert len(data) >= 6
    reserved, icon_type, count = struct.unpack("<HHH", data[:6])
    assert reserved == 0
    assert icon_type == 1  # 1 = ICO
    assert count >= 4, f"ICO must have at least 4 resolutions, found {count}"

    # Read each ICONDIRENTRY (16 bytes each)
    sizes = []
    for i in range(count):
        offset = 6 + i * 16
        w, h, color_count, _, planes, bpp, bytes_in_res, img_offset = struct.unpack(
            "<BBBBHHII", data[offset : offset + 16]
        )
        actual_w = 256 if w == 0 else w
        actual_h = 256 if h == 0 else h
        sizes.append(actual_w)

    assert 16 in sizes, "ICO must contain 16px resolution"
    assert 32 in sizes, "ICO must contain 32px resolution"
    assert 48 in sizes, "ICO must contain 48px resolution"
    assert 256 in sizes, "ICO must contain 256px resolution"


def test_database_uses_localappdata():
    """Verify that DatabaseManager defaults to per-user LOCALAPPDATA directory."""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        db = DatabaseManager()
        assert local_appdata.lower() in db.db_path.lower()
        assert "TRIAD" in db.db_path
        assert db.db_path.endswith("triad_workspace.db")


def test_build_script_configuration():
    """Verify that build.ps1 includes the icon and packaging configuration."""
    root = Path(__file__).resolve().parent.parent
    build_ps1 = root / "build.ps1"
    content = build_ps1.read_text(encoding="utf-8")

    assert "--icon=\"assets/triad.ico\"" in content
    assert "--windowed" in content or "--noconsole" in content
    assert "--onedir" in content
    assert "TRIAD.exe" in content
    assert "$Shortcut" in content


def test_desktop_shortcut_script_validation():
    """Verify that Create-DesktopShortcut.ps1 validates executable presence and syntax."""
    root = Path(__file__).resolve().parent.parent
    shortcut_ps1 = root / "Create-DesktopShortcut.ps1"
    assert shortcut_ps1.exists()

    content = shortcut_ps1.read_text(encoding="utf-8")
    assert "TRIAD.exe" in content
    assert "TRIAD.lnk" in content
    assert "Desktop" in content
    assert "WScript.Shell" in content
    assert "TargetPath" in content
    assert "WorkingDirectory" in content
    assert "IconLocation" in content

    # Run dry-run test with non-existent path to verify validation logic
    cmd = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(shortcut_ps1),
        "-DistPath",
        "D:\\non_existent_folder\\fake.exe",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 1
    assert "Packaged executable not found" in proc.stdout or "Packaged executable not found" in proc.stderr
