"""The setup script."""

import sys
from subprocess import run
from typing import List, Tuple

from setuptools import Command, find_packages, setup

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

packages = find_packages(include=['git_backup'])


class PylintCommand(Command):
    '''Setup custom command that runs pylint.'''

    description = 'Run pylint.'

    user_options: List[Tuple] = []

    def initialize_options(self):
        '''Must override but does nothing.'''

    def finalize_options(self):
        '''Must override but does nothing.'''

    def run(self):  # pylint: disable=no-self-use
        '''Run pylint and fail on E, F errors.'''
        pylint_proc = run(['pylint'] + packages + ['setup.py'])
        if pylint_proc.returncode & 0b100011 != 0:  # Mask out C, R, W errors
            sys.exit(pylint_proc.returncode)


class MypyCommand(Command):
    '''Setup custom command that runs mypy.'''

    description = 'Run mypy.'

    user_options: List[Tuple] = []

    def initialize_options(self):
        '''Must override but does nothing.'''

    def finalize_options(self):
        '''Must override but does nothing.'''

    def run(self):  # pylint: disable=no-self-use
        '''Import and run mypy.'''
        mypy_proc = run(['mypy'] + packages + ['setup.py'])
        if mypy_proc.returncode != 0:
            sys.exit(mypy_proc.returncode)


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
    packages=packages,
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://gitlab.com/riccz/git-backup',
    version='0.1.0',
    zip_safe=False,
)
