# nanochat: a padded eval batch raises `IndexError: Target -1 is out of bounds`

A fix is attached as `nanochat-ignore-padded-eval.patch` (against `0e4eea4`).

## Summary

`_TokenBatches.__iter__` pads a short final eval batch and marks the padding
with `-1` targets. `BitsPerByte.update` handles that correctly. But the loss
path that runs *first* — `NanoChatTrainStep.eval_loss` → `_per_token_loss` —
passes those labels straight into `functional.cross_entropy` with no
`ignore_index`, so the run dies before the metric designed to exclude them ever
executes.

It fires whenever the evaluated row count is not an exact multiple of
`dataset.eval_batch_size`, which is a property of the prepared split rather than
of the recipe — the default `eval_batch_size = 16` happens to divide the
reference split.

## Repro

With a 636-row validation split and the default `eval_batch_size = 16`,
`636 = 39·16 + 12`, so the final batch is padded by four rows:

```
File "priml/baselines/nanochat/train_step.py", line 370, in eval_loss
  per_token = self._per_token_loss(self.model, batch)
File "priml/baselines/nanochat/train_step.py", line 458, in _per_token_loss
  return functional.cross_entropy(
IndexError: Target -1 is out of bounds.
```

## Why the metric survives and the loss does not

The two consumers of the batch disagree about how padding is marked.

`data.py:479-484` emits *both* signals — `-1` labels and a `valid_count`:

```python
if valid < self.batch_size:
    label = label.clone()
    label[valid:] = _IGNORED_TARGET
yield {"media": media, "label": label,
       "token_bytes": self.token_bytes, "valid_count": valid}
```

`BitsPerByte.update` (`metric.py:81-83`) deliberately ignores the `-1` marker
and truncates on `valid_count` instead, and its comment says why: a negative
index would wrap into the byte table and land on a real length, so the padding
would be *scored* rather than skipped.

`_per_token_loss` (`train_step.py:452-462`) reads neither. It takes `label`
whole, so the `-1` reaches `cross_entropy` as a class index and raises.

## The fix

`valid_count`, the same signal the metric already trusts, so both consumers read
padding the same way.

Two constraints shape the patch:

- **The returned tensor stays full width.** `BitsPerByte.update` rejects a
  per-token loss whose shape disagrees with the batch's targets, so returning
  `[valid, S]` would move the failure rather than remove it. Padding rows come
  back as zeros, which every consumer then drops on the same row count.
- **The reduction excludes them.** With `reduction="none"` the ignored positions
  are `0.0`, and `eval_loss` reduced with `.mean()` over the whole `[B, S]` — so
  a padded batch would have reported a loss diluted by exactly the rows that are
  not data. That is a second, quieter bug that any fix here has to close; a bare
  `ignore_index=` would leave it open. All three reduction sites now go through
  one `_valid_mean` helper, including the training path, where it is a no-op by
  construction (a short train batch is dropped, never padded) but keeps every
  path spelled the same way.

## Verification

Scoring one checkpoint over the same 636 rows, with and without padding:

| `eval_batch_size` | 636 % bs | before | after |
|---|---|---|---|
| 12 | 0 | `val_bpb=1.8846` | `val_bpb=1.8846` |
| 16 | 12 | `IndexError` | `val_bpb=1.8846` |

Identical to the last digit — the padded configuration now runs *and* reports
the unpadded number.

`test_a_padded_eval_batch_scores_as_its_unpadded_self` covers both halves. It
was confirmed to bite: reverting `train_step.py` alone fails it with the
original `IndexError`. `pytest priml/baselines/nanochat priml/train` is
474 passed, 4 skipped.

## Workaround, without the patch

Choose an `eval_batch_size` that divides the split exactly; every row is still
scored and no batch is padded.

## Environment

priml @ `0e4eea4`, torch 2.11.0 (CPU), Python 3.12, Linux.
