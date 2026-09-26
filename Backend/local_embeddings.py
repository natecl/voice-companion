"""Optional, pinned CPU embedding adapter. No transcript is sent to a model API."""
from admission import Rejected

MODEL='BAAI/bge-small-en-v1.5'
REVISION='aa8f8b060edb00e03bfdd08813a2949946c8ba55'
CONTRACT=f'{MODEL}:{REVISION}:fastembed-0.8.1:windows-v1'


class LocalEmbeddings:
    contract=CONTRACT
    dimensions=384

    def __init__(self,cache):
        from fastembed import TextEmbedding
        from huggingface_hub import snapshot_download
        path=snapshot_download('Qdrant/bge-small-en-v1.5-onnx-Q',revision=REVISION,cache_dir=str(cache),
            allow_patterns=['model_optimized.onnx','tokenizer.json','tokenizer_config.json','config.json','special_tokens_map.json'])
        self.model=TextEmbedding(MODEL,specific_model_path=path,threads=2,providers=['CPUExecutionProvider'])

    def windows(self,text):
        start=0
        while start<len(text):
            end=min(len(text),start+1600)
            # token_count truncates at 512; a <=400 test still detects every oversized window.
            if self.model.token_count(text[start:end])>400:
                low,high=start+1,end
                while low<high:
                    middle=(low+high+1)//2
                    if self.model.token_count(text[start:middle])<=400:low=middle
                    else:high=middle-1
                end=low
            if end<len(text):
                boundary=max(text.rfind('. ',start+(end-start)//2,end),text.rfind('\n',start+(end-start)//2,end))
                if boundary!=-1:end=boundary+1
            yield start,end,text[start:end]
            if end==len(text):break
            start=max(start+1,end-80)

    def passages(self,texts):
        return list(self.model.passage_embed(texts,batch_size=32))

    def query(self,text):
        if self.model.token_count(text)>400:raise Rejected('embedding_query_too_large')
        return next(self.model.query_embed(text))
