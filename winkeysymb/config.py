"""Configuration and persistence for WinKeySymb (settings, recent characters, startup)."""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

DEFAULT_CONFIG = {
    "hotkey": "Win+Alt+C",  # Options: Win+Alt+C, Win+Alt+Space, Alt+Shift+Space, Ctrl+Alt+Space
    "start_on_boot": False,
    "max_recents": 24,
    "recent_characters": ["≈", "≠", "→", "α", "β", "°", "€", "—", "½", "✓", "★", "±"],
    "theme": "dark",
    "copy_to_clipboard": True,
}


def get_config_dir() -> Path:
    """Return directory where winkeysymb configuration is stored."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata) / "winkeysymb"
    else:
        base = Path.home() / ".winkeysymb"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_config_path() -> Path:
    return get_config_dir() / "config.json"


class ConfigManager:
    def __init__(self):
        self.path = get_config_path()
        self.data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        self.data[key] = value
        self.save()

    def add_recent(self, char: str):
        recents: List[str] = self.data.get("recent_characters", [])
        if char in recents:
            recents.remove(char)
        recents.insert(0, char)
        max_recents = self.data.get("max_recents", 24)
        self.data["recent_characters"] = recents[:max_recents]
        self.save()

    def get_recents(self) -> List[str]:
        return list(self.data.get("recent_characters", []))

    def toggle_start_on_boot(self) -> bool:
        new_state = not self.get("start_on_boot", False)
        self.set("start_on_boot", new_state)
        self.apply_startup_shortcut(new_state)
        return new_state

    def apply_startup_shortcut(self, enable: bool):
        """Create or remove a shortcut in the Windows Startup directory."""
        startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if not startup_dir.exists():
            return
        
        shortcut_path = startup_dir / "WinKeySymb.lnk"
        
        if not enable:
            if shortcut_path.exists():
                try:
                    shortcut_path.unlink()
                except Exception:
                    pass
            return

        try:
            # Determine target executable
            if getattr(sys, "frozen", False):
                target = sys.executable
            else:
                target = sys.executable
                args = f'"{Path(__file__).parent.parent / "main.py"}"'
            
            # Create shortcut via PowerShell
            ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{target}'
"""
            if not getattr(sys, "frozen", False):
                ps_script += f"$Shortcut.Arguments = '{args}'\n"
            ps_script += """
$Shortcut.WorkingDirectory = Split-Path -Path $Shortcut.TargetPath
$Shortcut.Description = 'WinKeySymb Special Character Picker'
$Shortcut.Save()
"""
            import subprocess
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, check=False)
        except Exception as e:
            print(f"Failed to create startup shortcut: {e}")
