import urllib.request
import urllib.parse
import urllib.error
import json


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
                return "ACTIVE" if "id" in data or "name" in data else "INVALID_RESPONSE"
            return f"HTTP_{response.status}"
    except urllib.error.HTTPError as e:
        return "BROKEN" if e.code == 404 else f"HTTP_{e.code}"
    except (urllib.error.URLError, TimeoutError):
        return "NETWORK_ERROR"


