"""
    SmartAPI Web Server Entry Point

        > python index.py

"""

import os.path

from biothings.web.index_base import main
from biothings.web.settings import BiothingESWebSettings

import config

WEB_SETTINGS = BiothingESWebSettings(config=config)


if __name__ == '__main__':
    (SRC_PATH, _) = os.path.split(os.path.abspath(__file__))
    STATIC_PATH = os.path.join(SRC_PATH, 'web', 'static')
    main(WEB_SETTINGS.generate_app_list(),
         app_settings={"cookie_secret": config.COOKIE_SECRET},
         debug_settings={"static_path": STATIC_PATH},
         use_curl=True)
