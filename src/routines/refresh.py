'''
    ES Index Update
    @ 1 am every day
'''

import asyncio

import aiocron
from tornado.ioloop import IOLoop

from api.es import ESQuery


@aiocron.crontab('0 1 * * *')
async def refresh():
    '''
        Refresh APIs.
    '''

    def sync_func():

        esq = ESQuery()
        esq.refresh_all(dryrun=False)

    await IOLoop.current().run_in_executor(None, sync_func)

if __name__ == '__main__':

    asyncio.run(refresh.func())
