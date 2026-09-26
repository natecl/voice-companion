"""Offline historical probes, not acceptance tests for the repaired system.

Run against a checkout using --backend. No provider client is constructed;
network access and budget reservations fail closed. All writes use temporary DBs.
"""
import argparse
import asyncio
import contextlib
import inspect
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from unittest.mock import patch

FIXTURE = Path(__file__).parent / 'fixtures/memory_rework/maya_correction.json'


def source(session, text):
    return dict(session_id=session, revision=1, captured_at=100., timezone='UTC',
                completed=True, passages=[dict(id='p1', start=0., duration=2., text=text, speakers=[])])


def candidate(text):
    return dict(text=text, subject='user', kind='fact', basis='stated', passages=['p1'],
                judgment_version='fixture-v1', valid_from=100.)


async def probe(backend):
    sys.path.insert(0, str(backend))
    from memory_store import MemoryStore
    from memory_writer import MemoryWriter, MemoryWorker, select_claims, subject_key
    import memory_recall

    results = []
    has_profile_recall = 'personal_recall' in inspect.signature(MemoryStore).parameters
    with tempfile.TemporaryDirectory() as directory:
        now = [200.]
        options = dict(personal_learning=True)
        if has_profile_recall:
            options['personal_recall'] = True
        store = MemoryStore(Path(directory)/'memory.sqlite', clock=lambda: now[0], **options)
        owner = store.owner_for('synthetic-credential')

        def add(session, text):
            data = source(session, text)
            data.update(origin='personal_text', captured_at=now[0])
            store.put_source(owner, data)
            store.commit_claims(store.claim_job(owner), [candidate(text)])

        add('old-bird', 'The user enjoys sketching sparrows.')
        for index in range(9):
            now[0] += 1
            add(f'new-{index}', f'The user owns household item {index}.')
        if has_profile_recall:
            items = memory_recall.combined_shortlist(store.recall_snapshot(owner), {
                'question': 'Suggest a relaxing creative activity for the weekend.',
                'passages': [{'text': 'A break.'}]})
            assert not any(item['session_id'] == 'old-bird' for item in items)
            results.append(dict(case='paraphrase_candidate_loss', observed='relevant_old_fact_missing', candidates=len(items)))
        else:
            results.append(dict(case='paraphrase_candidate_loss', observed='not_available_on_verified_main'))
        for index in range(9, 51):
            now[0] += 1
            add(f'new-{index}', f'The user owns household item {index}.')
        profile = store.profile(owner)
        assert len(profile) == 50 and not any('sparrows' in item['text'] for item in profile)
        results.append(dict(case='correction_pool_truncation', observed='older_target_missing', pool=len(profile)))

    with tempfile.TemporaryDirectory() as directory:
        store = MemoryStore(Path(directory)/'memory.sqlite')
        owner = store.owner_for('synthetic-credential')
        assert store.put_source(owner, source('large', 'A conversation sentence. '*900))['status'] == 'stored'
        store.put_source(owner, source('following', 'The appointment is Tuesday.'))

        class NoBudget:
            def reserve(self, *args):
                raise AssertionError('Offline probes must not reserve provider budget')

        class Admission:
            def active_credentials(self):
                return ['synthetic-credential']

        with contextlib.redirect_stdout(io.StringIO()):
            await asyncio.wait_for(MemoryWorker(MemoryWriter(store, None, NoBudget()), Admission()).run(), 2)
        with store.connect() as db:
            jobs = [dict(row) for row in db.execute('SELECT session,state,error FROM job ORDER BY rowid')]
        assert jobs[0]['error'] == 'memory_extraction_too_large' and jobs[1]['state'] == 'queued'
        results.append(dict(case='oversized_source_stops_worker', observed='following_job_stalled', jobs=jobs))

    evidence = json.loads(FIXTURE.read_text())
    claims, _ = select_claims(evidence['source'], evidence['cached']['extract']['data']['memories'],
                             evidence['cached']['judge']['data']['answers'], [[evidence['old']]], ['supported'])
    assert claims[0]['relation'] == 'new'
    assert claims[0]['subject'] != evidence['old']['subject']
    results.append(dict(case='uncertain_correction', observed='new_claim_different_subject'))
    assert subject_key('Maya') == subject_key(' maya ')
    results.append(dict(case='same_name_key', observed='identical_key_without_identity_evidence'))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    backend = args.backend.resolve()
    commit = subprocess.check_output(['git', '-C', str(backend), 'rev-parse', 'HEAD'], text=True).strip()
    # Patch actual socket connection paths, not a fake provider response.
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')), \
         patch.object(socket.socket, 'connect_ex', side_effect=AssertionError('Network forbidden')), \
         patch.object(socket, 'create_connection', side_effect=AssertionError('Network forbidden')):
        results = asyncio.run(probe(backend))
    print(json.dumps(dict(backend_commit=commit, provider_calls=0,
                         interpretation='Historical failures reproduced; not fixed acceptance.', results=results), indent=2))


if __name__ == '__main__':
    main()
