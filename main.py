"""
Git Reverse Intelligence System — Application Entrypoint
Launches the FastAPI server and opens the desktop UI in the default browser.
"""
import sys
import os
import argparse
import webbrowser
import threading
import time

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app._version import __version__, __app_name__


def parse_args():
    parser = argparse.ArgumentParser(
        prog="gitreverse",
        description="Git Reverse Intelligence System (GRIS) — Repository Intelligence Platform",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"{__app_name__} v{__version__}"
    )
    parser.add_argument(
        "--reset-setup",
        action="store_true",
        help="Reset first-run onboarding wizard preferences",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically",
    )
    return parser.parse_args()


def open_browser_when_ready(host: str, port: int, delay: float = 1.5):
    """Opens the app in the default browser after the server starts."""
    time.sleep(delay)
    webbrowser.open(f"http://{host}:{port}")


def main():
    args = parse_args()

    if args.reset_setup:
        from app.services.secrets import SecretsManager
        config = SecretsManager.load_config()
        config["first_run_complete"] = False
        SecretsManager.save_config(config)
        print("First-run onboarding state reset successfully.")
        return

    from app.api.main_router import create_app
    import uvicorn

    app = create_app()

    host = args.host
    port = args.port

    print(f"\n{'='*56}")
    print(f"  {__app_name__} v{__version__}")
    print(f"  Repository Intelligence System")
    print(f"  Server: http://{host}:{port}")
    print(f"  API Docs: http://{host}:{port}/api/docs")
    print(f"{'='*56}\n")

    # Open browser in background thread after server starts
    if not args.no_browser:
        t = threading.Thread(
            target=open_browser_when_ready,
            args=(host, port),
            daemon=True,
        )
        t.start()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()
