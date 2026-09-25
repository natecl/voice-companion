"""Approved founder trial policy; shared by the service and administrative CLI."""
import os
from pathlib import Path
from admission import Admission


def open_ledger():
    directory = Path(os.environ['VOICE_DATA_DIR'])
    # Hosting must mount this directory before startup. Never recreate a missing disk.
    if not directory.is_dir():
        raise ValueError('Persistent data directory is unavailable')
    return Admission(directory / 'usage.sqlite', total_microusd=5_000_000,
                     limits={'stt': (2_000_000, 20_000, 6)})
