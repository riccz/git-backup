import tempfile
from pathlib import Path
from subprocess import check_call, check_output
from textwrap import dedent

import pygit2
import pytest

from git_backup.backup import *


pytestmark = pytest.mark.slow


def test_smoke(simple_git_repo, tmp_path):
    '''Check that a regular clone-fetch-update cycle runs without crashing.'''

    source_repo = GitRepo(simple_git_repo.path, 'simple-repo', 'simple-repo')
    bak_repo = LocalBackup(source_repo, tmp_path / 'local_backups')
    bak_repo.backup()


def test_origin_remote(simple_git_repo, tmp_path):
    '''Check that the local backup has an 'origin' remote, with the right URL.'''

    source_repo = GitRepo(simple_git_repo.path, 'simple-repo', 'simple-repo')
    bak_repo = LocalBackup(source_repo, tmp_path / 'local_backups')
    bak_repo.clone()
    assert bak_repo.cloned_repo.remotes['origin'].url == source_repo.url


def test_clone_idempotent(simple_git_repo, tmp_path):
    '''Check that multiple calls to clone have no effect.'''

    source_repo = GitRepo(simple_git_repo.path, 'simple-repo', 'simple-repo')
    bak_repo = LocalBackup(source_repo, tmp_path / 'local_backups')
    bak_repo.clone()
    bak_repo.clone()
    assert bak_repo.cloned_repo.remotes['origin'].url == source_repo.url


def test_fetch_refs(simple_git_repo, tmp_path):
    '''Check that all the references are fetched with the right name.

    See `README.md` for a known issue with non-commit references (like
    `direct_README` in `simple_git_repo`).
    '''

    source_repo = GitRepo(simple_git_repo.path, 'simple-repo', 'simple-repo')
    bak_repo = LocalBackup(source_repo, tmp_path / 'local_backups')
    bak_repo.clone()
    bak_repo.fetch()

    backup_refs = [ref for ref in bak_repo.cloned_repo.references
                   if bak_repo._is_remote_ref(ref)]
    expected_refs = [
        'refs/git-backup/origin/heads/master',
        'refs/git-backup/origin/heads/fork1',
        'refs/git-backup/origin/heads/fork2',
        'refs/git-backup/origin/tags/initial_commit',
        'refs/git-backup/origin/tags/list_of_refs',
        # 'refs/git-backup/origin/sym_alias_fork1',
        # 'refs/git-backup/origin/direct_README',
    ]
    assert sorted(backup_refs) == sorted(expected_refs)


def test_fetch_fastforward(simple_git_repo, tmp_path):
    '''Check that a fast-forwarded remote ref is fetched.'''

    source_repo = GitRepo(simple_git_repo.path, 'simple-repo', 'simple-repo')
    bak_repo = LocalBackup(source_repo, tmp_path / 'local_backups')
    bak_repo.clone()
    bak_repo.fetch()

    old_master = bak_repo.cloned_repo.lookup_reference(
        'refs/git-backup/origin/heads/master'
    )

    check_call(['git', 'checkout', 'master'], cwd=simple_git_repo.workdir)
    with Path(simple_git_repo.workdir).joinpath('README.md').open('w') as f:
        f.write(dedent('''\
            # Edited README #

            This file README.md is being replaced to test the fetch of
            an updated reference.
        '''))
    check_call(['git', 'commit', '-am', 'Replace README.md'],
               cwd=simple_git_repo.workdir)

    bak_repo.fetch()
    new_master = bak_repo.cloned_repo.lookup_reference(
        'refs/git-backup/origin/heads/master'
    )
    new_master_parent = bak_repo.cloned_repo.revparse_single(
        'refs/git-backup/origin/heads/master^'
    )

    assert old_master.target != new_master.target
    assert old_master.target == new_master_parent.oid
    assert str(new_master.target) == check_output(
        ['git', 'log', '--pretty=format:%H', '-n', '1', 'master'],
        cwd=simple_git_repo.workdir, text=True
    ).strip()


def test_fetch_nonff(simple_git_repo, tmp_path):
    '''Check that a non-fast-forwarded remote ref is fetched.'''

    source_repo = GitRepo(simple_git_repo.path, 'simple-repo', 'simple-repo')
    bak_repo = LocalBackup(source_repo, tmp_path / 'local_backups')
    bak_repo.clone()
    bak_repo.fetch()

    old_master = bak_repo.cloned_repo.lookup_reference(
        'refs/git-backup/origin/heads/master'
    )

    check_call(['git', 'checkout', 'master'], cwd=simple_git_repo.workdir)
    with Path(simple_git_repo.workdir).joinpath('README.md').open('w') as f:
        f.write(dedent('''\
            # Edited README #

            This file README.md is being replaced to test the fetch of
            an updated reference.
        '''))
    check_call(['git', 'commit', '--amend', '-am', 'Replace README.md'],
               cwd=simple_git_repo.workdir)

    bak_repo.fetch()
    new_master = bak_repo.cloned_repo.lookup_reference(
        'refs/git-backup/origin/heads/master'
    )
    new_master_parent = bak_repo.cloned_repo.revparse_single(
        'refs/git-backup/origin/heads/master^'
    )

    assert old_master.target != new_master.target
    assert old_master.target != new_master_parent.oid
    assert str(new_master.target) == check_output(
        ['git', 'log', '--pretty=format:%H', '-n', '1', 'master'],
        cwd=simple_git_repo.workdir, text=True
    ).strip()


def test_update_idempotent(simple_git_repo, tmp_path):
    '''Check that a repeated update works.'''

    source_repo = GitRepo(simple_git_repo.path, 'simple-repo', 'simple-repo')
    bak_repo = LocalBackup(source_repo, tmp_path / 'local_backups')
    bak_repo.clone()
    bak_repo.fetch()

    expected_refs = [
        'refs/heads/master',
        'refs/heads/fork1',
        'refs/heads/fork2',
        'refs/tags/initial_commit',
        'refs/tags/list_of_refs',
        # 'refs/sym_alias_fork1',
        # 'refs/direct_README',
    ]

    bak_repo.update_refs()
    after_one_refs = [ref for ref in bak_repo.cloned_repo.references
                      if ref.startswith('refs/heads/') or ref.startswith('refs/tags/')]
    assert sorted(after_one_refs) == sorted(expected_refs)

    bak_repo.update_refs()
    after_two_refs = [ref for ref in bak_repo.cloned_repo.references
                      if ref.startswith('refs/heads/') or ref.startswith('refs/tags/')]
    assert sorted(after_two_refs) == sorted(expected_refs)


def test_update_fastforward(simple_git_repo, tmp_path):
    '''Check that a fast-forwarded ref is updated.'''

    source_repo = GitRepo(simple_git_repo.path, 'simple-repo', 'simple-repo')
    bak_repo = LocalBackup(source_repo, tmp_path / 'local_backups')
    bak_repo.clone()
    bak_repo.fetch()
    bak_repo.update_refs()

    old_master = bak_repo.cloned_repo.lookup_reference('refs/heads/master')

    check_call(['git', 'checkout', 'master'], cwd=simple_git_repo.workdir)
    with Path(simple_git_repo.workdir).joinpath('README.md').open('w') as f:
        f.write(dedent('''\
            # Edited README #

            This file README.md is being replaced to test the fetch of
            an updated reference.
        '''))
    check_call(['git', 'commit', '-am', 'Replace README.md'],
               cwd=simple_git_repo.workdir)

    bak_repo.fetch()
    bak_repo.update_refs()
    new_master = bak_repo.cloned_repo.lookup_reference('refs/heads/master')
    new_master_parent = bak_repo.cloned_repo.revparse_single(
        'refs/heads/master^'
    )

    assert old_master.target != new_master.target
    assert old_master.target == new_master_parent.oid
    assert str(new_master.target) == check_output(
        ['git', 'log', '--pretty=format:%H', '-n', '1', 'master'],
        cwd=simple_git_repo.workdir, text=True
    ).strip()


def test_update_nonff(simple_git_repo, tmp_path):
    '''Check that a fast-forwarded ref is updated.'''

    source_repo = GitRepo(simple_git_repo.path, 'simple-repo', 'simple-repo')
    bak_repo = LocalBackup(source_repo, tmp_path / 'local_backups')
    bak_repo.clone()
    bak_repo.fetch()
    bak_repo.update_refs()

    old_master = bak_repo.cloned_repo.lookup_reference('refs/heads/master')

    check_call(['git', 'checkout', 'master'], cwd=simple_git_repo.workdir)
    with Path(simple_git_repo.workdir).joinpath('README.md').open('w') as f:
        f.write(dedent('''\
            # Edited README #

            This file README.md is being replaced to test the fetch of
            an updated reference.
        '''))
    check_call(['git', 'commit', '--amend', '-am', 'Replace README.md'],
               cwd=simple_git_repo.workdir)

    nonffcb_args = []
    nonffcb_kwargs = {}

    def nonff_callback(*args, **kwargs):
        nonlocal nonffcb_args, nonffcb_kwargs
        nonffcb_args = args
        nonffcb_kwargs = kwargs
        return True

    bak_repo.fetch()
    bak_repo.update_refs(nonff_callback=nonff_callback)
    new_master = bak_repo.cloned_repo.lookup_reference('refs/heads/master')
    new_master_parent = bak_repo.cloned_repo.revparse_single(
        'refs/heads/master^'
    )

    assert old_master.target != new_master.target
    assert old_master.target != new_master_parent.oid
    assert str(new_master.target) == check_output(
        ['git', 'log', '--pretty=format:%H', '-n', '1', 'master'],
        cwd=simple_git_repo.workdir, text=True
    ).strip()

    assert nonffcb_args[0].target == new_master.target
    assert nonffcb_args[1].target == new_master.target  # After update
    assert bak_repo.cloned_repo.lookup_reference(nonffcb_args[2]).target == \
        old_master.target
    assert nonffcb_args[2].startswith('refs/heads/master_replaced_')
