#!/usr/bin/env python3
import glob
import configparser
import urllib.request
import urllib.parse
import urllib.error
import json


def find_copr_repos():
    """
    Shared scanning logic: finds COPR repo files, parses them,
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


def scan_repos():
    """List owner/project/filepath for every COPR repo found."""
    results = list(find_copr_repos())
    if not results:
        print("No COPR repository files found in /etc/yum.repos.d/")
        return

    print(f"Found {len(results)} COPR entr(y/ies):\n")
    for filepath, owner, project in results:
        print(f"File:    {filepath}")
        print(f"Owner:   {owner}")
        print(f"Project: {project}")
        print("-" * 40)


def validate_repos():
    """Validate each found COPR repo against the live Fedora API."""
    results = list(find_copr_repos())
    if not results:
        print("No COPR repository files found in /etc/yum.repos.d/")
        return

    print(f"Checking {len(results)} COPR entries  against live Fedora API...\n")
    for filepath, owner, project in results:
        status = check_copr_status(owner, project)
        if status == "ACTIVE":
            print(f"[  ACTIVE  ] {owner}/{project}")
        elif status == "BROKEN":
            print(f"[  BROKEN  ] {owner}/{project} -> File: {filepath}")
        else:
            print(f"[ {status} ] {owner}/{project}")


if __name__ == "__main__":
    validate_repos()
