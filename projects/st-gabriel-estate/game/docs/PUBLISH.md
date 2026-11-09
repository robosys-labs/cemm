# Publish the repository

## Current status

A local Git repository was prepared. No remote was created or uploaded because the connected GitHub tools exposed no repository-creation or content-write action and this runtime had no authenticated Git CLI.

## From the Git bundle

```bash
git clone st-gabriel-estate.bundle st-gabriel-estate
cd st-gabriel-estate
```

Cloning a bundle may set `origin` to the local bundle. Remove that local-only remote before running the publish helper:

```bash
git remote remove origin
gh auth login
python tools/publish_github.py
```

The helper creates a new **private** repository named `st-gabriel-estate` under the signed-in account. Use `--owner ACCOUNT` for another authorized owner. No existing remote is overwritten, and no force-push is used.

## From the working-tree ZIP

Extract the ZIP and enter its `st-gabriel-estate` directory. The ZIP does not contain `.git`; use the bundle to preserve the prepared commit history. The publish helper can initialize the extracted working tree, provided Git's user name and email are already configured:

```bash
gh auth login
python tools/publish_github.py
```

Git and GitHub CLI must be installed locally. The publish helper itself uses only Python's standard library. A no-change preview is available:

```bash
python tools/publish_github.py --dry-run
```

## What will be pushed

The original ZIP under `releases/`, all 137 original extracted PNGs, the new runtime assets and editable vector sources, manifests, source generators, validation tool, catalog, demo and documentation. No credentials, font files or external package folders are included.

CLI reference verified for the helper: `https://cli.github.com/manual/gh_repo_create` and `https://cli.github.com/manual/gh_auth_login`.
