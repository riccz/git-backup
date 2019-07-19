import logging
from dataclasses import dataclass
from itertools import starmap
from typing import Dict, Iterable, Mapping, Optional, Type
from urllib.parse import urlparse

import github
import gitlab
import pygit2

logger = logging.getLogger(__name__)


class GitSource(type):
    '''Metaclass used to register and lookup all git source classes.'''

    _git_source_classes: Dict[str, Type] = {}

    def __new__(cls, name, bases, attrs, tag: str):
        '''Register every class using `tag` as lookup key.

        See `get_by_tag`.
        '''

        newcls = super().__new__(cls, name, bases, attrs)
        if tag in GitSource._git_source_classes:
            raise RuntimeError('GitSource tag {!r} is already used for {!r}'
                               .format(tag, GitSource._git_source_classes[tag]))
        GitSource._git_source_classes[tag] = newcls
        return newcls

    def __init__(cls, name, bases, attrs, tag: str):  # pylint: disable=unused-argument
        '''Override just to ignore the `tag` argument.'''
        super().__init__(name, bases, attrs)

    @classmethod
    def get_by_tag(mcs, tag: str, default: Optional[Type] = None) -> Optional[Type]:
        '''Lookup the GitSource-type registered class with `tag`.'''
        return GitSource._git_source_classes.get(tag, default)

    @classmethod
    def from_dict(mcs, d: Mapping):
        '''Try to create an instance of one of the registered classes using a dict of arguments.

        The dict must contain _exactly one_ key equal to one of the registered
        tags. The corresponding value must be a valid kwargs dict for the class
        associated to the tag.
        '''
        found_items = [(k, C) for k, C in GitSource._git_source_classes.items()
                       if k in d]
        if len(found_items) == 0:
            raise RuntimeError('The source spec {!r} has an unknown source type'
                               .format(d))
        elif len(found_items) > 1:
            raise RuntimeError('The source spec {!r} has multiple source types: {!r}'
                               .format(d, [k for k, _ in found_items]))
        else:
            k, C = found_items[0]
            args = d[k]
            return C(**args)


@dataclass(frozen=True)
class GitRepo:
    url: str
    full_name: str
    name: str


class PlainGitClient(metaclass=GitSource, tag='plain_git'):
    def __init__(self, repos: Mapping[str, str],
                 key_path: Optional[str] = None):
        self.key_path = key_path
        self.repos = list(starmap(lambda name, url: GitRepo(url=url,
                                                            full_name=name,
                                                            name=name),
                                  repos.items()))

    def get_repos(self) -> Iterable[GitRepo]:
        return iter(self.repos)

    def get_callbacks(self) -> pygit2.RemoteCallbacks:
        return PlainGitCallbacks(self.key_path)


class PlainGitCallbacks(pygit2.RemoteCallbacks):
    def __init__(self, key_path: Optional[str]):
        super().__init__()
        self.__key_path = key_path

    def credentials(self, url: str, username_from_url: Optional[str], allowed_types: int):  # pylint: disable=method-hidden
        if self.__key_path is None or not allowed_types & pygit2.credentials.GIT_CREDTYPE_SSH_KEY:
            return super().credentials(url, username_from_url, allowed_types)

        return pygit2.Keypair(username_from_url,
                              self.__key_path + '.pub',
                              self.__key_path,
                              '')


class GithubClient(metaclass=GitSource, tag='github'):
    def __init__(self, token: str):
        self.token = token
        self.client = github.Github(token)

    def get_repos(self) -> Iterable[GitRepo]:
        orig_repos = (self.client.get_user()
                      .get_repos(affiliation='owner,organization_member'))
        return map(lambda r: GitRepo(url=r.clone_url,
                                     full_name=r.full_name,
                                     name=r.name),
                   orig_repos)

    def get_callbacks(self) -> pygit2.RemoteCallbacks:
        return GithubCallbacks(self.client.get_user().login, self.token)


class GithubCallbacks(pygit2.RemoteCallbacks):
    def __init__(self, username: str, token: str):
        super().__init__()
        self.__username = username
        self.__token = token

    def credentials(self, url: str, username_from_url: Optional[str], allowed_types: int):  # pylint: disable=method-hidden
        if not allowed_types & pygit2.credentials.GIT_CREDTYPE_USERPASS_PLAINTEXT:
            return super().credentials(url, username_from_url, allowed_types)

        parsed_url = urlparse(url)
        if parsed_url.scheme != 'https' or parsed_url.netloc != 'github.com':
            logger.warning('Trying to use Github credentials on a non-github URL: %r',
                           url)
            return super().credentials(url, username_from_url, allowed_types)

        return pygit2.UserPass(self.__username, self.__token)


class GitlabClient(metaclass=GitSource, tag='gitlab'):
    def __init__(self, token: str):
        self.token = token
        self.client = gitlab.Gitlab('https://gitlab.com', private_token=token)
        self.client.auth()  # Needed to create `user`

    def get_repos(self) -> Iterable[GitRepo]:
        projs = self.client.projects.list(all=True, owned=True, simple=True)
        return map(lambda p: GitRepo(url=p.http_url_to_repo,
                                     full_name=p.path_with_namespace,
                                     name=p.path), projs)

    def get_callbacks(self) -> pygit2.RemoteCallbacks:
        return GitlabCallbacks(self.client.user.username, self.token)


class GitlabCallbacks(pygit2.RemoteCallbacks):
    def __init__(self, username: str, token: str):
        super().__init__()
        self.__username = username
        self.__token = token

    def credentials(self, url: str, username_from_url: Optional[str], allowed_types: int):  # pylint: disable=method-hidden
        if not allowed_types & pygit2.credentials.GIT_CREDTYPE_USERPASS_PLAINTEXT:
            return super().credentials(url, username_from_url, allowed_types)

        parsed_url = urlparse(url)
        if parsed_url.scheme != 'https' or parsed_url.netloc != 'gitlab.com':
            logger.warning('Trying to use Gitlab credentials on a non-gitlab URL: %r',
                           url)
            return super().credentials(url, username_from_url, allowed_types)

        return pygit2.UserPass(self.__username, self.__token)
