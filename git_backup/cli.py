import logging
import logging.config
import sys
from pathlib import Path

import click

from .backup import LocalBackup
from .config import load_config, setup_logging
from .sources import GitSource


logger = logging.getLogger(__name__)


@click.command()
@click.option('-c', '--config', default='config.yml', metavar='PATH',
              help='Path to the configuration file.')
@click.option('-v', '--verbose', count=True,
              help='Increase verbosity at each repetition.')
def main(config, verbose):
    cfg = load_config(config)
    setup_logging(cfg, verbose)
    logger.info('Configuration loaded from %r', config)

    base_dir = Path(cfg['clone_base_dir']).expanduser()
    logger.info('Using %r as base directory for local clones', str(base_dir))

    sources = {s['name']: GitSource.from_dict(s) for s in cfg['sources']}

    for label, source in sources.items():
        logger.info("Backing up repos from source %r", label)
        subdir = base_dir / label
        callbacks = source.get_callbacks()
        for repo in source.get_repos():
            logger.info("Backing up repo %r", repo.full_name)
            local_backup = LocalBackup(repo, subdir, callbacks)
            local_backup.clone()
            local_backup.fetch()
            local_backup.update_refs()
    return 0


if __name__ == '__main__':
    sys.exit(main())  # pylint: disable=no-value-for-parameter
