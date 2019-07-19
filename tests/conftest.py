'''Pytest configuration and common fixtures.'''

from pathlib import Path
from shutil import unpack_archive

import pygit2
import pytest

TEST_DATA_DIR = Path(__file__).parent.joinpath('data').resolve()


def pytest_addoption(parser):  # pylint: disable=missing-docstring
    parser.addoption(
        "--fast", action="store_true", default=False, help="don't run slow tests"
    )


def pytest_configure(config):  # pylint: disable=missing-docstring
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):  # pylint: disable=missing-docstring
    if config.getoption("--fast"):
        skip_slow = pytest.mark.skip(
            reason="the `--fast` option skips slow tests")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


@pytest.fixture
def simple_git_repo(tmp_path):
    '''A simple git repository with multiple commits, tags and branches.'''

    tgz_path = TEST_DATA_DIR / 'simple-git-repo.tar.gz'
    unpack_archive(tgz_path, tmp_path)
    repo_path = tmp_path / 'simple-git-repo'
    return pygit2.Repository(str(repo_path))
