# Starter capacity qualification

Founder decision: keep Render Starter (512 MiB / 0.5 CPU); no upgrade authorized. Local Linux x86_64 containers use Python 3.13.7, pinned semantic dependencies, `--memory 512m --memory-swap 512m --cpus .5 --network none`, and the prewarmed model read-only. No production load or paid API calls.

The original 32-window batch reached the entire 536,870,912-byte cgroup limit on 32 synthetic 1,500-character passages. It completed in about 34 seconds but lacked useful service headroom. This is a preserved failed capacity criterion, not evidence that all configurations require a larger plan.

The adapter now embeds one window at a time and serializes inference through a shared lock, released between windows. Model, revision, windows, normalization and vector contract stay unchanged. In the same limited container, 32 passages plus five foreground queries peaked at 368,345,088 bytes (351 MiB), completing in about 35 seconds; concurrent queries took 0.81–0.98 seconds. Indexing remains off the answer loop. This bounds activations without removing semantic retrieval.

The actual hosted-process test also passed in the limited container: new QA allowance, authenticated history, real offline indexing, and unchanged usage. Frozen hybrid retrieval checks passed at 10/100/1,000 sources, including late evidence, source spans, cache and deletion; maximum local query latency at 1,000 sources was 20.029 ms. CPU timings under local emulation are not a hosted latency guarantee. Actual Render startup/health/memory and physical acceptance remain gates.

Reproducible capacity command (dependencies installed in the test image):

```sh
docker run --rm --platform linux/amd64 --memory 512m --memory-swap 512m --cpus .5 --network none \
  -e HF_HUB_OFFLINE=1 -e PYTHONPATH=/app/Backend \
  -v "$PWD/Backend:/app/Backend:ro" -v "$PWD/work/embedding-models:/cache:ro" \
  voice-companion-capacity:local python Backend/evaluate_embedding_capacity.py --cache /cache
```

The probe requires less than 448 MiB peak and foreground embedding below two seconds, leaving room beneath the three-second recall deadline. It does not establish multi-user capacity or real microphone correctness. No hosting tier changes, source deletion or historical backfill are part of this optimization.
