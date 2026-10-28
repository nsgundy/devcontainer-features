#!/usr/bin/env python3
"""Local socket-access test with the installed extension CLI; no authentication."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--allow-desktop-access', action='store_true', required=True)
parser.add_argument('--cli', type=Path, required=True)
parser.add_argument('--no-lockfile', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
assert (Path(os.environ['XDG_RUNTIME_DIR']) / '1Password-BrowserSupport.sock').is_socket()
gid = subprocess.check_output(['stat', '-c', '%g', '/usr/bin/op'], text=True).strip()

def command(argv, **kwargs):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=240, **kwargs)
    if result.returncode:
        print(result.stdout[-6000:])
        print(result.stderr[-6000:])
        raise RuntimeError(f'Command failed: {argv[0]}')
    return result.stdout

def files(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file()}

workspace_mutations = False
for scenario in ('dockerfile', 'compose'):
    with tempfile.TemporaryDirectory(prefix=f'onepassword-feature-{scenario}-') as temporary:
        workspace = Path(temporary)
        config_dir = workspace / '.devcontainer'
        config_dir.mkdir()
        shutil.copytree(root / 'src/1password-desktop', config_dir / 'feature')
        (config_dir / 'Dockerfile').write_text('''FROM ubuntu:24.04
RUN usermod -u 12345 ubuntu && groupmod -g 12345 ubuntu && chown -R 12345:12345 /home/ubuntu
USER ubuntu
CMD ["sleep", "infinity"]
''')
        config = {'remoteUser': 'ubuntu', 'updateRemoteUserUID': True}
        project = f'onepassword-test-{os.getpid()}'
        if scenario == 'dockerfile':
            config['build'] = {'dockerfile': 'Dockerfile'}
        else:
            (config_dir / 'compose.yaml').write_text(f'''name: {project}
services:
  development:
    build: .
    command: sleep infinity
    volumes:
      - ..:/workspace
''')
            config.update(dockerComposeFile='compose.yaml', service='development', workspaceFolder='/workspace')
        (config_dir / 'devcontainer.json').write_text(json.dumps(config))
        before = files(workspace)
        container = None
        image = None
        label = f'onepassword-feature-test={scenario}-{os.getpid()}'
        try:
            output = command(['node', str(args.cli), 'up', '--workspace-folder', str(workspace),
                              '--id-label', label, '--additional-features', json.dumps({
                                  './feature': {'hostCliGid': gid, 'acceptRuntimeOverride': True}}),
                              '--include-merged-configuration', '--log-level', 'info',
                              *(['--no-lockfile'] if args.no_lockfile else [])])
            result = json.loads(output.strip().splitlines()[-1])
            assert result['outcome'] == 'success'
            container = result['containerId']
            image = command(['docker', 'inspect', '-f', '{{.Config.Image}}', container]).strip()
            uid = command(['docker', 'exec', '-u', 'ubuntu', container, 'id', '-u']).strip()
            assert uid == str(os.getuid()), f'UID update failed: {uid}'
            doctor = command(['docker', 'exec', '-u', 'ubuntu', container, '1password-desktop-doctor'])
            assert 'FAIL:' not in doctor
            # postStart must have completed; test a second explicit lifecycle run.
            command(['docker', 'exec', '-u', 'ubuntu', container, 'sudo', '-n',
                     '/usr/local/share/1password-desktop/configure-user.py'])
            after = files(workspace)
            changed = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
            print(json.dumps({'scenario': scenario, 'uid_updated': True, 'doctor_passed': True,
                              'lifecycle_rerun_passed': True, 'workspace_changes': changed}), flush=True)
            workspace_mutations |= bool(changed)
        finally:
            # Label cleanup also covers a partial CLI failure before returning an ID.
            ids = subprocess.check_output(['docker', 'ps', '-aq', '--filter', f'label={label}'], text=True).split()
            for cid in ids:
                subprocess.run(['docker', 'rm', '-f', cid], capture_output=True)
            if scenario == 'compose':
                subprocess.run(['docker', 'compose', '-p', project, '-f', str(config_dir / 'compose.yaml'),
                                'down', '--remove-orphans'], capture_output=True)
            if image:
                subprocess.run(['docker', 'image', 'rm', image], capture_output=True)
            # The CLI may also tag an intermediate image before UID remapping.
            tags = subprocess.check_output(['docker', 'image', 'ls', '--format',
                                            '{{.Repository}}:{{.Tag}}'], text=True).splitlines()
            for tag in tags:
                if tag.startswith(f'vsc-{workspace.name}-') or tag.startswith(f'{project}-'):
                    subprocess.run(['docker', 'image', 'rm', tag], capture_output=True)
if workspace_mutations:
    raise SystemExit('Workspace mutation gate failed (see results above)')
