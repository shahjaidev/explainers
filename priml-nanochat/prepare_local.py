"""Run nanochat's own prepare() against the local shards.

Identical to `python -m priml.baselines.nanochat.scripts.prepare_data` except
for `text_directory`, which the module's CLI does not expose: the download
stage is skipped and the staged `shard_*.parquet` files are read instead.
Every later stage -- tokenizer fit, packing, provenance -- is untouched.

Row width is a flag because a split is packed at one geometry and the loader
verifies it against the model, so a run at a different `max_seq_len` needs its
own directory rather than a rebuild of this one.
"""

from __future__ import annotations

import argparse
import logging

from priml.baselines.nanochat.scripts.prepare_data import prepare


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default="/opt/scratch/datasets/nanochat")
    parser.add_argument("--max-seq-len", type=int, default=2_048)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    prepare(
        args.directory,
        num_train_shards=1,
        max_seq_len=args.max_seq_len,
        text_directory="/opt/scratch/nanochat-src",
    )


if __name__ == "__main__":
    main()
