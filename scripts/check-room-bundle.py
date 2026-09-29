#!/usr/bin/env python3
"""Prove that the installed build packages the same assets as the preview, not a UI translation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'App/RoomUI'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--app', type=Path, help='Built .app whose RoomUI resource bytes must match')
p.add_argument('--prototype', type=Path, help='Approved original prototype to check preserved CSS against')
a = p.parse_args()
subprocess.run(['node', '--check', str(BUNDLE / 'room.js')], check=True)
if a.prototype:
    import re
    css = re.search(r'<style>(.*?)</style>', a.prototype.read_text(), re.S).group(1)
    assert (BUNDLE / 'room.css').read_text() == '/* Approved prototype styling, preserved verbatim. */\n' + css
files = {}
for source in sorted(BUNDLE.iterdir()):
    if not source.is_file():
        continue
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if a.app:
        packaged = a.app / 'RoomUI' / source.name
        assert packaged.exists(), f'Missing packaged asset: {source.name}'
        assert packaged.read_bytes() == source.read_bytes(), f'Stale or different packaged asset: {source.name}'
    files[source.name] = digest
print(json.dumps({'status': 'pass', 'same_packaged_bytes': bool(a.app), 'files': files}, indent=2))
