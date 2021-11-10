import os
import subprocess
import re
import importlib


class PackageManager:
    # regex pattern for an import line
    import_pattern = '(^from [^.][^\s]+ import .+)|(^import .+( as .+)?)'
    package_pattern = '((?<=^import )[^\s.]+)|((?<=^from )[^\s.]+)'

    def __init__(self, pwd = '.'):
        self.pwd = pwd

        self.requirements = os.path.join(self.pwd, 'requirements.txt')
        self.has_requirements = self._check_requirements()
        self.packages = self._get_packages()

        print(self.pwd)

    def _get_scripts(self):
        scripts = []
        for path, dirs, files in os.walk(self.pwd):
            scripts = scripts + [os.path.join(path, f) for f in files if re.search('.py$', f)]

        print(scripts)

        return scripts

    def _check_requirements(self):
        return os.path.exists(self.requirements)

    def _install_requirements(requirements=None):
        if requirements is None:
            requirements = self.requirements

        subprocess.run(['pip', 'install', '-r', requirements])

    @staticmethod
    def _check_package_name(package):
        if re.search('_', package):
            return package.replace('_', '-')
        else:
            return package

    @staticmethod
    def _install_package(package):
        print(f'Installing {package}')

        subprocess.run(['pip', 'install', package])

    def _is_import_line(self, line):
        return re.search(self.import_pattern, line) is not None

    def _extract_packages(self, line):
        if re.search(self.package_pattern, line):
            packages = re.search(self.package_pattern, line).group(0)

            return packages.split(',')
        else:
            print(line)
            raise Exception('Not an import statement')

    def _get_packages(self):
        if self.has_requirements:
            return

        packages = []
        for s in self._get_scripts():
            with open(s, 'r') as file:
                for curline in file:
                    line = curline.strip()

                    if self._is_import_line(line):
                        ps = self._extract_packages(line)

                        for p in ps:
                            if p.strip() not in packages and len(p.strip()) > 0:
                                packages.append(p.strip())

        return packages

    def _check_package_install(self):
        need_install = []

        print(packages)

        for p in self.packages:
            try:
                importlib.import_module(p)
                print(f'Can import {p}')
            except ImportError as e:
                need_install.append(p)

        return need_install

    def install_packages(self):
        if self.has_requirements:
            self._install_requirements()
        else:
            need_install = self._check_package_install()

            print(need_install)

            for n in need_install:
                self._install_package(n)
