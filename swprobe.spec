%define short_name swprobe
%define version 0.2.1
%define release SPI1
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Middleware for exporting swift metrics to statsd
Name: openstack-swift-%{short_name}
Version: %{version}
Release: %{release}
Source0: %{short_name}-%{version}.tar.gz
License: Apache Software License 2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Packager: Jasper Capel <jasper.capel@spilgames.com>
Url: https://github.com/spilgames/swprobe
Requires: python
BuildRequires: python python-setuptools

%description
Middleware for exporting swift metrics to statsd

%prep
%setup -n %{short_name}-%{version}

%build
python setup.py build

%install
python setup.py install --root=%{buildroot} --record=INSTALLED_FILES

%clean
rm -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root)
%{python_sitelib}/*
