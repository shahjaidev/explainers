"""Glimmer channel-token protocol.

Muse Glimmer emits ``<thought>``, ``<action>`` and ``<observation>`` as
vocabulary items with XML-style ATEM tool calls. That gives us step
boundaries declared by the model rather than recovered by a chunker, which is
where the process reward model scores and where the loss mask changes.

Two rules encoded here:

* ``<observation>`` spans are environment-generated and must be excluded from
  the loss — :func:`loss_mask` marks them.
* Scoring points are the ends of ``<action>`` spans — :func:`action_boundaries`.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

THOUGHT_RE = re.compile(r"<thought>(.*?)</thought>", re.S)
ACTION_RE = re.compile(r'<action\s+name="([A-Za-z_]+)"\s*>(.*?)</action>', re.S)
ARG_RE = re.compile(r'<arg\s+name="([A-Za-z_]+)"\s*>(.*?)</arg>', re.S)
OBS_RE = re.compile(r"<observation>(.*?)</observation>", re.S)


def render_action(name: str, args: Dict[str, str], thought: str = "") -> str:
    parts = []
    if thought:
        parts.append(f"<thought>{thought}</thought>")
    body = "".join(f'<arg name="{k}">{v}</arg>' for k, v in args.items())
    parts.append(f'<action name="{name}">{body}</action>')
    return "".join(parts)


def render_observation(text: str) -> str:
    return f"<observation>{text}</observation>"


def parse_turn(text: str) -> Tuple[str, Optional[str], Dict[str, str]]:
    """Return ``(thought, action_name, args)`` for the first action in *text*."""
    thought_m = THOUGHT_RE.search(text)
    thought = thought_m.group(1).strip() if thought_m else ""
    action_m = ACTION_RE.search(text)
    if not action_m:
        return thought, None, {}
    name = action_m.group(1)
    args = {k: v for k, v in ARG_RE.findall(action_m.group(2))}
    return thought, name, args


def action_boundaries(text: str) -> List[int]:
    """Character offsets just past each ``</action>`` — the scoring points."""
    return [m.end() for m in ACTION_RE.finditer(text)]


def loss_mask(text: str) -> List[int]:
    """1 for trainable characters, 0 for environment-generated observations.

    Character-level here for testability; the token-level version applies the
    same spans after offset mapping from the tokenizer.
    """
    mask = [1] * len(text)
    for m in OBS_RE.finditer(text):
        for i in range(m.start(), m.end()):
            mask[i] = 0
    return mask
