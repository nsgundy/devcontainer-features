#!/usr/bin/env python3
"""Fail closed before publishing a new stable Feature version."""
import argparse
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

REPOSITORY = 'nsgundy/devcontainer-features'
PACKAGE = REPOSITORY + '/1password-desktop'


def validate(root, version):
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise ValueError('Use a stable version such as 0.2.1, without a v prefix')
    metadata = json.loads((root / 'src/1password-desktop/devcontainer-feature.json').read_text())
    if metadata['version'] != version:
        raise ValueError('Requested version must match Feature metadata')
    notes = root / 'releases' / (version + '.md')
    if not notes.is_file() or not notes.read_text().strip():
        raise ValueError('Add non-empty release notes at releases/<version>.md')
    return notes


def fetch(url, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=30) as response:
        return response.read()


def require_absent(url, headers):
    try:
        fetch(url, headers)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return
        raise
    raise ValueError('Version already exists; refusing to overwrite: ' + url)


def check_remote(version):
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('Release publishing is restricted to the owning repository')
    headers = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
               'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    require_absent(f'https://api.github.com/repos/{REPOSITORY}/git/ref/tags/v{version}', headers)
    require_absent(f'https://api.github.com/repos/{REPOSITORY}/releases/tags/v{version}', headers)
    token = json.loads(fetch(f'https://ghcr.io/token?service=ghcr.io&scope=repository:{PACKAGE}:pull'))['token']
    require_absent(f'https://ghcr.io/v2/{PACKAGE}/manifests/{version}', {
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.oci.image.manifest.v1+json'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version')
    parser.add_argument('--check-remote', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    validate(root, args.version)
    if args.check_remote:
        check_remote(args.version)
    print('Release preflight passed:', args.version)


if __name__ == '__main__':
    main()
