#!/usr/bin/env python3
"""Create a PRIVATE GitHub repository from this pack using the user's local gh login.

Never reads, prints or asks for a token. Never overwrites a remote or force-pushes.
Run: python tools/publish_github.py [--owner ACCOUNT] [--name st-gabriel-estate]
"""
from __future__ import annotations
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(args: list[str], *, check=True, capture=False) -> subprocess.CompletedProcess:
    return subprocess.run(args,cwd=ROOT,text=True,check=check,capture_output=capture)

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name',default='st-gabriel-estate')
    p.add_argument('--owner',default='')
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',a.name) or (a.owner and not re.fullmatch(r'[A-Za-z0-9-]+',a.owner)):
        p.error('Invalid repository or owner name.')
    target=f'{a.owner}/{a.name}' if a.owner else a.name
    command=['gh','repo','create',target,'--private','--source',str(ROOT),'--remote','origin','--push','--description','St. Gabriel Estate: spiritual community simulation — prototype asset library']
    if a.dry_run:
        print('No changes made. Would create a PRIVATE repository and push committed files:')
        print(subprocess.list2cmdline(command))
        return 0
    for tool in ['git','gh']:
        if not shutil.which(tool):
            print(f'Missing {tool}. Install it before publishing.',file=sys.stderr);return 2
    if run(['gh','auth','status','--hostname','github.com'],check=False,capture=True).returncode:
        print('GitHub CLI is not authenticated. Run: gh auth login',file=sys.stderr);return 2
    if not (ROOT/'.git').exists():
        for field in ['user.name','user.email']:
            r=run(['git','config','--get',field],check=False,capture=True)
            if r.returncode or not r.stdout.strip():
                print(f'Configure git {field} before publishing. No repository created.',file=sys.stderr);return 2
        run(['git','init','-b','main']);run(['git','add','.']);run(['git','commit','-m','assets: import St. Gabriel Estate prototype pack'])
    if run(['git','remote','get-url','origin'],check=False,capture=True).returncode==0:
        print('An origin remote already exists. Refusing to replace it or push without review.',file=sys.stderr);return 2
    if run(['git','status','--porcelain'],capture=True).stdout.strip():
        print('Uncommitted changes exist. Review and commit them before publishing.',file=sys.stderr);return 2
    # Create does not overwrite an existing repository. gh owns the authentication flow.
    run(command)
    run(['gh','repo','view',target,'--json','url,visibility','--jq','{url: .url, visibility: .visibility}'])
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except subprocess.CalledProcessError as e:
        print(f'Command failed with exit status {e.returncode}. No force-push or remote replacement was attempted.',file=sys.stderr)
        sys.exit(e.returncode or 1)
