"""Opt-in indexed recall compatible with the existing Ask streaming boundary."""
import asyncio
import json
import re
from admission import Rejected
from memory_context import valid
from memory_hybrid import retrieve
from memory_indexing import coverage
from memory_ranking import MemoryRanker


def memory_disabled(data):
    if data.get('memory') is False:return True
    text=data['question'].strip().casefold().replace('’', "'")
    return bool(re.match(r"^(?:please )?(?:(?:do not|don't) (?:use|retrieve|look up|refer to) (?:my |any |the )?(?:memory|past (?:notes|conversations|recordings))\b|only use (?:this|the current) (?:recording|transcript|conversation)\b)",text))


class IndexedMemoryRecall:
    def __init__(self,store,models,budget,embedder=None,*,multi_source=False):
        self.store,self.embedder=store,embedder
        self.ranker=MemoryRanker(store,models,budget,multi_source=multi_source)

    async def prepare(self,credential,data):
        # Explicit opt-out comes before owner lookup, candidate retrieval and inference.
        if memory_disabled(data):
            return dict(status='disabled',sources=[],contract='indexed-v1',packet=None)
        owner=await asyncio.to_thread(self.store.owner_for,credential)
        found=await asyncio.to_thread(retrieve,self.store,owner,data['question'],embedder=self.embedder,
                                      exclude_session=data.get('session_id'),limit=12)
        result=await self.ranker.prepare(owner,data['question'],found['packet'])
        packet=result['packet']
        sources=[dict(id=f'm{i}',**item) for i,item in enumerate(packet['items'],1)]
        if len(sources)>8:raise Rejected('related_context_too_large')
        state=await asyncio.to_thread(coverage,self.store,owner,self.embedder.contract) if self.embedder else {}
        partial=self.embedder is None or any(value for key,value in state.items() if key!='done')
        status=result['status']
        if status=='context_limited':raise Rejected('recall_too_large')
        proposed={**data,'past_sources':sources,'memory_status':status,'memory_contract':'indexed-v1',
                  'memory_coverage':'partial' if partial else 'indexed'}
        from ask import input_fits
        if not input_fits(proposed):raise Rejected('recall_too_large')
        return dict(status=status,sources=sources,contract='indexed-v1',packet=packet,
                    coverage=proposed['memory_coverage'])

    async def validate(self,manifest):
        packet=manifest['packet']
        if packet is not None and not await asyncio.to_thread(valid,self.store,packet['owner'],packet):
            raise Rejected('memory_context_changed')
