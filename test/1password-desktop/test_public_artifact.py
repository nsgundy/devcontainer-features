#!/usr/bin/env python3
"""Anonymous registry/archive checks and credential-free Feature build smoke test."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--cli', type=Path, required=True)
args = parser.parse_args()
repository = 'nsgundy/devcontainer-features/1password-desktop'
expected_digest = 'sha256:6657a917a6ce58e346e920155939a49fbee6a203a2f07914fd6ddc1fb47f711a'
# No local credentials are consulted for these HTTP requests.
with urllib.request.urlopen(f'https://ghcr.io/token?service=ghcr.io&scope=repository:{repository}:pull', timeout=30) as response:
    token = json.load(response)['token']

def fetch(path):
    request = urllib.request.Request(f'https://ghcr.io/v2/{repository}/{path}', headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.oci.image.manifest.v1+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()

manifest = None
for tag in ('0.1.0', '0.1', '0', 'latest'):
    data = fetch('manifests/' + tag)
    assert 'sha256:' + hashlib.sha256(data).hexdigest() == expected_digest
    manifest = json.loads(data)
print('Anonymous tags verified:', expected_digest, flush=True)
layer = manifest['layers'][0]
archive = fetch('blobs/' + layer['digest'])
assert 'sha256:' + hashlib.sha256(archive).hexdigest() == layer['digest']
packaged = {}
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    for member in tar.getmembers():
        if member.isdir():
            continue
        assert member.isfile(), 'Unexpected non-file archive member'
        name = member.name.removeprefix('./')
        assert '/' not in name and name not in packaged, 'Unexpected archive path'
        packaged[name] = tar.extractfile(member).read()
assert set(packaged) == {'LICENSE', 'README.md', 'configure-user.py', 'devcontainer-feature.json', 'doctor.py', 'install.sh'}
metadata = json.loads(packaged['devcontainer-feature.json'])
assert metadata['id'] == '1password-desktop' and metadata['version'] == '0.1.0'
print('Released archive integrity/allowlist verified; included files:', ', '.join(sorted(packaged)), flush=True)

with tempfile.TemporaryDirectory(prefix='onepassword-public-install-') as temporary:
    workspace = Path(temporary)
    config = workspace / '.devcontainer'
    config.mkdir()
    (config / 'devcontainer.json').write_text(json.dumps({'image': 'ubuntu:24.04', 'remoteUser': 'ubuntu'}))
    home = workspace / 'clean-home'
    home.mkdir()
    docker_config = workspace / 'docker-config'
    docker_config.mkdir()
    (docker_config / 'config.json').write_text('{}')
    # Minimal environment: no gh tokens, Docker auth, credential helpers, host
    # home, or prior CLI user data. Builds do not mount the desktop socket.
    env = {'PATH': os.environ['PATH'], 'HOME': str(home), 'DOCKER_CONFIG': str(docker_config)}
    image = 'local/onepassword-public-install:smoke'
    try:
        result = subprocess.run(['node', str(args.cli), 'build', '--workspace-folder', str(workspace),
            '--user-data-folder', str(workspace / 'cli-data'), '--no-lockfile', '--image-name', image,
            '--additional-features', json.dumps({'ghcr.io/' + repository + ':0.1.0': {
                'hostCliGid': '23456', 'acceptRuntimeOverride': True}})],
            env=env, capture_output=True, text=True, timeout=300)
        if result.returncode:
            print(result.stderr[-6000:])
            raise SystemExit(result.returncode)
        subprocess.run(['docker', 'run', '--rm', '--network', 'none', image, 'sh', '-c',
                        'test "$(stat -c %u:%g:%a /usr/bin/op)" = 0:23456:2755'],
                       env=env, check=True, timeout=15)
        print('Credential-free published Feature installation passed; no desktop socket mounted')
    finally:
        subprocess.run(['docker', 'image', 'rm', image], env=env, capture_output=True)
