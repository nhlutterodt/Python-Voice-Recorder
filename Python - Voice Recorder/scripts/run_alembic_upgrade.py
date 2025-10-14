"""Run Alembic `upgrade head` programmatically using the project's alembic.ini.

This helper is intended for development use so the DB schema is kept up to date
without requiring developers to remember alembic CLI usage.
"""
import os
import sys

from alembic.config import Config
from alembic import command

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, '..'))
ALEMBIC_INI = os.path.join(PROJECT_ROOT, 'alembic.ini')

def main():
    if not os.path.exists(ALEMBIC_INI):
        print('alembic.ini not found at', ALEMBIC_INI)
        sys.exit(1)

    cfg = Config(ALEMBIC_INI)
    # Ensure Alembic looks up scripts location relative to project root
    cfg.set_main_option('script_location', os.path.join(PROJECT_ROOT, 'alembic'))

    print('Running alembic upgrade head using', ALEMBIC_INI)
    command.upgrade(cfg, 'head')


if __name__ == '__main__':
    main()
