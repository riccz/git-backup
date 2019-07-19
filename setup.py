#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

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
    'pytest-mypy',
    'pytest-pylint',
    'pytest',
]

extra_requirements = {
    'test': test_requirements,
}

setup(
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
