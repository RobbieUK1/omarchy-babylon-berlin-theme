import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EntrypointTests(unittest.TestCase):
    def test_local_and_piped_installer(self):
        # Exercise Bash stdin handling and clone cleanup without touching a desktop.
        with tempfile.TemporaryDirectory(prefix='installer space ') as folder:
            temporary = Path(folder)
            commands = temporary / 'bin'
            commands.mkdir()
            log = temporary / 'called'
            clone = temporary / 'clone-path'
            (commands / 'python3').write_text('#!/bin/bash\n[[ -f "$1" ]] || exit 2\nprintf "%s\\n" "$@" > "$CALL_LOG"\n')
            (commands / 'git').write_text('#!/bin/bash\n[[ "$1" == clone && "$*" == *"--branch main"* ]] || exit 2\ndest="${@: -1}"\nprintf "%s" "$dest" > "$CLONE_LOG"\ncp -a "$TEST_ROOT" "$dest"\n')
            for p in commands.iterdir():
                p.chmod(0o755)
            env = dict(os.environ, PATH=str(commands)+':'+os.environ['PATH'], CALL_LOG=str(log), CLONE_LOG=str(clone), TEST_ROOT=str(ROOT))
            subprocess.run(['bash', str(ROOT/'install.sh'), '--remove'], env=env, check=True)
            self.assertEqual(log.read_text().splitlines(), [str(ROOT/'scripts/install-theme.py'), '--remove'])
            subprocess.run(['bash', '-s', '--', '--remove'], input=(ROOT/'install.sh').read_text(), text=True, cwd=temporary, env=env, check=True)
            self.assertEqual(log.read_text().splitlines()[1], '--remove')
            self.assertFalse(Path(clone.read_text()).exists())


if __name__ == '__main__':
    unittest.main()
