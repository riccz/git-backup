import itertools
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import pygit2

from .sources import GitRepo


logger = logging.getLogger(__name__)


class LocalBackup:
    '''Backup a single remote git repo to a clone on the local filesystem.'''

    def __init__(self, repo: GitRepo,
                 base_dir: Union[str, Path],
                 callbacks: pygit2.RemoteCallbacks = None):
        self.dest_path = Path(base_dir) / (repo.full_name + ".git")
        assert '..' not in str(self.dest_path), \
            "Dest path {!r} contains '..'".format(self.dest_path)

        self.source_repo = repo
        self.callbacks = callbacks

        self.fetch_ref_prefix = 'refs/git-backup/origin/'
        self.fetch_prefix_filters = [
            'heads/',
            'tags/',
        ]

        self.cloned_repo: pygit2.Repository  # Initialize at `clone`

    def clone(self):
        '''Create the `cloned_repo` instance, doing the initial cloning if necessary.

        This method _must_ be called before doing anything else with the
        repository.
        '''

        if self.dest_path.exists():
            self._existing_clone()
        else:
            self._new_clone()

    def _new_clone(self):
        logger.debug('New clone of repo %r at %r', self.source_repo.full_name,
                     str(self.dest_path))
        self.cloned_repo = pygit2.clone_repository(self.source_repo.url,
                                                   str(self.dest_path),
                                                   bare=True,
                                                   callbacks=self.callbacks)

    def _existing_clone(self):
        logger.debug("Repo %r is already cloned at %r",
                     self.source_repo.full_name, str(self.dest_path))
        self.cloned_repo = pygit2.Repository(str(self.dest_path))

        if not any(r.name == 'origin' for r in self.cloned_repo.remotes):
            raise RuntimeError('Repo at {!r} does not have an \'origin\' remote'
                               .format(str(self.dest_path)))
        elif self.cloned_repo.remotes['origin'].url != self.source_repo.url:
            raise RuntimeError('\'origin\' remote at {!r} has URL {!r} instead of {!r}'
                               .format(str(self.dest_path),
                                       self.cloned_repo.remotes['origin'].url,
                                       self.source_repo.url))

    def _config_local_clone(self):
        '''Edit the local clone's configuration to fetch the correct references.

        This method is idempotent.
        '''

        config = self.cloned_repo.config
        fetch_lines = config.get_multivar('remote.origin.fetch')
        expected_refspecs = [f'+refs/{pf}*:{self.fetch_ref_prefix}{pf}*'
                             for pf in self.fetch_prefix_filters]
        if sorted(fetch_lines) != sorted(expected_refspecs):
            # Match all and replace with first refspec
            config.set_multivar('remote.origin.fetch', '',
                                expected_refspecs[0])
            # Match none, append other refspecs
            for r in expected_refspecs[1:]:
                config.set_multivar('remote.origin.fetch', '^$', r)

        self.cloned_repo.config['remote.origin.prune'] = False
        self.cloned_repo.config['remote.origin.tagOpt'] = '--no-tags'

    def fetch(self):
        '''Fetch _all_ the remote references into the temp directory `fetch_ref_prefix`.

        Non-fast-forward updates overwrite the local temp references.
        '''

        self._config_local_clone()
        remote = self.cloned_repo.remotes['origin']
        logger.info("Fetching %r from 'origin' (%r)",
                    self.source_repo.url, remote.url)
        remote.fetch(callbacks=self.callbacks)

    def _is_remote_ref(self, ref: str):
        return any(ref.startswith(prefix) for prefix in [self.fetch_ref_prefix])

    def update_refs(self, nonff_callback=None):
        '''Update all the local references with the fetched ones.

        Non-fast-forward updates cause a the old ref to be backed up with a
        unique suffix. See `_update_one_ref`.
        '''

        for ref_name in filter(self._is_remote_ref, self.cloned_repo.references):
            dest_name = ref_name.replace(self.fetch_ref_prefix, 'refs/', 1)
            self._update_one_ref(ref_name, dest_name, nonff_callback)

    def _update_one_ref(self, ref_name: str, dest_name: str, nonff_callback):
        ref = self.cloned_repo.lookup_reference(ref_name)
        try:
            dest = self.cloned_repo.lookup_reference(dest_name)
        except KeyError:
            logger.debug("Copy remote ref %r to new local ref %r",
                         ref.name, dest_name)
            self.cloned_repo.create_reference(dest_name, ref.target)
            return

        if type(ref.target) == type(dest.target) and ref.target == dest.target:
            logger.debug("Remote ref %r and local ref %r are already equal",
                         ref.name, dest.name)
            return

        both_oids = (isinstance(ref.target, pygit2.Oid) and
                     isinstance(dest.target, pygit2.Oid))
        if both_oids and self.cloned_repo.descendant_of(ref.target, dest.target):
            logger.info("Remote ref %r is a descendant of local ref %r",
                        ref.name, dest.name)
            dest.set_target(ref.target,
                            'git-backup: Fast-forward {!r} to {!r}'
                            .format(dest.name, ref.name))
            return

        dest_backup_name = self._backup_ref_name(dest.name)
        if nonff_callback is None:
            logger.warning("Remote ref %r and local ref %r have diverged",
                           ref.name, dest.name)
        elif not nonff_callback(ref, dest, dest_backup_name):
            logger.info('Skip remote ref %r', ref.name)
            return

        self.cloned_repo.create_reference(
            dest_backup_name, dest.target, force=False)
        logger.info("Backed up old ref to %r", dest_backup_name)
        dest.set_target(ref.target,
                        'git-backup: Replace {!r} with remote {!r}, backup old ref as {!r}'
                        .format(dest.name, ref.name, dest_backup_name))

    def _backup_ref_name(self, ref_name: str) -> str:
        timestr = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')
        backup_ref_name = "{}_replaced_{}".format(ref_name, timestr)
        alternate_names = (backup_ref_name + '_{:d}'.format(i)
                           for i in itertools.count(1))
        for r in itertools.chain([backup_ref_name], alternate_names):
            try:
                self.cloned_repo.lookup_reference(r)
            except KeyError:
                return r
        assert False, 'Infinite loop is not infinite'

    def backup(self, nonff_callback=None):
        '''Backup the remote repo to a local clone.

        nonff_callback -- A function to be called when a ref is about to be
        overwritten by a non-fast-forward update. Its signature must be:

            def nonff_callback(remote_ref: pygit2.Reference,
                               local_ref: pygit2.Reference,
                               backup_ref_name: str) -> bool:
                return True

        On ``True`` the local reference is backed up and overwritten, otherwise
        it is left unchanged.
        '''

        self.clone()
        self.fetch()
        self.update_refs(nonff_callback=nonff_callback)
