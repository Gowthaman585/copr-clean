import os
from collections import defaultdict

from copr_clean.parser import find_copr_repos
from copr_clean.api import check_copr_status

import subprocess



def setup_copr_package_names() -> dict:
    """
    Query the local dnf database to get all currently installed copr package names.
    """
    try:
        result = subprocess.run(
            ["dnf", "repoquery", "--installed", "--qf", "%{name}|%{from_repo}\n"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        copr_packages_ProjectOwner_name = defaultdict(set)
        
        for line in result.stdout.splitlines():
            if '|' in line:
                name, repo = line.split("|" ,1 )
                parts = repo.strip().split(":")
                if(len(parts)>=4 and parts[0].lstrip("@") == "copr"):
                    copr_packages_ProjectOwner_name[parts[-1],parts[-2]].add(name.strip())
        return copr_packages_ProjectOwner_name

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to query local RPM database: {e}")
        return {}


def is_root():
    """Check if the script is running with root/sudo privileges."""
    return os.geteuid() == 0




def clean_broken_repos():
    
    """Validates repos and offers interactive removal for fully broken repo files."""

    # collect all the availabe copr repos in /etc/yum*
    results = list(find_copr_repos())
    
    if not results:
        print("No COPR repository files found in /etc/yum.repos.d/")
        return

    print(f"Checking {len(results)} COPR entries against live Fedora API...\n")

    # Step 1: Map each file to all of its section statuses
    # Format: filepath -> [ (owner, project, status), ... ]
    file_statuses = defaultdict(list)

    for filepath, owner, project in results:
        status = check_copr_status(owner,project)
        file_statuses[filepath].append((owner, project, status))

        if status == "ACTIVE":
            print(f"[ACTIVE] {owner}/{project}")
        elif status == "BROKEN":
            print(f"[BROKEN] {owner}/{project} -> File: {filepath}")
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

    # collect all the copr packages downloaded in the system
    copr_packages_details = setup_copr_package_names()
    
    
    # Step 4: Interactive deletion for fully broken files
    
    # get the filepath that their package can't be removed for some reasons 
    failed_filepath_package_removal = set()
    # this one is for the package that user did not want to uninstall so collect that particular repo filepath not to touch them
    cancelled_filepath_package_removal = set()

    for filepath in broken_files:
        entries = file_statuses[filepath]
        for owner, project, status in entries:
            matched_package_name = copr_packages_details.get((project,owner),set())
            if matched_package_name:
                for pkg in matched_package_name:
                    confirm = input(f"Delete installed package '{pkg}'? [y/N]: ").strip().lower()
                    if confirm == 'y':
                        try:
                            subprocess.run(["dnf","remove",pkg] , check=True)
                            print("[SUCCESS] Package removed.")
                        except subprocess.CalledProcessError as e:
                            failed_filepath_package_removal.add(filepath)
                            print(f"[ERROR] Failed to remove the package {pkg}: {e}")
                    else:
                        cancelled_filepath_package_removal.add(filepath)
                        print(f"[SKIPPED] leaving the package '{pkg}' as installed")


        if filepath not in cancelled_filepath_package_removal and filepath not in failed_filepath_package_removal:
            confirm = input(f"Delete broken repo file '{filepath}'? [y/N]: ").strip().lower()
            if confirm == 'y':
                try:
                    os.remove(filepath)
                    print(f"[SUCCESS] repofile removed {filepath}")
                except OSError as e:
                    print(f"[ERROR] Failed to delete {filepath}: {e}")
            else:
                print(f"[SKIPPED] repofile {filepath}")

