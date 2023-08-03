import os
from datetime import datetime
from flomoDatabase import FlomoDatabase
from readwise import Readwise
from logger import loguru_logger
# os.environ['NOTION_INTEGRATION_TOKEN'] = "secret_sbEgXxZiwDwkTvoRW80il0CUhOL4Ns1eWr25y1temRJ"
# os.environ['NOTION_DATABASE_ID'] = "f323f02767944b14ab4fb33f9eb50d76"
# os.environ['READWISE_ACCESS_TOKEN'] = "71FYCeD5zI0CHATsKofjiHkcRItkMfypRECZRHHZeDXlmuW6se"
NOTION_INTEGRATION_TOKEN = os.environ['NOTION_INTEGRATION_TOKEN']
NOTION_DATABASE_ID = os.environ['NOTION_DATABASE_ID']
READWISE_ACCESS_TOKEN = os.environ['READWISE_ACCESS_TOKEN']

# Only sync new memos by managing a last sync time
# Both Github Actions and Notion API are in UTC time zone
last_sync_time_file = 'last_sync_time.txt'
# Save all logs to a same file
logger = loguru_logger('flomo2readwise')


def get_last_sync_time():
    if not os.path.exists(last_sync_time_file):
        return None
    with open(last_sync_time_file, 'r') as f:
        return datetime.fromisoformat(f.read().replace("\n", ""))


def update_last_sync_time(sync_time=None):
    if not sync_time:
        update_time = datetime.now()  # UTC time on Github Actions
    else:
        dt_obj = datetime.strptime(
            '2023-07-31T14:44:00.000Z', '%Y-%m-%dT%H:%M:%S.%fZ')
        update_time = dt_obj.strftime('%Y-%m-%dT%H:%M:%S.%f')
    with open(last_sync_time_file, 'w') as f:
        f.write(str(update_time))
    return update_time


readwise = Readwise(READWISE_ACCESS_TOKEN, logger)


def sync_callback(flomo_memos):
    global readwise
    last_hl = readwise.create_highlights_from_memos(flomo_memos)
    update_time = update_last_sync_time(last_hl["highlighted_at"])
    logger.log('Update last sync time:', update_time)


def sync_flomo_to_readwise():
    last_sync_time = get_last_sync_time()
    if last_sync_time:
        logger.log('Last sync time:', last_sync_time)
    else:
        logger.log('First sync')

    # Fetch flomo memos
    flomo_database = FlomoDatabase(
        NOTION_INTEGRATION_TOKEN, NOTION_DATABASE_ID, logger)
    flomo_memos = flomo_database.fetch_flomo_memos(
        sync_callback,
        last_sync_time=last_sync_time)
    logger.log('Number of flomo memos to sync:', len(flomo_memos))

    logger.log('Finished')
    logger.log('')


if __name__ == '__main__':
    sync_flomo_to_readwise()
