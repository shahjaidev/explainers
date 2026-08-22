"""The nanochat ladder at CPU scale.

A separate study, not an edit to `priml.baselines.nanochat`: the reference
ladder is defined on GPU reference hardware, and a number measured here cannot
be compared with one measured there. Keeping it in its own directory is what
stops the two from being mistaken for each other.

What is unchanged is the RECIPE -- pre-norm transformer, rotary positions,
squared-ReLU feed-forward, NorMuon on the matrices with AdamW on the embedding
and head, trapezoid schedule, the same fixed-wall-clock budget. Only SIZE
moves: width, depth, context, and the tokens an optimizer step consumes. That
is the same rule the priml skill states for shrinking a test -- touching the
recipe would mean this no longer covers the experiment; changing size never
does.

The ladder mirrors the reference one, so the two mechanisms it tests are
visible here at a scale that finishes in minutes:

    exp000  every layer attends over the full context     (window_pattern L)
      +-- exp001  three layers in four attend over half   (window_pattern SSSL)
            +-- exp002  value embeddings on alternating layers

Prepare the 512-token split once, then launch::

    python /opt/scratch/nanochat-src/prepare_local.py --directory /opt/scratch/datasets/nanochat-512 --max-seq-len 512
    python -m priml nanochat_cpu.experiments.exp000
"""

from __future__ import annotations

from priml.baselines.nanochat.experiments import NanoChatLoop
from priml.baselines.nanochat.experiments import exp000 as reference_exp000
from priml.baselines.nanochat.model import ValueGatedAttention


def exp000() -> NanoChatLoop.Config:
    """The reference exp000 recipe, sized for a four-core CPU.

    Hypothesis:
      The reference baseline's claim -- that a plain pre-norm transformer with
      orthogonalized updates is the bar the ladder's two mechanisms must clear
      -- should hold at any size, so a CPU-scale copy is a usable rehearsal of
      the comparison even though its absolute score is not comparable.

    References:
      priml.baselines.nanochat.experiments.exp000, whose recipe this inherits
      unchanged; only width, depth, context, and step size differ.

    Results:
      TBD. Not reference hardware -- a number measured here is a rehearsal,
      never a result.

    """
    cfg = reference_exp000()
    cfg.study_name = "nanochat_cpu"

    # Size, and nothing else. The head width is not derived from the model
    # width, so narrowing one without the other leaves a model that cannot be
    # built at all.
    cfg.step.model.channels = 256
    cfg.step.model.num_layers = 6
    cfg.step.model.max_seq_len = 512
    attention = cfg.step.model.block.attn
    assert isinstance(attention, ValueGatedAttention.Config)
    attention.channels_head = 64

    # A CPU step is ~3 orders of magnitude slower than the reference GPU one,
    # so the reference 524_288 tokens would spend the whole budget inside a
    # single optimizer step and the schedule would never anneal.
    cfg.step.tokens_per_optimizer_step = 16_384
    cfg.step.rows_per_pass = 8
    # Warmup steps are excluded from the budget clock; two is enough here
    # because there is no compile to amortize.
    cfg.step.budget_warmup_steps = 2
    # torch.compile on CPU costs more than the run it would accelerate.
    cfg.step.compile = False
    cfg.step.device = "cpu"
    cfg.step.dtype_autocast = None

    # Eval often enough that the budget produces a curve rather than a
    # before-and-after pair.
    cfg.num_steps_eval = 25
    cfg.num_steps_log = 10

    # Divides the 636-row validation split exactly, so no batch is padded.
    # Not a preference: a short final batch is padded with -1 targets, and
    # NanoChatTrainStep._per_token_loss passes labels to cross_entropy with no
    # ignore_index, so a padded eval batch raises IndexError before the metric
    # that excludes them ever runs. Every row is still scored.
    cfg.dataset.eval_batch_size = 12
    return cfg


def exp001() -> NanoChatLoop.Config:
    """exp000 with three layers in four attending over half the context.

    Hypothesis:
      Most layers resolve local structure, so restricting their attention to
      recent history should cost little accuracy while making each step
      cheaper. Under a fixed budget the saved time becomes more steps, so this
      wins if the accuracy given up is smaller than the accuracy those extra
      steps buy.

    References:
      https://arxiv.org/abs/2004.05150
        Beltagy et al. Longformer: The Long-Document Transformer.

    Results:
      TBD.

    """
    cfg = exp000()
    cfg.experiment_name = "exp001"
    cfg.step.model.window_pattern = "SSSL"
    return cfg


def exp002() -> NanoChatLoop.Config:
    """exp001 plus a gated value embedding on alternating layers.

    Hypothesis:
      A deep stack's residual stream is increasingly processed, so a layer
      wanting the raw token identity must reconstruct it. Letting alternating
      layers read a dedicated embedding of the input tokens -- admitted
      through a per-head gate, so a head can decline it -- supplies that
      directly.

    References:
      https://arxiv.org/abs/2410.17897
        Zhou et al. Value Residual Learning.

    Results:
      TBD.

    """
    cfg = exp001()
    cfg.experiment_name = "exp002"
    cfg.step.model.value_embedding_stride = 2
    return cfg
