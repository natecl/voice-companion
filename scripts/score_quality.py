"""Score synthetic references against output reduced by the production Swift model."""
import argparse
import itertools
import json
from pathlib import Path
import re
import subprocess

def tokens(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text.lower())

def align(reference, actual):
    rows, cols = len(reference), len(actual)
    cost = [[0] * (cols + 1) for _ in range(rows + 1)]
    for i in range(rows + 1): cost[i][0] = i
    for j in range(cols + 1): cost[0][j] = j
    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            cost[i][j] = min(cost[i-1][j-1] + (reference[i-1] != actual[j-1]),
                             cost[i-1][j] + 1, cost[i][j-1] + 1)
    pairs = []
    i, j = rows, cols
    counts = {'substitutions': 0, 'deletions': 0, 'insertions': 0}
    while i or j:
        if i and j and cost[i][j] == cost[i-1][j-1] + (reference[i-1] != actual[j-1]):
            if reference[i-1] == actual[j-1]: pairs.append((i-1, j-1))
            else: counts['substitutions'] += 1
            i -= 1; j -= 1
        elif i and cost[i][j] == cost[i-1][j] + 1:
            counts['deletions'] += 1; i -= 1
        else:
            counts['insertions'] += 1; j -= 1
    return counts, pairs

def score(folder, reducer):
    reference = json.loads((folder / 'reference.json').read_text())
    summary = json.loads((folder / 'summary.json').read_text())
    result = json.loads(subprocess.check_output([str(reducer), str(folder / 'events.json')]))
    (folder / 'reduced.json').write_text(json.dumps(result, indent=2))
    ref = [(word, turn['speaker']) for turn in reference['turns'] for word in tokens(turn['text'])]
    actual = [(word, item.get('speaker')) for segment in result['segments']
              for item in (segment['words'] or [{'text': segment['text']}]) for word in tokens(item['text'])]
    counts, pairs = align([word for word, _ in ref], [word for word, _ in actual])
    speakers = sorted({speaker for _, speaker in actual if speaker is not None})
    reference_speakers = sorted({speaker for _, speaker in ref})
    # Extra predicted clusters must map to a dummy, never to a duplicate reference identity.
    candidates = reference_speakers + [None] * max(0, len(speakers) - len(reference_speakers))
    best = len(pairs)
    for assignment in itertools.permutations(candidates, len(speakers)):
        mapping = dict(zip(speakers, assignment))
        best = min(best, sum(mapping.get(actual[j][1]) != ref[i][1] for i, j in pairs))
    first = summary.get('first_text_elapsed', 0) - summary.get('audio_started_elapsed', 0)
    final = summary.get('completion_elapsed', 0) - summary.get('audio_done_sent_elapsed', 0)
    wer = sum(counts.values()) / len(ref)
    mismatch = best / len(pairs) if pairs else 1
    complete_metadata = all(s['isFinal'] and s['words'] and all('start' in w and 'end' in w and w.get('speaker') is not None for w in s['words']) for s in result['segments']) and bool(result['segments'])
    report = {'fixture': reference['name'], 'reference_words': len(ref), 'actual_words': len(actual), **counts,
              'wer': wer, 'speaker_mismatch_on_matched_words': mismatch, 'word_match_coverage': len(pairs)/len(ref),
              'speaker_clusters': len(speakers), 'first_text_seconds': first, 'finalization_seconds': final,
              'audio_seconds': summary['audio_seconds'], 'complete_final_metadata': complete_metadata,
              'estimated_cost_usd': summary['estimated_audio_cost_usd'], 'billing_verified': False}
    report['screen_passed'] = summary['status'] == 'completed' and wer <= (.2 if reference['noise_db'] else .1) and mismatch <= .1 and 0 < first <= 3 and 0 <= final <= 3 and complete_metadata
    (folder / 'quality.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--reducer', type=Path, required=True)
    args = parser.parse_args()
    if not score(args.directory, args.reducer.resolve())['screen_passed']:
        raise SystemExit(1)
