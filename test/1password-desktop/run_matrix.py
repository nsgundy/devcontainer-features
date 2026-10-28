#!/usr/bin/env python3
"""No host mounts, credentials or desktop access. Build networking is apt-only."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
bases = sys.argv[1:] or ['debian:12', 'debian:13', 'ubuntu:22.04', 'ubuntu:24.04']
failed = []
for base in bases:
    tag = 'local/onepassword-matrix:' + base.replace(':', '-').replace('/', '-')
    try:
        with tempfile.TemporaryFile(mode='w+') as log:
            result = subprocess.run(['docker', 'build', '--build-arg', f'BASE={base}',
                                     '-f', 'test/1password-desktop/matrix.Dockerfile',
                                     '-t', tag, '.'], cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=300)
            if result.returncode:
                log.seek(0)
                print(log.read()[-6000:])
                raise RuntimeError('Image build failed')
        subprocess.run(['docker', 'run', '--rm', '--network', 'none', tag], check=True, timeout=90)
        print(f'PASS: {base}', flush=True)
    except (RuntimeError, subprocess.SubprocessError) as error:
        print(f'FAIL: {base}: {error}', flush=True)
        failed.append(base)
    finally:
        subprocess.run(['docker', 'image', 'rm', tag], capture_output=True)
if failed:
    raise SystemExit('Matrix failures: ' + ', '.join(failed))
