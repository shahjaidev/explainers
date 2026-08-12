# Margaret

An AI memory companion for a person living with dementia. Three screens, one memory:

| File | What it is |
|---|---|
| `index.html` | The landing page, built to the Margaret design doc |
| `patient.html` | The patient screen — three panels, live camera, voice |
| `dashboard.html` | The caregiver dashboard — live feed, mood, flags, nightly one-pager |
| `margaret.css` | Design tokens and shared components |
| `data.js` | The seed: Eleanor, ~40 memories over five days, photo library, a week of history |
| `engine.js` | Memory, retrieval, the agent loop, the vision/mood pipeline, voice |

Everything is static. Open `index.html` over any web server — `python3 -m http.server`
from the repo root, then `/margaret/` — and it runs. Camera and microphone need a
secure context, so `localhost` or HTTPS, not `file://`.

## Running the demo

Open the patient screen and the dashboard side by side, in the same browser. They talk
to each other over a `BroadcastChannel`, which is standing in for a MongoDB change
stream — anything written on one appears on the other immediately.

**Patient screen.** Nothing on it is for the patient to operate. The operator's controls
live in a drawer: move the pointer to the very top edge, or press <kbd>D</kbd> to pin it.

- **Camera** — starts `getUserMedia`. The device picker lists every camera; on stage,
  select **OBS Virtual Camera** and the synthetic patient video plays into it.
- **Use a video file** — plays a local clip in place of the camera and reads the mood
  from its frames. Simpler than OBS if you only need the synthetic patient.
- **Run the distress arc** — an 80-second scripted mood curve: calm, sliding into
  distress, then recovering. Use it to rehearse the comfort ladder without acting.
- **Mic on** — voice energy feeds the mood score alongside the camera.
- **Listen for speech** — the browser's recognition; speak and she answers.
- **Say to her** — type an utterance if the room is too loud to talk into a laptop.

Keyboard: <kbd>1</kbd>–<kbd>5</kbd> play the scripted questions, <kbd>E</kbd> ends the
day and writes the report, <kbd>D</kbd> toggles the drawer, <kbd>Esc</kbd> clears the photo.

**Dashboard.** Everything updates live. *End the day & write the report* runs the
consolidation and renders the clinician one-pager; *Print the one-pager* gives you the
PDF (the print stylesheet drops everything but the report). *Reset the demo data*
re-seeds both tabs.

To rehearse the escalation faster, shorten the timers from the console:

```js
Margaret.Settings.set('escalationMs', 8000);   // default 22000
Margaret.Settings.set('outcomeMs', 10000);     // default 30000
```

## The demo beats, and where they live

1. **Infinite patience.** Ask the same question twice. The answer is identical in warmth
   and never mentions the repetition; the dashboard logs `repeatOf` and flags it quietly
   at three in an hour. `classify()` in `engine.js`.
2. **Gentle reorientation.** "Where is Robert?" — no blunt fact, no lie, a move toward a
   warm shared memory and something to do now. The deceased-loved-one branch of
   `decideLocally()`, driven by `profile.lifeFacts`.
3. **Comfort escalation.** Distress → a comfort topic → the best-matching high-comfort
   photograph → the daughter's consented cloned voice, each rung waiting to see whether
   she comes back. `Agent.startEscalation()`.
4. **It learns.** When she settles, the strategy that was on screen gets the credit and
   its effectiveness is rewritten — visibly, on the dashboard. `Agent.creditStrategy()`
   and the outcome check scheduled after every exchange.
5. **The night's page.** Repetition rate, agitation episodes with what resolved them,
   the sundowning window, adherence, and care plan suggestions. `Agent.consolidate()`.

## What is real, and what is standing in

The demo runs entirely in the browser so it never depends on a conference network. Each
hosted service in the plan has a named seam — search `engine.js` for `SEAM:` — and the
data either side of it is already the right shape.

| In the plan | Running here |
|---|---|
| MongoDB Atlas + change streams | `Store`: in-memory collections, `localStorage`, `BroadcastChannel` |
| Voyage AI embeddings | `embed()`: 256-dim hashed lexical vectors with stemming, synonyms, bigrams |
| Atlas Vector Search | `retrieve()`: cosine, reranked by importance × recency, episodic memory decaying |
| Fireworks fast LLM | `classify()`: intent, agitation markers, repeat detection at 0.85 similarity |
| Fireworks VLM | `VisionMood`: frame-difference motion energy, face-region luminance, voice RMS |
| Claude via OpenRouter | `decideLocally()`: the dementia-care rules, deterministic |
| ElevenLabs Scribe / TTS / cloning | Web Speech recognition and synthesis, warm and slow; a distinct voice for the family message |

The Claude seam is live rather than notional. Put a key in and the decide step calls
the real model with the real system prompt:

```js
Margaret.Settings.set('openrouterKey', 'sk-or-…');
Margaret.Settings.set('model', 'anthropic/claude-sonnet-4.5');
```

If the call fails it falls back to the rules engine without a visible stumble, because a
demo that depends on a network is not a demo. Replies that came from Claude are tagged
as such in the dashboard feed.

## Wording, deliberately

"Clinician-ready observations" and "care plan suggestions for a doctor to review" —
never medical-grade, never diagnosis, never therapy. Voice cloning is always with the
family's consent, recorded in person by the owner of the voice. The patient on stage is
synthetic, and we say so out loud. Every name, face, memory and voice in this build is
invented.
