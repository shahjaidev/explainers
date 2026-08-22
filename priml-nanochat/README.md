# priml nanochat — a run, a ladder, and a fix

Working artifacts from running [`rekursiv-ai/priml`](https://github.com/rekursiv-ai/priml)'s
`nanochat` baseline end to end at `0e4eea4`.

## What is here

| File | What it is |
|---|---|
| `nanochat.html` | Explainer: the annotated `exp000().pprint()` tree, the ladder diffs, the run |
| `ISSUE.md` | Upstream bug report for the padded-eval `IndexError`, with the fix and its verification |
| `nanochat-ignore-padded-eval.patch` | The fix, against `0e4eea4` — `git apply` inside a priml checkout |
| `nanochat_cpu_experiments.py` | The CPU-scale study (`exp000`–`exp002`), recipe unchanged, size reduced |
| `make_shards.py`, `prepare_local.py` | Substitute-corpus builder and a driver for priml's own `prepare()` |
| `exp00*_result.txt` | The three runs' final lines, verbatim |

## The runs

Same recipe, same 300-second budget, run sequentially on an otherwise idle
4-core machine. Lower bits-per-byte is better.

| | steps | train loss | val bits/byte |
|---|---|---|---|
| `exp000` full attention | 91 | 4.9308 | 1.8897 |
| `exp001` windowed attention | 92 | 4.9040 | **1.8794** |
| `exp002` + value embeddings | 91 | 4.9176 | 1.8846 |

**These numbers do not decide anything.** The spread is ~0.01 bpb across three
runs at one seed each; nothing here separates the rungs from run-to-run
variance, and no seed replicates were taken. They are reported because the runs
happened, not because they answer the ladder's question.

Two reasons the rehearsal is expected to understate `exp001` in particular: at
ctx 512 in a 6-layer model, attention is a small share of a step, where the
reference runs ctx 2048 and attention dominates far more — so the time windowed
attention saves, which is the entire mechanism, is mostly absent at this size.
And the corpus is 2.8 M tokens rather than billions, so all three rungs see the
same text many times over.

## What differs from the reference recipe

The **recipe is untouched** — NorMuon on the matrices with AdamW on the tables
and head, trapezoid schedule, ReLU² feed-forward, the 300-second budget. Only
size and hardware accommodations move: 6×256 at ctx 512 rather than 8×512 at
ctx 2048, 16 384 tokens per optimizer step rather than 524 288, fp32 without
`torch.compile`. That is priml's own rule for shrinking — size never
invalidates coverage, recipe does — which is why this lives in its own study
directory rather than as edits to the baseline.

The corpus is wikitext-2 plus Shakespeare, fed through priml's own
`prepare(text_directory=…)`, because `huggingface.co` was unreachable from the
machine this ran on. Tokenizer fit and packing are the real stages; only the
text is substituted.

## Reproducing

```bash
python make_shards.py                      # writes shard_*.parquet
python prepare_local.py --directory /opt/scratch/datasets/nanochat-512 --max-seq-len 512
PYTHONPATH=. python -m priml nanochat_cpu.experiments.exp000 \
    --override dataset.working_dir=/datasets/nanochat-512
```

`prepare_local.py` exists only because the module's CLI does not expose
`text_directory`; every stage it runs is priml's.
