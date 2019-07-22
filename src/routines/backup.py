'''
    ES Index Backup
    @ 12 am every day
'''

import asyncio
import logging

import aiocron
from botocore.exceptions import ClientError
from tornado.ioloop import IOLoop

from api.es import ESQuery


@aiocron.crontab('0 0 * * *')
async def backup():
    '''
        Backup es index to s3 or locally.
    '''

    def sync_func():

        esq = ESQuery()

        try:
            esq.backup_all(aws_s3_bucket='smartapi')

        except ClientError:

            logging.error((
                "Backup to s3 failed. "
                "Backing up locally instead."))

            esq.backup_all()

    await IOLoop.current().run_in_executor(None, sync_func)

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)
    asyncio.run(backup.func())
