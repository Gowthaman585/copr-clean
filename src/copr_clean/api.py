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



"""
For now this methos used nowhere in this project
but leaving this as it is.
this may usefule at some point of time to specifically search copr repo for more details with copr-api

for now this method is tested to fetch all package names that the repo containes
"""

def get_copr_package_name(owner: str, project: str) -> list:

    
    """
    Query the Fedora COPR v3 API to fetch all package names 
    associated with a specific owner and project.
    
    Endpoint format:
    https://copr.fedorainfracloud.org/api_3/package/get/list?ownername={owner}&projectname={project}
    """
    url = f"https://copr.fedorainfracloud.org/api_3/package/list?ownername={owner}&projectname={project}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "copr-clean/1.0.2 (Python utility)"}
    )
    


    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                # COPR API returns packages under the 'items' key
                packages = data.get("items", [])
                # Extract just the package names from the dictionary objects

                # !!! <DEBUG> may be other then extracting name something can useful from the packages above
                # for i in packages:
                #    print(f"====={i}=====1")
                # !!! <end>

                return [pkg.get("name") for pkg in packages if "name" in pkg]
    except Exception as e:
        # Gracefully handle network errors or missing projects during check
        print(f"[-] Warning: Could not fetch package manifest for {owner}/{project}: {e}")
        
    return []

