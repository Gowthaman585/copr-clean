Name:           copr-clean
Version:        1.0
Release:        2%{?dist}
Summary:        Scan and clean up broken COPR repositories

License:        MIT
URL:            https://github.com/Gowthaman585/copr-clean
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch
Requires:       python3

%description
copr-clean scans locally enabled COPR repositories, validates them
against the live Fedora COPR API, and helps remove ones that no
longer exist upstream.

%prep
%setup -q

%build
# nothing to build, it's a plain Python script

%install
mkdir -p %{buildroot}%{_bindir}
install -m 0755 start-scan.py %{buildroot}%{_bindir}/copr-clean

%files
%{_bindir}/copr-clean
%license LICENSE
%doc README.md

%changelog
* Sat Sep 05 2026 Gowthaman M <gowthamanm585@gmail.com> - 1.0-1
- Initial release
