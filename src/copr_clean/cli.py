#!/usr/bin/env python3

from copr_clean.cleaner import clean_broken_repos
from copr_clean.api import get_copr_package_name
from copr_clean.cleaner import find_installed_copr_packages

def main():
    # !!! Commenting out this call temporarily
    # clean_broken_repos()
    # !!!

    # copr_packages_name -> list []
    copr_package_name = get_copr_package_name("relativesure","all-packages")
    
    # installed-copr_packages -> list []
    installed_copr_packages = find_installed_copr_packages(copr_package_name)
    
    if installed_copr_packages:
        print("======= Installed copr packages =======")
        for pkg in installed_copr_packages:
            print(f"- {pkg}")
        print("="*40)
    else:
        print("!!! No copr package is found")
            


if __name__ == "__main__":
    main()
