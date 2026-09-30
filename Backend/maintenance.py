"""Startup-only maintenance and shared exclusion for offline database operations."""
import asyncio
from contextlib import contextmanager
import fcntl
from http import HTTPStatus
import json
from pathlib import Path
from websockets.asyncio.server import serve


def enabled(env):
    value = env.get('VOICE_MAINTENANCE', '0')
    if value not in ('0', '1'):
        raise ValueError('Invalid maintenance flag')
    return value == '1'


@contextmanager
def database_lease(directory):
    """Normal hosted runtime and offline operators exclude each other.

    Only versions participating in this lock are covered. Verify the deployed
    version and maintenance health before an operator changes live databases.
    """
    with (Path(directory) / 'database.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def respond(connection, request):
    if request.path == '/health':
        response = connection.respond(HTTPStatus.OK, json.dumps({
            'state': 'maintenance', 'database_open': False, 'workers': 'stopped'}) + '\n')
        response.headers['Content-Type'] = 'application/json'
        return response
    response = connection.respond(HTTPStatus.SERVICE_UNAVAILABLE, 'Service is under maintenance\n')
    response.headers['Retry-After'] = '60'
    return response


async def run(directory, port, *, expiry_interval=None):
    from backup_retention import running
    # Share the service singleton lock; never acquire/open active databases.
    # The offline operator may hold database_lease while this health server runs.
    with (Path(directory) / 'service.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        async def reject(socket):
            await socket.close(1013, 'maintenance')
        async with running(directory, expiry_interval), serve(reject, '0.0.0.0', port, process_request=respond,
                         max_size=64000, max_queue=8, close_timeout=2, server_header=None):
            print('Maintenance service ready; active databases unopened; application workers stopped', flush=True)
            await asyncio.Future()
