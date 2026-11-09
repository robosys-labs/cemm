# St Gabriel Estate

A 1990s-estate spiritual community simulation in the tradition of Pharaoh. The player coordinates wingless companions while persistent residents, households, institutions and traffic respond to their circumstances and choices.

## Project home and complete downloads

[Open the St Gabriel Estate Space](https://chatgpt.com/space/page_6af1b8026a488191941fc0425db4d90f).

The Space links the complete repository ZIP, original individual assets ZIP, runtime batch 02, and local Git history bundle. It also preserves the design direction, preview and next asset priorities. Access to the Space remains subject to the owner's ChatGPT permissions.

**Storage status:** this CEMM directory contains the project index, design handoff, archive hashes, restoration tool, asset status and resident fixtures. The large ZIP/bundle payloads are Library downloads linked from the Space, NOT binary files committed to this Git branch. Batch 02 is also uploaded directly to the Space. This is not a complete binary mirror.

## Restore the complete working project

Download `St_Gabriel_Estate_Repository.zip` from the Space, then run from this directory:

```bash
python restore.py /path/to/St_Gabriel_Estate_Repository.zip
```

The standard-library-only tool verifies the exact archive size and SHA-256, checks member paths and CRCs, and restores 574 files into a new `restored/` directory. It refuses to overwrite an existing destination. It makes no network requests and does not execute archive code. To check without extracting:

```bash
python restore.py /path/to/St_Gabriel_Estate_Repository.zip --verify-only
```

Open `restored/index.html` for the searchable asset library, and `restored/demo/index.html` for the integration preview. The preview uses fixture data; it is not a running society simulation. Full source, manifests, generators and validation tools are inside the ZIP.

## Scope

The asset manifest addresses 438 PNGs, including 180 animation frames and 15 atlases; 91 editable SVGs are included. Additional previews/source boards are not counted as playable assets. Character locomotion, authored companion actions, directional vehicles and audio remain outstanding.

This project is kept in a dedicated branch and directory. CEMM's runtime, tests, authority data and main branch are unchanged. Historical publishing notes inside the preserved ZIP describe the earlier session; the connected account's current write access was confirmed when this entry was published.
