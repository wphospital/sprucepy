import os
import subprocess
import re
import pkgutil
import sys
from .constants import ineligible_packages


class PackageManager:
    # regex pattern for an import line
    import_pattern = '(^from [^.][^\s]+ import .+)|(^import .+( as .+)?)'
    package_pattern = '((?<=^import )[^\s.]+)|((?<=^from )[^\s.]+)'

    def __init__(self, pwd = '.'):
        self.pwd = pwd

        self.requirements = os.path.join(self.pwd, 'requirements.txt')
        self.has_requirements = self._check_requirements()
        self.packages = self._get_packages()

    def _get_scripts(self):
        scripts = []
        for path, dirs, files in os.walk(self.pwd):
            scripts = scripts + [os.path.join(path, f) for f in files if re.search('.py$', f)]

        return scripts

    def _check_requirements(self):
        return os.path.exists(self.requirements)

    def _install_requirements(self, requirements=None):
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

            return [p.strip() for p in packages.split(',')]
        else:
            raise Exception(f'Not an import statement: {line}')

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
                            if p not in packages and len(p) > 0 and p not in ineligible_packages:
                                packages.append(p)

        return packages

    def _check_package_install(self):
        importable = [m.name for m in pkgutil.iter_modules()] + list(sys.builtin_module_names)

        print(self.packages)

        need_install = list(set(self.packages) - set(importable))

        print(need_install)

        return need_install

    def install_packages(self):
        print(f'Starting install routine in {self.pwd}')

        # TODO: evaluate whether it's ever better to use requirements.txt
        # if self.has_requirements:
        #     print('Has requirements')
        #     self._install_requirements()
        # else:

        print('Checking for needed packages')
        need_install = self._check_package_install()

        for n in need_install:
            self._install_package(n)
