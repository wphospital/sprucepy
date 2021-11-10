import os
import subprocess
import re
import importlib


class PackageManager:
    # regex pattern for an import line
    import_pattern = '(^from [^.][^\s]+ import .+)|(^import .+( as .+)?)'
    package_pattern = '((?<=^import )[^\s.]+)|((?<=^from )[^\s.]+)'

    def __init__(self, pwd = '.'):
        self.has_requirements = self._check_requirements()
        self.packages = self._get_packages()

        self.pwd = pwd

        self._set_working_directory()

    @staticmethod
    def _get_scripts():
        scripts = []
        for path, dirs, files in os.walk('.'):
            scripts = scripts + [os.path.join(path, f) for f in files if re.search('.py$', f)]

        return scripts

    @staticmethod
    def _check_requirements():
        return os.path.exists('requirements.txt')

    @staticmethod
    def _install_requirements(requirements='requirements.txt'):
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

    def _extract_package(self, line):
        if re.search(self.package_pattern, line):
            return re.search(self.package_pattern, line).group(0)
        else:
            print(line)
            raise Exception('Not an import statement')

    def _set_working_directory(self):
        os.chdir(self.pwd)

    def _get_packages(self):
        if self.has_requirements:
            return

        packages = []
        for s in self._get_scripts():
            with open(s, 'r') as file:
                for curline in file:
                    line = curline.strip()

                    if self._is_import_line(line):
                        package = self._extract_package(line)

                        if package not in packages:
                            packages.append(package)

        return packages

    def _check_package_install(self):
        need_install = []
        for p in self.packages:
            try:
                importlib.import_module(p)
            except ImportError as e:
                need_install.append(p)

        return need_install

    def install_packages(self):
        if self.has_requirements:
            self._install_requirements()
        else:
            need_install = self._check_package_install()

            for n in need_install:
                self._install_package(n)
