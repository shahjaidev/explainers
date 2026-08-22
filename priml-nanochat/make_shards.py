"""Build local `shard_*.parquet` text shards for nanochat's prepare_data.

The upstream ClimbMix shards are on huggingface.co, which this machine's
network policy blocks. `prepare(text_directory=...)` is the script's own
supported path for local shards, so the pipeline below (tokenizer fit,
packing, provenance) is the real one -- only the corpus is substituted.

Documents are wikitext-2 articles, split on their top-level ` = Title = `
headings. The last 10% become the validation shard, so train and val share no
article.
"""

from __future__ import annotations

import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).parent
HEADING = re.compile(r"^ = [^=].* = $")


def documents(text: str) -> list[str]:
    """Split wikitext into articles, one document per top-level heading."""
    articles: list[list[str]] = []
    for line in text.splitlines():
        if HEADING.match(line):
            articles.append([])
        if articles:
            articles[-1].append(line)
    joined = ["\n".join(lines).strip() for lines in articles]
    return [article for article in joined if len(article) > 512]


def main() -> None:
    docs = documents((HERE / "wikitext2.txt").read_text(encoding="utf-8"))
    # Shakespeare, chunked, joins the training split only: a second register
    # keeps the vocabulary from fitting a single house style.
    play = (HERE / "shakespeare.txt").read_text(encoding="utf-8")
    chunks = [play[i : i + 8_192] for i in range(0, len(play), 8_192)]

    split = int(len(docs) * 0.9)
    train, val = docs[:split] + chunks, docs[split:]
    for index, rows in enumerate((train, val)):
        table = pa.table({"text": pa.array(rows, type=pa.string())})
        pq.write_table(table, HERE / f"shard_{index:05d}.parquet")
        chars = sum(len(row) for row in rows)
        print(f"shard_{index:05d}.parquet: {len(rows):,} documents, {chars:,} chars")


if __name__ == "__main__":
    main()
