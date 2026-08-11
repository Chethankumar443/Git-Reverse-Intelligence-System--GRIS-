# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

# Ensure frontend/dist is included in datas
datas = [
    ('app', 'app'),
    ('.agents', '.agents'),
    ('DESIGN-vercel.md', '.'),
    ('frontend/dist', 'frontend/dist'),
]

hiddenimports = [
    'app._version',
    'app.api.main_router',
    'app.api.analysis',
    'app.api.sessions',
    'app.api.chat',
    'app.api.config',
    'app.api.health',
    'app.api.export',
    'app.core.analysis_runner',
    'app.core.taxonomy',
    'fastapi',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'starlette',
    'starlette.applications',
    'starlette.routing',
    'starlette.staticfiles',
    'starlette.responses',
    'sse_starlette',
    'sse_starlette.sse',
    'websockets',
    'openai',
    'requests',
    'sqlalchemy',
    'keyring',
    'keyring.backends',
    'keyring.backends.Windows',
    'jinja2',
    'sqlite3',
    'webbrowser',
    'asyncio',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'PyQt5', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='git-reverse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='.agents/skills/favicon (1)/favicon.ico',
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
