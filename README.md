# copr-clean

A small command-line tool for Fedora/RPM-based systems that scans your locally
enabled [COPR](https://copr.fedorainfracloud.org/) repositories and checks
whether each one still exists on the Fedora COPR servers — then helps you
clean up the ones that don't.

Over time, COPR projects get renamed, deleted, or abandoned by their
maintainers. When that happens, the `.repo` file on your system sticks
around, pointing at a URL that no longer resolves — and DNF quietly starts
throwing errors (or worse, silently skipping the repo) on every
`dnf update`. `copr-clean` finds those dead repos for you and offers to
remove them, safely and interactively.

## What it does

1. **Scans** `/etc/yum.repos.d/` for COPR repo files (`_copr:*.repo`)
2. **Extracts** the owner and project name from each repo's `baseurl`
   (including group-owned projects, e.g. `@somegroup`)
3. **Validates** each one against the live Fedora COPR API
4. **Reports** each repo as `ACTIVE`, `BROKEN`, or a network/HTTP error
5. **Offers cleanup** — with your explicit `y/N` confirmation per file, and
   only after checking for root privileges

## Requirements

- Python 3.6+
- No external dependencies — uses only the Python standard library
  (`configparser`, `urllib`, `json`, `os`, `glob`)
- A COPR-based system (Fedora, Nobara, or any RPM distro using
  `/etc/yum.repos.d/`)

## Usage

### Check and clean up broken repos

```bash
sudo python3 start-scan.py
```

Example output:

```
Checking 3 COPR entries against live Fedora API...

[   ACTIVE   ] atim/lazygit
[   BROKEN   ] fakeuser/fakeproject -> File: /etc/yum.repos.d/_copr:...:fakeuser:fakeproject.repo

Found 1 broken repository file(s).
Delete broken repo file '/etc/yum.repos.d/_copr:...:fakeuser:fakeproject.repo'? [y/N]:
```

If you run it without `sudo`, it will still scan and report status — it
just won't offer to delete anything, since removing files from
`/etc/yum.repos.d/` requires root:

```
[WARNING] Root privileges are required to remove repo files.
Please re-run this command with 'sudo python3 start-scan.py' to perform cleanup.
```

### Safety behavior

- Repo files with **more than one** COPR entry are only offered for deletion
  if **every** entry in that file is broken. If a file has a mix of active
  and broken entries, it's left alone and flagged separately, so you never
  lose a working repo by accident.
- Deletion always requires a per-file `y` confirmation — nothing is ever
  removed automatically or in bulk.
- Malformed or unreadable `.repo` files are skipped with a warning instead
  of crashing the whole scan.
- Network issues (timeouts, DNS failures) are reported as
  `NETWORK_ERROR` rather than being mistaken for a broken repo.

## How it identifies a broken repo

Each repo's `baseurl` is parsed to pull out the owner and project name,
which are then checked against the
[COPR API v3](https://copr.fedorainfracloud.org/api_3/docs) `project`
endpoint:

- A `200` response with a valid project object → `ACTIVE`
- A `404` response → `BROKEN`
- Anything else (timeout, DNS failure, unexpected HTTP status) → reported
  as-is, and never treated as broken

## Project structure

This repository's `main` branch contains the finished tool:

| File | Description |
|---|---|
| `start-scan.py` | Scan, validate, and clean up broken COPR repos |

Earlier development stages (repo scanning only, validation without
cleanup) live on the `dev` branch as `sprint1.py` and `sprint2.py`, kept
for reference.

## Limitations

- Only recognizes repos with `copr.fedorainfracloud.org` in the `baseurl`
  — other COPR-compatible hubs aren't currently supported
- Deleted files are removed permanently — there is no backup or undo, so
  read the file path in the confirmation prompt carefully before
  answering `y`

## Installation & Usage

### Option 1: Install via Fedora COPR (Recommended)

You can install `copr-clean` directly as a native package using DNF:

```bash
# 1. Enable the COPR repository
sudo dnf copr enable gowt85/copr-clean

# 2. Install copr-clean
sudo dnf install copr-clean

# 3. Run the scanner
sudo copr-clean

## License

MIT — see [LICENSE](LICENSE) for details.

## Contributing

Issues and pull requests are welcome. If you find a repo layout this
script doesn't parse correctly (e.g. a COPR hub format it doesn't
recognize), please open an issue with the `baseurl` in question (feel free
to redact anything sensitive).
