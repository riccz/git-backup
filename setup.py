"""The setup script."""

import sys
from typing import List, Tuple

from setuptools import Command, find_packages, setup


class PylintCommand(Command):
    '''Setup custom command that runs pylint.'''

    description = 'Lint using pylint'

    user_options: List[Tuple] = []

    def initialize_options(self):
        '''Must override but does nothing.'''

    def finalize_options(self):
        '''Must override but does nothing.'''

    def run(self):
        '''Run pylint and fail on E, F errors.'''

        if self.distribution.tests_require:
            self.distribution.fetch_build_eggs(self.distribution.tests_require)

        from pylint.lint import Run

        try:
            Run(self.distribution.packages + ['setup.py'], do_exit=True)
        except SystemExit as exc:
            if exc.code & 0b100011 != 0:  # Mask out C, R, W errors
                raise exc


class MypyCommand(Command):
    '''Setup custom command that runs mypy.'''

    description = 'Statically typecheck using mypy'

    user_options: List[Tuple] = []

    def initialize_options(self):
        '''Must override but does nothing.'''

    def finalize_options(self):
        '''Must override but does nothing.'''

    def run(self):  # pylint: disable=no-self-use
        '''Import and run mypy.'''

        if self.distribution.tests_require:
            self.distribution.fetch_build_eggs(self.distribution.tests_require)

        from mypy.main import main  # pylint: disable=no-name-in-module

        try:
            main(None, sys.stdout, sys.stderr,
                 self.distribution.packages + ['setup.py'])
        except SystemExit as exc:
            if exc.code != 0:
                raise exc


# pylint: disable=invalid-name
with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = [
    "click",
    "pygit2",
    "pygithub",
    "python-gitlab",
    "pyyaml",
]

setup_requirements = ['pytest-runner']

test_requirements = [
    'mypy',
    'pylint',
    'pytest-cov',
    'pytest',
]

extra_requirements = {
    'test': test_requirements,
}


setup(
    cmdclass={
        'pylint': PylintCommand,
        'mypy': MypyCommand,
    },
    author="Riccardo Zanol",
    author_email='ricc@zanl.eu',
    entry_points={
        'console_scripts': [
            'git-backup=git_backup.cli:main',
        ],
    },
    install_requires=requirements,
    extras_require=extra_requirements,
    license="GNU General Public License v3",
    long_description=readme,
    include_package_data=True,
    name='git_backup',
    packages=find_packages(include=['git_backup']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://gitlab.com/riccz/git-backup',
    version='0.1.0',
    zip_safe=False,
)
