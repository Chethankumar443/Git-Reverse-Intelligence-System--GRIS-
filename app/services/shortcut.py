"""
Shortcut Service — Desktop Shortcut Creation for Git Reverse System.
Automatically creates a Desktop shortcut (.lnk) upon setup completion or demand.
"""

import os
import sys
import subprocess
import logging

logger = logging.getLogger(__name__)


def create_desktop_shortcut(name: str = "Git Reverse") -> bool:
    """
    Creates a desktop shortcut (.lnk) pointing to main.py / python environment.
    Returns True if successfully created, False otherwise.
    """
    try:
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop_dir):
            logger.warning(f"Desktop directory not found at {desktop_dir}")
            return False

        # Target script main.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)
        workspace_dir = os.path.dirname(app_dir)
        main_py = os.path.join(workspace_dir, "main.py")

        if not os.path.exists(main_py):
            logger.warning(f"main.py not found at {main_py}")
            return False

        shortcut_path = os.path.join(desktop_dir, f"{name}.lnk")

        # Icon path
        logo_dir = os.path.join(workspace_dir, ".agents", "skills", "favicon (1)")
        icon_path = os.path.join(logo_dir, "favicon.ico")

        # Target executable (prefer pythonw.exe if available to avoid console flash)
        python_exe = sys.executable
        pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
        target_exe = pythonw_exe if os.path.exists(pythonw_exe) else python_exe

        # PowerShell commands to build shortcut via WScript.Shell
        ps_commands = [
            "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('" + shortcut_path.replace("'", "''") + "')",
            "$s.TargetPath = '" + target_exe.replace("'", "''") + "'",
            "$s.Arguments = '\"" + main_py.replace("'", "''") + "\"'",
            "$s.WorkingDirectory = '" + workspace_dir.replace("'", "''") + "'",
        ]
        if os.path.exists(icon_path):
            ps_commands.append("$s.IconLocation = '" + icon_path.replace("'", "''") + "'")
        ps_commands.append("$s.Save()")

        ps_script = "; ".join(ps_commands)

        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script]

        # Hide subprocess window on Windows
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=creation_flags
        )

        if result.returncode == 0 and os.path.exists(shortcut_path):
            logger.info(f"Desktop shortcut created successfully at: {shortcut_path}")
            return True
        else:
            logger.error(f"Failed to create shortcut: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Error creating desktop shortcut: {e}")
        return False
