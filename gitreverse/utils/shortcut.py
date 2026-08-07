import os
import sys
import subprocess
import platform
from pathlib import Path
from gitreverse.utils.logging import get_logger

logger = get_logger("utils.shortcut")

def create_desktop_shortcut() -> bool:
    """Create a desktop shortcut to launch Git Reverse in a terminal window."""
    system = platform.system()
    desktop_dir = Path.home() / "Desktop"

    if not desktop_dir.exists():
        logger.warning("Desktop directory does not exist.")
        return False

    try:
        if system == "Windows":
            shortcut_path = desktop_dir / "Git Reverse.lnk"
            # Target cmd.exe to launch gitreverse in a visible console window
            ps_script = f"""
            $WScriptShell = New-Object -ComObject WScript.Shell
            $Shortcut = $WScriptShell.CreateShortcut('{shortcut_path}')
            $Shortcut.TargetPath = 'cmd.exe'
            $Shortcut.Arguments = '/c gitreverse'
            $Shortcut.WorkingDirectory = '{Path.home()}'
            $Shortcut.WindowStyle = 1
            $Shortcut.Description = 'Git Reverse Intelligence System'
            $Shortcut.Save()
            """
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                logger.info(f"Desktop shortcut created at {shortcut_path}")
                return True
            else:
                logger.error(f"Failed to create Windows shortcut: {res.stderr}")
                return False

        elif system == "Linux":
            shortcut_path = desktop_dir / "gitreverse.desktop"
            content = f"""[Desktop Entry]
Name=Git Reverse
Comment=Git Reverse Intelligence System
Exec=x-terminal-emulator -e gitreverse || gnome-terminal -- gitreverse || konsole -e gitreverse
Terminal=true
Type=Application
Categories=Development;
"""
            shortcut_path.write_text(content)
            shortcut_path.chmod(0o755)
            logger.info(f"Desktop shortcut created at {shortcut_path}")
            return True

        elif system == "Darwin": # macOS
            shortcut_path = desktop_dir / "Git Reverse.command"
            content = """#!/usr/bin/env bash
gitreverse
"""
            shortcut_path.write_text(content)
            shortcut_path.chmod(0o755)
            logger.info(f"Desktop shortcut created at {shortcut_path}")
            return True

    except Exception as e:
        logger.error(f"Error creating shortcut: {e}")
        return False

    return False
