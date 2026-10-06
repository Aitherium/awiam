# awiam for agents

Read this if you are an agent (or a human) editing this package. Short on
purpose: the commands, the traps that cost a session, and where the rest lives.
Nothing here is read at runtime — it is for you.

## What this is

PyPI distribution **`awiam`** (version in `pyproject.toml`), import package
`awiam`, Python >= 3.10. Who is this caller? A directory and session store
that **fails honestly**. Deactivation that takes effect "eventually" is not
deactivation, and a store that cannot be read reports zero users — which every
caller reads as "nobody is authorised" or, worse, as an empty directory to
helpfully repopulate.

This repository is a **synced mirror** of the AitherOS monorepo (lane
`.github/workflows/sync-awiam.yml`). Hand edits made here are overwritten on
the next sync — change the source and let the lane publish.

## Build, test, verify

```bash
python -m pytest tests -q        # the suite: 10 tests, green at v0.1.0
pip install -e .                 # editable install for developing against it
```

The suite was run from a source checkout with no prior install. The publish
lane (`publish-brick.yml`) additionally builds the wheel, installs it and
imports it — a tree that tests green can still ship a broken wheel.

## Rules that keep this useful

- **An unreadable store is never an empty directory.** The whole reason this
  brick exists is the tagline's failure mode: "cannot read" MUST return as
  could-not-judge, never as zero users and never as "nobody is authorised".
  `test_identity.py` pins it; any new read path gets the same case.
- **Deactivation is immediate or it is a lie.** No grace windows, no
  caches that outlive a revoke. If a caller can still resolve a deactivated
  identity after the write returns, the write is wrong.
- **Identity data is the last thing to log.** Names, sessions and keys do not
  belong in error strings; keep diagnostics about the SHAPE of the record,
  not its contents.
- **The registry drives the public surface.** This repo's README header,
  `llms.txt` and `aither-manifest.json` are generated from the ecosystem
  registry (one yaml in the AitherOS monorepo) and rewritten on every sync.
  Change the registry; do not hand-edit the generated blocks.

## Read next

- `llms.txt` — the install/use card written for an agent to execute
- `README.md` — the human front door
- `docs/` — the generated docs site source
