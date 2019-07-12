'''
    Create an index and restore a backup file.
'''

import os
import logging

from api import es

# find in cwd

backup = None
for file in os.listdir("."):
    if file.endswith(".json") and file.startswith("smartapi_oas3"):
        logging.info(os.path.abspath(file))
        backup = file
        break

if backup:
    esq = es.ESQuery()
    esq.restore_all(backup, es.ES_INDEX_NAME)
else:
    logging.error('Cannot find a backup file.')
    exit(1)
