"""Authenticated, bounded source synchronization; no extraction or paid calls."""
import asyncio
import json
from admission import Rejected


class MemoryService:
    def __init__(self, admission, store, *, generate_notes=False):
        self.admission, self.store = admission, store
        self.generate_notes = generate_notes
        self.slots = asyncio.Semaphore(2)

    async def handle(self, socket):
        try:
            async with asyncio.timeout(8):
                async with self.slots:
                    raw = await socket.recv()
                    if not isinstance(raw, str) or len(raw.encode()) > 63000:
                        raise Rejected('invalid_memory_request')
                    try:
                        data = json.loads(raw)
                    except ValueError:
                        raise Rejected('invalid_memory_request') from None
                    if not isinstance(data, dict) or data.get('version') not in (1, 2) or type(data.get('version')) is not int:
                        raise Rejected('invalid_memory_request')
                    token = socket.request.headers.get('Authorization', '').removeprefix('Bearer ')
                    credential = self.admission.authorized(token)
                    # Ownership derives from authenticated credentials, never the supplied owner.
                    owner = await asyncio.to_thread(self.store.owner_for, credential)
                    if data.get('owner') != owner:
                        raise Rejected('memory_owner_mismatch')
                    operation = data.get('operation')
                    if operation == 'upsert' and set(data) == {'version', 'owner', 'operation', 'source'}:
                        if not isinstance(data['source'], dict):
                            raise Rejected('invalid_memory_request')
                        if data['version'] == 1 and 'origin' in data['source']:
                            raise Rejected('invalid_memory_request')
                        # Recheck after async owner lookup, before persistence dispatch.
                        self.admission.authorized(token)
                        result = await asyncio.to_thread(self.store.put_source, owner, data['source'], generate_notes=self.generate_notes)
                    elif operation == 'delete' and set(data) == {'version', 'owner', 'operation', 'session_id'}:
                        self.admission.authorized(token)
                        result = await asyncio.to_thread(self.store.delete_source, owner, data['session_id'])
                    else:
                        raise Rejected('invalid_memory_request')
                    await socket.send(json.dumps({'type': 'memory_ack', 'version': data['version'], 'owner': owner, **result}))
        except Exception as error:
            reason = str(error) if isinstance(error, Rejected) else 'memory_unavailable'
            try:
                await socket.send(json.dumps({'type': 'error', 'message': reason}))
            except Exception:
                pass  # Client may be gone; idempotent replay resolves an uncertain acknowledgment.
        finally:
            await socket.close()
