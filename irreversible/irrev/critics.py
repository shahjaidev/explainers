"""Critics — the things that produce the potential phi.

Four implementations, matching the four arms of the critic-scaling plot:

* :class:`SparkCritic`    — the expensive teacher (Muse Spark), over HTTP.
* :class:`DistilledCritic` — a local model served OpenAI-style; the cheap arm.
* :class:`OracleCritic`   — a free proxy built from the recoverability oracle,
  for pilots and for sanity-checking the pipeline without spending anything.
* :class:`RandomCritic`   — the control. If noise helps, the measured effect is
  an optimisation artefact, not supervision.

:class:`CachingCritic` wraps any of them: it deduplicates prefixes (trajectory
prefixes overlap heavily, so this is most of the teacher bill) and writes a
JSONL label file, which is the training set for the distilled critic.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from .oracle import DataPairOracle
from .state import EnvState

SYSTEM_PROMPT = (
    "You are grading a database-migration agent mid-task. Given the task and the "
    "trajectory so far, reply with a single number between 0 and 1: the probability "
    "that this trajectory still reaches a correct migration with no data loss. "
    "Reply with the number only, no words."
)


class Critic(Protocol):
    def score(self, state: EnvState, transcript: List[str], task_name: str = "") -> float: ...


class ConstantCritic:
    def __init__(self, value: float = 0.0):
        self.value = value

    def score(self, state, transcript, task_name="") -> float:
        return self.value


class RandomCritic:
    """The control arm. Deterministic per prefix, so it is a real function."""

    def __init__(self, seed: int = 0):
        self.seed = seed

    def score(self, state, transcript, task_name="") -> float:
        key = f"{self.seed}:{len(transcript)}:{''.join(transcript)[-2000:]}"
        digest = hashlib.sha256(key.encode()).digest()
        return int.from_bytes(digest[:4], "big") / 2**32


class OracleCritic:
    """Free proxy potential: what fraction of protected data is still derivable.

    Not a stand-in for a learned PRM — it sees privileged state the model
    cannot. Useful for validating the plumbing and for establishing the
    ceiling a perfect process signal would give.
    """

    def __init__(self, oracle: DataPairOracle):
        self.oracle = oracle

    def score(self, state, transcript, task_name="") -> float:
        return self.oracle.fraction_now(state)


class _HTTPCritic:
    def __init__(
        self,
        endpoint: str,
        model: str,
        api_key_env: str = "TEACHER_API_KEY",
        timeout: int = 60,
        max_chars: int = 24_000,
    ):
        self.endpoint = endpoint
        self.model = model
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.max_chars = max_chars

    def _prompt(self, transcript: List[str], task_name: str) -> str:
        body = "\n".join(transcript)[-self.max_chars :]
        return f"Task: {task_name}\n\nTrajectory so far:\n{body}\n\nProbability of success:"

    def score(self, state, transcript, task_name="") -> float:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(
                f"{self.api_key_env} is not set — refusing to call {self.endpoint}"
            )
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": self._prompt(transcript, task_name)},
                ],
                "temperature": 0.0,
                "max_tokens": 8,
            }
        ).encode()
        req = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        text = data["choices"][0]["message"]["content"].strip()
        return _clamp01(text)


class SparkCritic(_HTTPCritic):
    """Muse Spark 1.2 as a step-level critic.

    Weights are not public as of writing, so this points at an endpoint.
    Set ``TEACHER_ENDPOINT``/``TEACHER_MODEL`` for an Azure Foundry or
    first-party deployment.
    """

    def __init__(self, endpoint: Optional[str] = None, model: Optional[str] = None, **kw):
        super().__init__(
            endpoint or os.environ.get("TEACHER_ENDPOINT", ""),
            model or os.environ.get("TEACHER_MODEL", "muse-spark-1.2"),
            **kw,
        )


class DistilledCritic(_HTTPCritic):
    """The cheap arm: a small critic trained on Spark labels, served locally."""

    def __init__(self, endpoint: Optional[str] = None, model: Optional[str] = None, **kw):
        kw.setdefault("api_key_env", "CRITIC_API_KEY")
        super().__init__(
            endpoint or os.environ.get("CRITIC_ENDPOINT", "http://localhost:8000/v1/chat/completions"),
            model or os.environ.get("CRITIC_MODEL", "distilled-critic"),
            **kw,
        )


def _clamp01(text: str) -> float:
    try:
        value = float(text.split()[0].strip().rstrip(".,"))
    except (ValueError, IndexError):
        return 0.5
    return max(0.0, min(1.0, value))


class CachingCritic:
    """Prefix cache plus a JSONL label log.

    The cache is where most of the teacher bill goes: trajectory prefixes are
    shared across a group of rollouts, and every scoring call re-sends one.
    The log is the distillation training set — one line per unique prefix.
    """

    def __init__(self, inner: Critic, log_path: Optional[Path] = None):
        self.inner = inner
        self.log_path = Path(log_path) if log_path else None
        self.cache: Dict[str, float] = {}
        self.calls = 0
        self.hits = 0

    @staticmethod
    def _key(transcript: List[str], task_name: str) -> str:
        return hashlib.sha256(("\n".join(transcript) + "|" + task_name).encode()).hexdigest()

    def score(self, state, transcript, task_name="") -> float:
        key = self._key(transcript, task_name)
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        value = self.inner.score(state, transcript, task_name)
        self.cache[key] = value
        self.calls += 1
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            record: Dict[str, Any] = {
                "key": key,
                "task": task_name,
                "steps": len(transcript),
                "transcript": "\n".join(transcript),
                "score": value,
            }
            with self.log_path.open("a") as fh:
                fh.write(json.dumps(record) + "\n")
        return value

    @property
    def hit_rate(self) -> float:
        total = self.calls + self.hits
        return self.hits / total if total else 0.0
