#!/usr/bin/env python3
"""Seed fictional content for two real localhost QA identities and check isolation.

Leaves owner-scoped fixtures for subsequent native UI QA. Never use with hosted
or personal data. Temporary request credentials are revoked in finally.
"""

import argparse
import asyncio, json, ssl, sys, time, uuid, subprocess
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Backend"))
from admission import Admission
from memory_store import MemoryStore
from companion_chat import CompanionChat
from recording_notes import RecordingNotes
from test_memory import source
from websockets.asyncio.client import connect

parser = argparse.ArgumentParser()
parser.add_argument("--directory", type=Path, required=True)
parser.add_argument("--simulator", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
P = args.directory
endpoint = (P / "endpoint.txt").read_text().strip()
assert urlparse(endpoint).hostname == "127.0.0.1"
ctx = ssl.create_default_context(cafile=str(P / "cert.pem"))
store = MemoryStore(P / "memory.sqlite")
a = Admission(
    P / "usage.sqlite",
    total_microusd=1,
    limits={"stt": (100, 20, 5), "ask": (100, 20, 5)},
)
with store.connect() as db:
    identities = dict(db.execute("select issuer,owner from account_identity"))
assert len(identities) == 2
manifest = P / "isolation-fixtures.json"
assert not manifest.exists(), "Preserve existing fixtures; inspect before rerunning"
fixtures = {}
for provider, issuer in [
    ("google", "https://accounts.google.com"),
    ("apple", "https://appleid.apple.com"),
]:
    owner = identities[issuer]
    sid = str(uuid.uuid4()).upper()
    marker = (
        "Fictional "
        + provider.title()
        + " "
        + ("compass" if provider == "google" else "lantern")
    )
    text = marker + " belongs only to this test account."
    fixtures[provider] = dict(
        owner=owner, session=sid, marker=marker, text=text, turn=str(uuid.uuid4())
    )
manifest.write_text(json.dumps(fixtures))
manifest.chmod(0o600)
for f in fixtures.values():
    store.put_source(f["owner"], source(f["session"], text=f["text"]), learn=False)
    n = RecordingNotes(store)
    n.enqueue(f["owner"], f["session"], 1)
    n.complete(
        n.claim(f["owner"], f["session"]),
        dict(
            title=f["marker"],
            overview=dict(text=f["text"], passages=["p1"]),
            sections=[
                dict(
                    heading="QA fixture", items=[dict(text=f["text"], passages=["p1"])]
                )
            ],
        ),
    )
    c = CompanionChat(store)
    c.start(f["owner"], f["turn"], "What is my fictional isolation marker?")
    c.complete(f["owner"], f["turn"], f["text"])
SIM = args.simulator
container = Path(
    subprocess.check_output(
        [
            "xcrun",
            "simctl",
            "get_app_container",
            SIM,
            "ai.voicecompanion.phone",
            "data",
        ],
        text=True,
    ).strip()
)
for f in fixtures.values():
    folder = (
        container
        / "Library/Application Support/VoiceCompanion/accounts"
        / f["owner"]
        / "sessions"
    )
    folder.mkdir(parents=True, exist_ok=True)
    session = dict(
        id=f["session"],
        createdAt=time.time() - 978307200,
        completed=True,
        memoryOwnerID=f["owner"],
        memoryTerminal=True,
        captureTimezone="UTC",
        transcript=dict(
            segments=[dict(start=0, duration=2, text=f["text"], words=[], isFinal=True)]
        ),
    )
    path = folder / (f["session"] + ".json")
    assert not path.exists()
    path.write_text(json.dumps(session))


async def run():
    credentials = []
    result = {}

    async def request(path, token, body):
        async with connect(
            endpoint.replace("/account", path),
            ssl=ctx,
            additional_headers={"Authorization": "Bearer " + token},
            open_timeout=5,
        ) as ws:
            await ws.send(json.dumps(body))
            return json.loads(await asyncio.wait_for(ws.recv(), 10))

    try:
        for provider, f in fixtures.items():
            other = fixtures["apple" if provider == "google" else "google"]
            with a.transaction():
                credential, token = a.enroll(lifetime_seconds=120)
                credentials.append(credential)
                store.owner_for(credential, existing_owner=f["owner"])
            own = await request(
                "/notes",
                token,
                dict(operation="read", session_id=f["session"], revision=1),
            )
            assert own["result"]["notes"]["title"] == f["marker"]
            alien = await request(
                "/notes",
                token,
                dict(operation="read", session_id=other["session"], revision=1),
            )
            assert alien == dict(type="error", message="source_unavailable")
            spoof = await request(
                "/memory",
                token,
                dict(
                    version=2,
                    owner=other["owner"],
                    operation="delete",
                    session_id=other["session"],
                ),
            )
            assert spoof == dict(type="error", message="memory_owner_mismatch")
            history = await request(
                "/companion", token, dict(operation="history", before=None)
            )
            raw = json.dumps(history)
            assert f["marker"] in raw and other["marker"] not in raw
            assert store.source(other["owner"], other["session"]) is not None
            result[provider] = dict(
                own_notes_visible=True,
                foreign_notes_rejected=True,
                spoofed_owner_delete_rejected=True,
                chat_history_isolated=True,
                other_source_preserved=True,
            )
        receipt = dict(
            scope="real enrolled local QA owners; fictional seeded content; synthetic request credentials",
            results=result,
            native_fixtures_prepared=True,
            paid_calls=0,
            limitations=[
                "Native account switching and notes cache behavior remain to be exercised",
                "No physical-device or hosted acceptance",
            ],
        )
        args.output.write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))
    finally:
        with a.transaction():
            for credential in credentials:
                a.revoke(credential)
        a.close()


asyncio.run(run())
