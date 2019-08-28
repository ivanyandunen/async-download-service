from aiohttp import web
import aiofiles
import asyncio
import os.path
import logging
import argparse
from functools import partial


def get_parser_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-l', '--logging',
        default=False,
        action='store_true',
        help='Enable logging.'
    )
    parser.add_argument(
        '-d', '--delay',
        type=float,
        help='Enable delay before downloading.'
    )
    parser.add_argument(
        '-f', '--folder',
        type=str,
        default='test_photos',
        help="Path to photo directory."
    )
    return parser.parse_args()


async def archivate(delay, folder, request):
    path_to_files = os.path.join(folder, request.match_info['archive_hash'])
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'
    await response.prepare(request)

    if not os.path.exists(path_to_files):
        raise web.HTTPNotFound(text="Archive doesn't exist or deleted")

    process = await asyncio.create_subprocess_shell(f'zip -rj - {path_to_files}', stdout=asyncio.subprocess.PIPE)
    try:
        while True:
            archive_chunk, _ = await process.communicate()

            if delay:
                await asyncio.sleep(delay)

            logging.info('Sending archive chunk')

            if not archive_chunk:
                break
            else:
                await response.write(archive_chunk)

    except asyncio.CancelledError:
        logging.info('Download was interrupted')
        process.kill()
        raise

    finally:
        response.force_close()
        return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    args = get_parser_args()
    params = partial(archivate, args.delay, args.folder)

    if args.logging:
        logging.basicConfig(level=logging.INFO)

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', params)
    ])
    web.run_app(app)
