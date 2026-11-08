"""
Module for finding and parsing COPR repository files.
Handles detection of /etc/yum.repos.d/_copr*.repo files 
and extracts owner/project information from baseurl lines.
"""

import glob
import configparser


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

