import os
import sys
from collections import defaultdict

from copr_clean.parser import find_copr_repos
from copr_clean.api import check_copr_status

import subprocess

def get_installed_copr_packages() -> dict:
    """
    Query the local RPM database to get all currently installed package names.
    Uses `rpm -qa --qf '%{NAME}\n'` for fast, clean name extraction.
    """
    try:
        result = subprocess.run(
            ["rpm", "-qa", "--qf", "%{NAME}|%{VENDOR}\n"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        installed_package_name_and_vendor = {}
        
        for line in result.stdout.splitlines():
            if '|' in line:
                name, vendor = line.split("|" ,1 )
                if "copr" in vendor.lower():
                    installed_package_name_and_vendor[name.strip()] = vendor.strip()

        return installed_package_name_and_vendor

    except subprocess.CalledProcessError as e:
        print(f"[-] Warning: Failed to query local RPM database: {e}")
        return {}




def find_installed_copr_packages(copr_package_names: list) -> list:
    """
    Cross-reference a list of COPR package names against the local RPM database
    to find which ones are currently installed on the user's system.
    """
    installed_copr_package = get_installed_copr_packages()
    
    # Filter the COPR list to only include packages present in the local RPM set
    matched_packages = [pkg for pkg in copr_package_names if pkg in installed_copr_package]
    return matched_packages


def is_root():
    """Check if the script is running with root/sudo privileges."""
    return os.geteuid() == 0


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
            print(f"[ {status:^16} ] {owner}/{project}")

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
        print("Please re-run this command with 'sudo copr-clean' to perform cleanup.")
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

