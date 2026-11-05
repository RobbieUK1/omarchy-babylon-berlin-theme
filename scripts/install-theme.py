#!/usr/bin/env python3
"""Install Babylon Berlin with a shared, theme-scoped Quickshell randomizer."""
import argparse
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
ID = 'crows.background'
SLUG = 'babylon-berlin'


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout.strip()


def enabled_clones(config):
    settings = json.loads((config / 'shell.json').read_text()) if (config / 'shell.json').exists() else {}
    found = []
    for entry in settings.get('plugins', []):
        name = entry if isinstance(entry, str) else entry.get('id', '')
        manifest = config / 'plugins' / name / 'manifest.json'
        if name not in settings.get('disabledPlugins', []) and manifest.exists():
            if json.loads(manifest.read_text()).get('omarchy', {}).get('clonedFrom') == 'omarchy.background':
                found.append(name)
    return found


def main(remove=False):
    home = Path.home()
    config = home / '.config/omarchy'
    target = config / 'themes' / SLUG
    plugin = config / 'plugins' / ID
    if remove:
        marker = target / 'wallpaper-randomizer.json'
        if marker.exists():
            marker.write_text('{"version": 1, "enabled": false}\n')
        if run('omarchy', 'theme', 'current').lower().replace(' ', '-') == SLUG:
            run('omarchy', 'theme', 'set', SLUG)
        print('Babylon Berlin randomizer disabled. Shared renderer and other themes retained.')
        return
    for command in ('omarchy', 'omarchy-shell', 'python3'):
        if not shutil.which(command):
            raise RuntimeError('Missing required command: ' + command)
    source = Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'shell/plugins/background'
    if not (source / 'Background.qml').exists():
        raise RuntimeError('Requires the Omarchy Quickshell background renderer; legacy swaybg is unsupported.')
    clones = enabled_clones(config)
    unknown = [name for name in clones if name not in (ID, 'sunnyoled.background')]
    if unknown:
        raise RuntimeError('Custom renderer needs explicit migration: ' + ', '.join(unknown))
    if not (ROOT / 'backgrounds').is_dir():
        raise RuntimeError('Complete theme checkout required, including backgrounds/.')
    spec = importlib.util.spec_from_file_location('builder', SCRIPTS / 'build-plugin.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    with tempfile.TemporaryDirectory(prefix='babylon-berlin-') as temporary:
        stage = Path(temporary)
        builder.build(source, stage / 'plugin', SCRIPTS)
        # Reuse the known renderer only when its code matches this tested version.
        # Never replace a locally customized renderer, including one using our ID.
        reuse = plugin.exists()
        if reuse:
            for name in ('Background.qml', 'Randomize.js', 'list-backgrounds.py', 'manifest.json'):
                if not (plugin / name).is_file() or (plugin / name).read_bytes() != (stage / 'plugin' / name).read_bytes():
                    raise RuntimeError('Existing shared renderer differs; explicit migration required: ' + str(plugin))
        same_checkout = ROOT.resolve() == target.resolve()
        if not same_checkout:
            shutil.copytree(ROOT, stage / 'theme', ignore=shutil.ignore_patterns('.git', '__pycache__'))
        backup = home / '.local/state/omarchy/backups' / ('babylon-berlin-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir(parents=True)
        if (config / 'shell.json').exists():
            shutil.copy2(config / 'shell.json', backup / 'shell.json')
        if target.exists():
            shutil.copytree(target, backup / 'theme', symlinks=True)
        if plugin.exists():
            shutil.copytree(plugin, backup / 'plugin')
        print('Backup:', backup)
        if not same_checkout:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(stage / 'theme', target)
        if not reuse:
            plugin.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(stage / 'plugin', plugin)
        sunny_marker = config / 'themes/sunny-oled/wallpaper-randomizer.json'
        if 'sunnyoled.background' in clones and sunny_marker.parent.is_dir() and not sunny_marker.exists():
            sunny_marker.write_text('{"version": 1, "enabled": true}\n')
        try:
            run('omarchy-shell', 'shell', 'rescanPlugins')
            for _ in range(40):
                catalog = json.loads(run('omarchy', 'plugin', 'list', '--json'))
                if any(item.get('id') == ID for item in catalog):
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError('Shared wallpaper renderer was not discovered')
            for name in clones:
                if name != ID:
                    run('omarchy', 'plugin', 'disable', name)
            run('omarchy', 'plugin', 'enable', ID)
            run('omarchy', 'theme', 'set', SLUG)
        except Exception:
            if ID not in clones:
                subprocess.run(['omarchy', 'plugin', 'disable', ID], capture_output=True)
            for name in clones:
                subprocess.run(['omarchy', 'plugin', 'enable', name], capture_output=True)
            raise
    print('Babylon Berlin installed with integrated independent wallpapers.')
    print('Disable for this theme: bash install.sh --remove')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remove', action='store_true', help='disable randomization for Babylon Berlin; retain shared renderer')
    args = parser.parse_args()
    main(args.remove)
