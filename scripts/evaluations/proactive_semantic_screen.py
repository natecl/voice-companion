"""Three predeclared Luna negatives through real retrieval and durable service.

Default is offline exact-request replay. --live permits one call per new case;
the operator's existing separate $0.25 / 12-attempt ledger remains authoritative.
No fallback from replay to paid inference and no automatic retry.
"""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import tempfile

from companion_chat import CompanionChat
from memory_store import MemoryStore
from proactive_context import prepare
from proactive_service import ProactiveService
from proactive_replay import recording

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / 'Backend/fixtures/proactive/semantic-cases.json'


class Models:
    def __init__(self, row, output, rows, live):
        self.row, self.output, self.rows, self.live = row, output, rows, live
        self.used = 0
        self.failure = None

    async def extract(self, request):
        self.used += 1
        try:
            if self.used != 1:
                raise AssertionError('One call per case; no retries')
            if self.live:
                payload = dict(id=self.row['case'] + ':llm:draft', request=request)
                process = await asyncio.to_thread(subprocess.run, [
                    'ssh', '-i', '/Users/n.chinlue/.ssh/voice_companion_render',
                    '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    'srv-daqtfs7lot8c73dleuug@ssh.virginia.render.com',
                    'python3 /tmp/proactive-provider-20260928.py'],
                    input=json.dumps(payload) + '\n', text=True, capture_output=True, timeout=25)
                if process.returncode:
                    raise RuntimeError('Operator transport failed; inspect receipt, do not retry')
                saved = json.loads(process.stdout)
                self.row['calls'].append(saved)
                self.output.write_text(json.dumps(self.rows, indent=2))
            else:
                saved = self.row['calls'][0]
            if 'error' in saved:
                raise RuntimeError('Provider attempt failed; no retry: ' + saved['error'])
            if saved['request'] != request:
                raise AssertionError('Unmatched request; no paid fallback')
            raw = saved['raw']
            if raw.get('status') != 'completed':
                raise AssertionError('Incomplete response; no retry')
            content = ''.join(c['text'] for o in raw['output'] if o['type'] == 'message'
                              for c in o['content'] if c['type'] == 'output_text')
            return dict(data=json.loads(content), usage=raw['usage'])
        except BaseException as error:
            self.failure = error
            raise


class OperatorBudget:
    """The remote transport reserves real spend; enforce one local call as well."""
    def __init__(self):
        self.reserved = False

    def reserve(self, key, model):
        if self.reserved or model != 'gpt-6-luna':
            raise AssertionError('Unexpected additional call')
        self.reserved = True

    def finish(self, *args):
        pass


async def run(output, live=False):
    cases = json.loads(CASES.read_text())
    if live and output.exists():
        raise RuntimeError('Output already exists; use offline replay, never implicit retry')
    rows = [] if live else json.loads(output.read_text())
    if not live:
        assert [r['case'] for r in rows] == [c['id'] for c in cases]
    reports = []
    for index, case in enumerate(cases):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'memory.sqlite'
            store = MemoryStore(path, clock=lambda: 300.)
            owner = store.owner_for('semantic-screen')
            store.put_source(owner, recording('prior', case['past']))
            current = recording('capture', case['live'], completed=False)
            context = prepare(store, owner, current)
            # Every case must actually supply evidence to the model.
            assert context and len(context['state']['sources']) == 1, case['id']
            assert context['state']['sources'][0]['text'] == case['past']
            if live:
                row = dict(case=case['id'], expected=case['expected'], rubric=case['rubric'],
                           state=context['state'], calls=[])
                rows.append(row)
                output.write_text(json.dumps(rows, indent=2))
            else:
                row = rows[index]
                assert row['state'] == context['state']
            model = Models(row, output, rows, live)
            service = ProactiveService(store, model, OperatorBudget())
            result = await service.evaluate(owner, current, lambda: True)
            if live:
                row['result'] = result
                output.write_text(json.dumps(rows, indent=2))
            else:
                assert result == row['result']
            if model.failure:
                raise model.failure
            assert model.used == 1
            # Preserve failed output before asserting acceptance; no prompt tuning here.
            assert result['type'] == case['expected'], (case['id'], result)
            assert CompanionChat(MemoryStore(path)).page(owner)['turns'] == []
            again = await service.evaluate(owner, current, lambda: True)
            assert again == dict(type='existing', state='silence', turn=None)
            assert model.used == 1
            reports.append(dict(case=case['id'], supplied_sources=1,
                                result=result['type'], persisted_messages=0,
                                repeated_attempt_suppressed=True))
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.output, args.live)), indent=2))
