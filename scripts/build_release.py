import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
SPEC_FILE = ROOT_DIR / "git_reverse.spec"
ICON_PATH = ROOT_DIR / ".agents" / "skills" / "favicon (1)" / "favicon.ico"

def create_desktop_shortcut(target_path: Path, shortcut_name: str = "Git Reverse.lnk"):
    """Creates a Windows Desktop Shortcut pointing to the target executable."""
    desktop = Path(os.path.expanduser("~/Desktop"))
    shortcut_path = desktop / shortcut_name
    
    powershell_cmd = (
        f"$WshShell = New-Object -ComObject WScript.Shell; "
        f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
        f"$Shortcut.TargetPath = '{target_path}'; "
        f"$Shortcut.WorkingDirectory = '{target_path.parent}'; "
        f"$Shortcut.IconLocation = '{ICON_PATH}'; "
        f"$Shortcut.Description = 'Git Reverse Intelligence System Desktop Application'; "
        f"$Shortcut.Save()"
    )
    
    print(f"Creating Desktop Shortcut: {shortcut_path} -> {target_path}")
    result = subprocess.run(["powershell", "-Command", powershell_cmd], capture_output=True, text=True)
    if result.returncode == 0:
        print("Desktop Shortcut created successfully.")
    else:
        print(f"Warning: Failed to create desktop shortcut: {result.stderr}")

def build():
    """Builds PyInstaller executable bundle and generates release package."""
    print("=== Building Git Reverse Release Package ===")
    print(f"Project Root: {ROOT_DIR}")
    
    # 1. Run PyInstaller
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", str(SPEC_FILE)]
    print(f"Running command: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if res.returncode != 0:
        print("Error: PyInstaller build failed!")
        sys.exit(res.returncode)
    
    # Check output executable
    exe_path = DIST_DIR / "git-reverse.exe"
    if not exe_path.exists():
        exe_path = DIST_DIR / "git-reverse" / "git-reverse.exe"
    
    if exe_path.exists():
        print(f"Build Success! Binary output: {exe_path}")
        # Always create desktop shortcut for current user
        create_desktop_shortcut(exe_path)
    else:
        print("Build finished, checking dist folder contents:")
        for item in DIST_DIR.glob("*"):
            print(f" - {item}")

if __name__ == "__main__":
    build()
