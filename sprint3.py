#!/usr/bin/env python3
import glob
import configparser
import urllib.request
import urllib.parse
import urllib.error
import json
import os
import sys
from collections import defaultdict


def is_root():
    """Check if the script is running with root/sudo privileges."""
    return os.geteuid() == 0


def find_copr_repos():
    """
    Finds COPR repo files, parses them,
    and yields (filepath, owner, project) for each valid COPR baseurl found.
    """
    repo_files = glob.glob("/etc/yum.repos.d/_copr*.repo")

    for filepath in repo_files:
        config = configparser.RawConfigParser()
        try:
            config.read(filepath)
        except configparser.Error as e:
            print(f"Skipping {filepath}, parse error: {e}")
            continue

        for section in config.sections():
            baseurl = config[section].get("baseurl", "")

            if "copr.fedorainfracloud.org" in baseurl:
                parts = baseurl.split("/")
                try:
                    results_index = parts.index("results")
                    if parts[results_index + 1] == "g":
                        owner = "g/" + parts[results_index + 2]
                        project = parts[results_index + 3]
                    else:
                        owner = parts[results_index + 1]
                        project = parts[results_index + 2]
                    yield filepath, owner, project
                except (ValueError, IndexError):
                    print(f"Could not parse structure for: {filepath}")


def check_copr_status(owner, project):
    """Queries Fedora COPR API v3 to check if a project exists."""
    if owner.startswith("g/"):
        api_owner = "@" + owner.split("/", 1)[1]
    else:
        api_owner = owner

    safe_owner = urllib.parse.quote(api_owner, safe='')
    safe_project = urllib.parse.quote(project, safe='')
    api_url = f"https://copr.fedorainfracloud.org/api_3/project?ownername={safe_owner}&projectname={safe_project}"

    headers = {'User-Agent': 'copr-clean/1.0'}
    req = urllib.request.Request(api_url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                try:
                    data = json.loads(response.read().decode('utf-8'))
                except json.JSONDecodeError:
                    return "INVALID_RESPONSE"
                return "ACTIVE" if "id" in data or "name" in data else "BROKEN"
            return f"HTTP_{response.status}"
    except urllib.error.HTTPError as e:
        return "BROKEN" if e.code == 404 else f"HTTP_{e.code}"
    except (urllib.error.URLError, TimeoutError):
        return "NETWORK_ERROR"


def clean_broken_repos():
    """Validates repos and offers interactive removal for fully broken repo files."""
    results = list(find_copr_repos())
    if not results:
        print("No COPR repository files found in /etc/yum.repos.d/")
        return

    print(f"Checking {len(results)} COPR entries against live Fedora API...\n")

    # Step 1: Map each file to all of its section statuses
    # Format: filepath -> [ (owner, project, status), ... ]
    file_statuses = defaultdict(list)

    for filepath, owner, project in results:
        status = check_copr_status(owner, project)
        file_statuses[filepath].append((owner, project, status))

        if status == "ACTIVE":
            print(f"[   ACTIVE   ] {owner}/{project}")
        elif status == "BROKEN":
            print(f"[   BROKEN   ] {owner}/{project} -> File: {filepath}")
        else:
            print(f"[ {status:^13} ] {owner}/{project}")

    # Step 2: Categorize files safely
    # Fully broken files: EVERY entry inside the file has status == "BROKEN"
    broken_files = [
        fp for fp, entries in file_statuses.items()
        if all(s == "BROKEN" for _, _, s in entries)
    ]

    # Mixed files: File contains at least one BROKEN section AND at least one ACTIVE section
    mixed_files = [
        fp for fp, entries in file_statuses.items()
        if any(s == "BROKEN" for _, _, s in entries)
        and any(s == "ACTIVE" for _, _, s in entries)
    ]

    # Inform the user about mixed files that were safely excluded from deletion
    if mixed_files:
        print(f"\n[ NOTE ] {len(mixed_files)} file(s) contain both active and broken sections.")
        print("These will NOT be deleted automatically to protect working repositories:")
        for fp in mixed_files:
            print(f"  - {fp}")

    if not broken_files:
        print("\nNo fully broken repository files to clean up.")
        return

    print(f"\nFound {len(broken_files)} fully broken repository file(s).")

    # Step 3: Privilege Check before prompting for deletion
    if not is_root():
        print("\n[WARNING] Root privileges are required to remove repo files.")
        print("Please re-run this command with 'sudo python3 sprint3.py' to perform cleanup.")
        return

    # Step 4: Interactive deletion for fully broken files
    for filepath in broken_files:
        confirm = input(f"Delete broken repo file '{filepath}'? [y/N]: ").strip().lower()
        if confirm == 'y':
            try:
                os.remove(filepath)
                print(f"[DELETED] {filepath}")
            except OSError as e:
                print(f"[ERROR] Failed to delete {filepath}: {e}")
        else:
            print(f"[SKIPPED] {filepath}")


if __name__ == "__main__":
    clean_broken_repos()
