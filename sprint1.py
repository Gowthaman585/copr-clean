#!/usr/bin/env python3
import glob
import configparser

def sprint1_scan_repos():
    """
    Sprint 1: Scan /etc/yum.repos.d/ for COPR repo files and extract
    owner, project name, and file path from each baseurl.
    """

    # 1. Find all COPR repository files
    repo_files = glob.glob("/etc/yum.repos.d/_copr*.repo")

    if not repo_files:
        print("No COPR repository files found in /etc/yum.repos.d/")
        return

    print(f"Found {len(repo_files)} COPR file(s):")

    # 2. Parse each file
    for filepath in repo_files:
        # RawConfigParser avoids crashes when a value contains a literal '%'
        # (ConfigParser treats '%' as the start of interpolation syntax,
        # e.g. %(name)s, and raises InterpolationSyntaxError on bare '%').
        config = configparser.RawConfigParser()

        try:
            config.read(filepath)
        except configparser.Error as e:
            # Catches things RawConfigParser does NOT protect against,
            # e.g. DuplicateSectionError, DuplicateOptionError, or a
            # malformed line that isn't valid INI syntax.
            # 'continue' skips only this file and moves to the next one,
            # so one corrupt repo file doesn't kill the whole scan.
            print(f"Skipping {filepath}, parse error: {e}")
            continue

        for section in config.sections():
            baseurl = config[section].get("baseurl", "")

            if "copr.fedorainfracloud.org" in baseurl:
                parts = baseurl.split("/")
                try:
                    # Find where 'results' is in the URL path
                    results_index = parts.index("results")

                    # COPR group-owned projects have an extra 'g' segment:
                    # .../results/g/<groupname>/<project>/...
                    # Personal projects look like:
                    # .../results/<owner>/<project>/...
                    if parts[results_index + 1] == "g":
                        owner = "g/" + parts[results_index + 2]
                        project = parts[results_index + 3]
                    else:
                        owner = parts[results_index + 1]
                        project = parts[results_index + 2]

                    print(f"File:    {filepath}")
                    print(f"Owner:   {owner}")
                    print(f"Project: {project}")
                    print("-" * 40)

                except (ValueError, IndexError):
                    # 'results' not found in URL, or URL has fewer
                    # segments than expected after 'results'
                    print(f"Could not parse structure for: {filepath}")

if __name__ == "__main__":
    sprint1_scan_repos()
