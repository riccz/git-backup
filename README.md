# git-backup #


# Known Issues & Limitations #

Libgit2 fails on non-commit refs that are not in `refs/tags/` (see
<https://github.com/libgit2/libgit2/issues/3595>). As a temporary workaround,
git-backup only fetches branches (`refs/heads/`) and tags (`refs/tags/`).


# TODO #

- [ ] Check for extra refs and warn?
- [ ] Docker image
- [ ] Package backups in bundles (no pygit, call git)
- [ ] Add snippets
- [ ] Add wikis
- [x] Separate pylint and mypy from pytest. See <https://jichu4n.com/posts/how-to-add-custom-build-steps-and-commands-to-setuppy/>
