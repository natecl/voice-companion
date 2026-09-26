"""Optional pinned English passage ranker. Scores order evidence, never verify facts."""
import math
from admission import Rejected

MODEL = 'Xenova/ms-marco-MiniLM-L-6-v2'
REVISION = 'a09144355adeed5f58c8ed011d209bf8ee5a1fec'


class LocalReranker:
    contract = f'{MODEL}:{REVISION}:fastembed-0.8.1'

    def __init__(self, cache):
        from huggingface_hub import snapshot_download
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        path = snapshot_download(MODEL, revision=REVISION, cache_dir=str(cache),
                                 allow_patterns=['onnx/model.onnx', 'config.json', 'tokenizer.json',
                                                 'tokenizer_config.json', 'special_tokens_map.json'])
        self.model = TextCrossEncoder(MODEL, specific_model_path=path, threads=2,
                                      providers=['CPUExecutionProvider'])

    def rank(self, query, texts):
        if not isinstance(query, str) or not query.strip() or len(query) > 1000 or len(texts) > 50:
            raise Rejected('invalid_ranking_input')
        # Reject rather than silently truncate evidence. Context windows come from the harness.
        if any(not isinstance(text, str) or self.model.token_count([(query, text)]) > 480 for text in texts):
            raise Rejected('ranking_context_too_large')
        scores = list(self.model.rerank(query, texts, batch_size=8)) if texts else []
        if len(scores) != len(texts) or not all(math.isfinite(score) for score in scores):
            raise Rejected('invalid_ranking_result')
        return sorted(range(len(texts)), key=lambda index: (-scores[index], index)), scores
