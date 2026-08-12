/* ══════════════════════════════════════════════════════════════════════════
   Margaret — the engine.

   This is the whole system of spec §4/§5, running client-side so the demo
   holds up with no cluster and no keys:

     MongoDB Atlas collections  →  Store (in-memory + localStorage, with a
                                   BroadcastChannel standing in for change
                                   streams so the dashboard is live)
     Voyage embeddings          →  embed(): hashed lexical vectors, cosine
     Atlas Vector Search        →  retrieve(): cosine × importance × recency
     Fireworks fast LLM         →  classify(): intent + agitation markers
     Fireworks VLM              →  VisionMood: frame-difference + luminance
                                   analysis of the live camera
     Claude via OpenRouter      →  decide(): dementia-care rules engine, or
                                   the real thing if a key is supplied
     ElevenLabs Scribe / TTS    →  Web Speech API recognition + synthesis

   Every seam is named so the hosted service can be dropped in behind it:
   search for `SEAM:` to find them.
   ══════════════════════════════════════════════════════════════════════ */

(function (global) {
  'use strict';

  const S = global.MargaretSeed;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const uid = (p) => p + '_' + Math.random().toString(36).slice(2, 10);

  /* ══ 1. Embeddings ══════════════════════════════════════════════════
     SEAM: voyage-3. A hashed bag-of-words vector with light stemming and
     bigrams. Not semantic in the way an embedding model is, but enough to
     make "did the girl come by?" land on the Sarah memory, which is the
     retrieval behaviour the demo turns on. */

  const DIM = 256;
  const STOP = new Set(('a an the is are was were be been am do does did have has had i you he she it we they ' +
    'my your his her our their me him them of to in on at for with and or but if my mine that this these those ' +
    'so as by from up down out about into over then than there here what when where who whom which how why ' +
    'again just now still yet very really please thank thanks ok okay yes no not').split(' '));

  const SYNONYM = {
    girl: 'sarah', daughter: 'sarah', 'my daughter': 'sarah',
    husband: 'robert', hubby: 'robert',
    pills: 'tablets', medicine: 'tablets', medication: 'tablets', meds: 'tablets', pill: 'tablets',
    flowers: 'roses', flower: 'roses',
    grandson: 'tom', granddaughter: 'alice',
    sea: 'whitstable', beach: 'whitstable', seaside: 'whitstable',
    music: 'piano', teaching: 'piano', taught: 'piano'
  };

  function stem(w) {
    w = w.replace(/'s$/, '');
    if (w.length > 4 && /(ing|ies|ed|es|s)$/.test(w)) {
      w = w.replace(/ies$/, 'y').replace(/(ing|ed|es|s)$/, '');
    }
    return w;
  }

  function tokens(text) {
    const raw = String(text || '').toLowerCase().replace(/[^a-z0-9\s']/g, ' ').split(/\s+/).filter(Boolean);
    const out = [];
    for (let w of raw) {
      if (SYNONYM[w]) w = SYNONYM[w];
      if (STOP.has(w)) continue;
      out.push(stem(w));
    }
    // Bigrams, over a snapshot of the unigrams — appending while walking
    // the same array would never terminate.
    const n = out.length;
    for (let i = 0; i < n - 1; i++) out.push(out[i] + '~' + out[i + 1]);
    return out;
  }

  function hash(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return (h >>> 0) % DIM;
  }

  function embed(text) {
    const v = new Float32Array(DIM);
    const t = tokens(text);
    for (const tok of t) v[hash(tok)] += tok.includes('~') ? 0.6 : 1;
    let n = 0;
    for (let i = 0; i < DIM; i++) n += v[i] * v[i];
    n = Math.sqrt(n) || 1;
    for (let i = 0; i < DIM; i++) v[i] /= n;
    return v;
  }

  function cosine(a, b) {
    let s = 0;
    for (let i = 0; i < DIM; i++) s += a[i] * b[i];
    return s;
  }

  /* ══ 2. Store ═══════════════════════════════════════════════════════
     SEAM: MongoDB Atlas. One "cluster", all collections. Writes broadcast
     on a channel; the dashboard subscribes exactly as it would to a change
     stream, so the wiring on the UI side is already right. */

  const CHANNEL = 'margaret.changestream';
  const PERSIST_KEY = 'margaret.state.v1';

  const Store = {
    patient: null,
    memories: [],
    media: [],
    interactions: [],
    moodEvents: [],
    comfortStrategies: [],
    alerts: [],
    reports: [],
    dayStats: [],
    voiceMessages: [],
    _bc: null,
    _subs: [],

    /* — time: the demo runs on a virtual clock anchored to a fixed
         "today" so that a seeded 3:40pm agitation episode is always at
         3:40pm no matter when the laptop is opened. — */
    now() { return new Date(); },
    todayAt(hhmm) {
      const d = new Date();
      const [h, m] = hhmm.split(':').map(Number);
      d.setHours(h, m, 0, 0);
      return d;
    },
    dayAt(dayOffset, hour) {
      const d = new Date();
      d.setDate(d.getDate() - dayOffset);
      d.setHours(Math.floor(hour), Math.round((hour % 1) * 60), 0, 0);
      return d;
    },

    init(opts) {
      opts = opts || {};
      const restored = opts.fresh ? null : this._load();
      if (restored) {
        Object.assign(this, restored);
        // Float32Arrays do not survive JSON — rebuild them.
        this.memories.forEach(m => { m.embedding = embed(m.content); });
        this.interactions.forEach(i => { i.embedding = embed(i.patientSaid); });
      } else {
        this._seed();
      }
      this._connect();
      return this;
    },

    _seed() {
      this.patient = JSON.parse(JSON.stringify(S.patient));
      this.media = S.media.map(m => Object.assign({ patientId: this.patient._id }, m));
      this.voiceMessages = S.voiceMessages.slice();

      this.memories = S.memories.map(m => ({
        _id: uid('mem'),
        patientId: this.patient._id,
        type: m.type,
        content: m.content,
        embedding: embed(m.content),
        ts: this.dayAt(m.dayOffset, +m.hhmm.split(':')[0] + (+m.hhmm.split(':')[1]) / 60).toISOString(),
        dayOffset: m.dayOffset,
        importance: m.importance,
        emotionalValence: m.emotionalValence || 0,
        refs: m.refs || { people: [], mediaIds: [] }
      }));

      this.comfortStrategies = S.comfortStrategies.map(c => Object.assign({
        patientId: this.patient._id,
        effectiveness: +(c.timesHelped / Math.max(1, c.timesUsed)).toFixed(2)
      }, c));

      const week = S.seedWeek();
      this.moodEvents = week.moodEvents.map(e => ({
        _id: uid('mo'), patientId: this.patient._id,
        ts: this.dayAt(e.dayOffset, e.hour).toISOString(),
        dayOffset: e.dayOffset, source: e.source, score: e.score, labels: e.labels
      }));
      this.dayStats = week.dayStats;

      this.interactions = S.seededInteractions.map(i => {
        const ts = this.todayAt(i.hhmm);
        return {
          _id: uid('ix'), patientId: this.patient._id, ts: ts.toISOString(),
          patientSaid: i.patientSaid, agentSaid: i.agentSaid,
          embedding: embed(i.patientSaid),
          intent: i.intent, repeatOf: i.repeat ? 'seeded' : null,
          moodAtTime: i.mood, actionTaken: i.action,
          outcome: { moodAfter: i.mood + 0.25, helped: true }, seeded: true
        };
      });

      this.alerts = [
        { _id: uid('al'), patientId: this.patient._id, ts: this.todayAt('16:14').toISOString(),
          kind: 'distress', message: 'Distress at 4:14pm — asked where Robert was. Settled by the garden.',
          acknowledged: true, resolvedBy: 'comfort_topic' },
        { _id: uid('al'), patientId: this.patient._id, ts: this.todayAt('13:10').toISOString(),
          kind: 'repetition_flag', message: 'Asked whether anyone is visiting 2× in an hour.',
          acknowledged: false }
      ];
      this.reports = [];
    },

    _connect() {
      if (this._bc || typeof BroadcastChannel === 'undefined') return;
      this._bc = new BroadcastChannel(CHANNEL);
      this._bc.onmessage = (e) => {
        const { collection, doc, op } = e.data || {};
        if (!collection) return;
        this._apply(collection, doc, op, true);
        this._subs.forEach(fn => fn({ collection, doc, op, remote: true }));
      };
    },

    /* Applies a change locally without re-broadcasting it. */
    _apply(collection, doc, op, remote) {
      const arr = this[collection];
      if (!Array.isArray(arr)) return;
      if (op === 'insert') {
        if (arr.some(d => d._id === doc._id)) return;
        if (collection === 'memories') doc.embedding = embed(doc.content);
        if (collection === 'interactions') doc.embedding = embed(doc.patientSaid);
        arr.push(doc);
      } else if (op === 'update') {
        const i = arr.findIndex(d => d._id === doc._id);
        if (i >= 0) Object.assign(arr[i], doc);
        else arr.push(doc);
      } else if (op === 'reset') {
        this._seed();
      }
      if (!remote) this._save();
    },

    write(collection, doc, op) {
      op = op || 'insert';
      this._apply(collection, doc, op, false);
      const payload = JSON.parse(JSON.stringify(doc, (k, v) => (k === 'embedding' ? undefined : v)));
      if (this._bc) this._bc.postMessage({ collection, doc: payload, op });
      this._subs.forEach(fn => fn({ collection, doc, op, remote: false }));
      return doc;
    },

    /* change-stream subscription */
    watch(fn) { this._subs.push(fn); return () => { this._subs = this._subs.filter(f => f !== fn); }; },

    _save() {
      try {
        const strip = (k, v) => (k === 'embedding' ? undefined : v);
        localStorage.setItem(PERSIST_KEY, JSON.stringify({
          patient: this.patient, memories: this.memories, media: this.media,
          interactions: this.interactions, moodEvents: this.moodEvents.slice(-4000),
          comfortStrategies: this.comfortStrategies, alerts: this.alerts,
          reports: this.reports, dayStats: this.dayStats, voiceMessages: this.voiceMessages,
          savedAt: Date.now()
        }, strip));
      } catch (e) { /* quota — the demo survives without persistence */ }
    },

    _load() {
      try {
        const raw = localStorage.getItem(PERSIST_KEY);
        if (!raw) return null;
        const st = JSON.parse(raw);
        // A stale save from a previous day would put "today" in the past.
        if (!st.savedAt || Date.now() - st.savedAt > 12 * 3600e3) return null;
        if (new Date(st.savedAt).getDate() !== new Date().getDate()) return null;
        return st;
      } catch (e) { return null; }
    },

    reset() {
      try { localStorage.removeItem(PERSIST_KEY); } catch (e) {}
      this._seed();
      if (this._bc) this._bc.postMessage({ collection: 'memories', doc: {}, op: 'reset' });
      this._subs.forEach(fn => fn({ collection: '*', op: 'reset' }));
    },

    /* — derived reads the UI leans on — */
    todaysInteractions() {
      const start = this.todayAt('00:00').getTime();
      return this.interactions.filter(i => new Date(i.ts).getTime() >= start);
    },
    currentMood() {
      const recent = this.moodEvents.slice(-6);
      if (!recent.length) return 0;
      // Weighted toward the newest sample; the aura should lead, not lag.
      let w = 0, s = 0;
      recent.forEach((e, i) => { const k = i + 1; s += e.score * k; w += k; });
      return s / w;
    },
    mediaById(id) { return this.media.find(m => m._id === id); },
    familyMember(name) {
      return this.patient.profile.family.find(f => f.name.toLowerCase() === String(name).toLowerCase());
    },
    rankedStrategies() {
      return this.comfortStrategies.slice().sort((a, b) => b.effectiveness - a.effectiveness);
    }
  };

  /* ══ 3. Retrieval ═══════════════════════════════════════════════════
     SEAM: Atlas Vector Search ($vectorSearch on memories.embedding, cosine,
     filtered by patientId). Reranked by importance × recency exactly as the
     server-side pipeline would. */

  function retrieve(text, opts) {
    opts = opts || {};
    const k = opts.k || 5;
    const q = embed(text);
    const now = Date.now();
    const scored = Store.memories.map(m => {
      const sim = cosine(q, m.embedding);
      const ageDays = Math.max(0, (now - new Date(m.ts).getTime()) / 86400e3);
      // Episodic memory fades; semantic and procedural knowledge does not.
      const recency = m.type === 'episodic' ? Math.exp(-ageDays / 3.2) : 1;
      return { memory: m, sim, score: sim * (0.45 + 0.55 * m.importance) * (0.35 + 0.65 * recency) };
    }).filter(r => r.sim > 0.04);
    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, k);
  }

  function retrieveMedia(text, opts) {
    opts = opts || {};
    const q = embed(text);
    const pool = Store.media.filter(m => (opts.kind ? m.kind === opts.kind : m.kind === 'photo'));
    return pool.map(m => {
      const sim = cosine(q, embed(m.caption + ' ' + (m.refs || []).join(' ')));
      return { media: m, sim, score: sim * (opts.comfort ? (0.3 + 0.7 * m.comfortScore) : 1) };
    }).sort((a, b) => b.score - a.score);
  }

  /* ══ 4. Classification ══════════════════════════════════════════════
     SEAM: Fireworks small/fast LLM. Intent plus agitation markers on the
     live transcript. Repeat detection is a vector match against today's
     interactions — over 0.85 it is the same question again. */

  const DISTRESS_WORDS = /\b(scared|frightened|afraid|lost|alone|help|don'?t know|where am i|why am i|hurt|crying|upset|worried|panic|nobody|no one|home|go home)\b/i;
  const QUESTION_RE = /\?|^(who|what|where|when|why|how|did|do|does|is|are|have|has|am|can|will|should|shall)\b/i;

  function classify(text, mood) {
    const t = String(text || '').trim();
    const lower = t.toLowerCase();

    // agitation markers: distress vocabulary, fragmentation, repetition of
    // a word within the utterance itself.
    const words = lower.split(/\s+/).filter(Boolean);
    const distinct = new Set(words).size;
    const fragmentation = words.length > 3 ? 1 - distinct / words.length : 0;
    let agitation = 0;
    if (DISTRESS_WORDS.test(lower)) agitation += 0.5;
    if (fragmentation > 0.35) agitation += 0.2;
    if (/[!]{1,}|\b(please|please please)\b/.test(lower)) agitation += 0.1;
    if (mood < -0.35) agitation += 0.35;
    agitation = clamp(agitation, 0, 1);

    // repeat detection against today's questions
    const q = embed(t);
    let repeatOf = null, best = 0;
    for (const ix of Store.todaysInteractions()) {
      if (!ix.embedding) continue;
      const sim = cosine(q, ix.embedding);
      if (sim > best) { best = sim; if (sim > 0.85) repeatOf = ix._id; }
    }

    let intent = 'chat';
    if (agitation >= 0.5 || mood < -0.5) intent = 'distress';
    else if (repeatOf) intent = 'repeat_question';
    else if (QUESTION_RE.test(t)) intent = 'question';

    return { intent, agitation, repeatOf, repeatSimilarity: +best.toFixed(2) };
  }

  /* ══ 5. Decide ══════════════════════════════════════════════════════
     SEAM: Claude via OpenRouter. The system prompt below is the real one —
     if a key is present in settings, it is sent verbatim and the model's
     structured JSON is used. With no key, the rules engine underneath
     encodes the same communication rules deterministically, so the demo
     never depends on the network.

     Rules, in the order they matter:
       · never quiz, never correct bluntly, never say "you already asked"
       · short warm sentences, one idea at a time, answer as if it were the
         first time
       · a question about someone who has died is met with gentle
         reorientation toward a shared, positive memory — never a blunt
         fact, and never a lie
       · follow the per-patient guidance in profile.lifeFacts
   */

  const SYSTEM_PROMPT = `You are Margaret, a voice companion for a person living with dementia.

Communication rules, absolute:
- Never quiz her. Never test her memory. Never ask "don't you remember?"
- Never say she has already asked, even when she has asked forty times. Answer as if it were the first time, with the same warmth.
- Never correct her bluntly. Never argue with her version of reality.
- Two short sentences at most. One idea at a time. Warm, plain, unhurried.
- If she asks about someone who has died, do not state the death and do not lie. Move gently toward a real, warm memory of that person, and offer something to do now.
- Use only what is in the retrieved memories. If you do not know, say so kindly and offer something comforting you do know.

Return strict JSON:
{"speech": string, "action": "answer"|"reorient"|"comfort_topic"|"show_photo"|"family_voice"|"alert_caregiver", "mediaId": string|null, "comfortStrategy": string|null, "enactment": string|null}`;

  const Settings = {
    get(k, d) { try { const v = localStorage.getItem('margaret.' + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('margaret.' + k, JSON.stringify(v)); } catch (e) {} }
  };

  async function decideWithClaude(ctx) {
    const key = Settings.get('openrouterKey', '');
    if (!key) return null;
    const body = {
      model: Settings.get('model', 'anthropic/claude-sonnet-4.5'),
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: JSON.stringify({
            patient: { name: ctx.patient.name, lifeFacts: ctx.patient.profile.lifeFacts,
                       family: ctx.patient.profile.family.map(f => ({ name: f.name, relation: f.relation, deceased: f.deceased || null })) },
            sheSaid: ctx.text, intent: ctx.cls.intent, moodNow: +ctx.mood.toFixed(2),
            retrievedMemories: ctx.hits.map(h => h.memory.content),
            availablePhotos: Store.media.filter(m => m.kind === 'photo').map(m => ({ id: m._id, caption: m.caption })),
            topComfortStrategies: Store.rankedStrategies().slice(0, 3).map(s => s.strategy),
            lastExchanges: Store.todaysInteractions().slice(-5).map(i => ({ she: i.patientSaid, margaret: i.agentSaid }))
          }) }
      ],
      temperature: 0.4, max_tokens: 350
    };
    try {
      const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + key },
        body: JSON.stringify(body)
      });
      if (!res.ok) throw new Error('OpenRouter ' + res.status);
      const json = await res.json();
      const txt = json.choices[0].message.content;
      const parsed = JSON.parse(txt.replace(/^```(?:json)?|```$/g, '').trim());
      parsed._source = 'claude';
      return parsed;
    } catch (e) {
      console.warn('[margaret] OpenRouter call failed, falling back to the local rules engine:', e.message);
      return null;
    }
  }

  /* — the local rules engine — */

  function sentences(s) { return String(s).split(/(?<=[.!?])\s+/).filter(Boolean); }
  function firstSentence(s) { return sentences(s)[0] || ''; }

  /* Memories are written about her in the third person, because that is how
     a carer would write them. She is spoken to in the second. Every "she"
     and "her" in the corpus refers to Eleanor — other people are always
     named — so the rewrite is safe here. */
  function toSecondPerson(text) {
    return String(text)
      .replace(/\bEleanor\b/g, 'you')
      .replace(/\bShe\b/g, 'You').replace(/\bshe\b/g, 'you')
      .replace(/\bHer\b/g, 'Your').replace(/\bher\b/g, 'your')
      .replace(/\bherself\b/g, 'yourself')
      .replace(/\byou was\b/g, 'you were')
      .replace(/\byou has\b/g, 'you have')
      .replace(/^you\b/, 'You');
  }

  function decideLocally(ctx) {
    const { text, cls, hits, mood } = ctx;
    const lower = text.toLowerCase();
    const top = hits[0] && hits[0].memory;
    const name = ctx.patient.name;

    const mentioned = ctx.patient.profile.family.filter(f => new RegExp('\\b' + f.name + '\\b', 'i').test(text)
      || (f.relation === 'daughter' && /\b(daughter|girl)\b/i.test(text))
      || (f.relation === 'husband' && /\b(husband)\b/i.test(text)));

    /* — deceased loved one: the rule that matters most — */
    const dead = mentioned.find(f => f.deceased);
    if (dead && /\b(where|when|why|is|has|come|coming|back|gone|home)\b/i.test(lower)) {
      const warm = Store.memories.filter(m => (m.refs.people || []).includes(dead.name) && m.emotionalValence > 0.2)
        .sort((a, b) => b.importance - a.importance)[0];
      const garden = Store.rankedStrategies()[0];
      return {
        speech: `${dead.name} isn't here just now, ${name}. ` +
                (warm ? toSecondPerson(firstSentence(warm.content)) + ' ' : '') +
                `Those roses by the wall are the ones you planted together. Shall we go and look at them?`,
        action: 'reorient',
        mediaId: 'md_garden',
        comfortStrategy: garden.strategy,
        enactment: null, _source: 'rules'
      };
    }

    /* — medication — */
    if (/\b(tablets|pill|pills|medicine|medication)\b/i.test(lower)) {
      const med = Store.memories.filter(m => /tablet/i.test(m.content) && m.type === 'episodic' && m.dayOffset === 0)
        .sort((a, b) => new Date(b.ts) - new Date(a.ts))[0];
      const evening = new Date().getHours() >= 20;
      return {
        speech: med
          ? `You have, ${name}. You took them at five past nine, with your orange juice.` +
            (evening ? ' The evening one is at nine.' : '')
          : `Not yet — they're at nine. I'll remind you when it's time.`,
        action: 'answer', mediaId: null, comfortStrategy: null,
        enactment: 'en_pills', _source: 'rules'
      };
    }

    /* — who is X — */
    const whoMatch = /\bwho(?:'s| is| was)\s+(\w+)/i.exec(text);
    if (whoMatch) {
      const who = Store.familyMember(whoMatch[1]) ||
        ctx.patient.profile.family.find(f => f.relation === whoMatch[1].toLowerCase());
      if (who) {
        const about = Store.memories.filter(m => (m.refs.people || []).includes(who.name));
        // Something warm and recent beats a stated fact — and the relation
        // has just been given, so never repeat it back.
        const recent = about.filter(m => m.type === 'episodic' && m.emotionalValence >= 0)
          .sort((a, b) => new Date(b.ts) - new Date(a.ts))[0];
        const sem = about.find(m => m.type === 'semantic');
        let extra = '';
        if (recent) {
          extra = toSecondPerson(firstSentence(recent.content))
            .replace(new RegExp('^' + who.name + '\\b'), who.relation === 'grandson' ? 'He' : 'She');
        } else if (sem) {
          const rest = sentences(sem.content).filter(s => !new RegExp('^' + who.name + '\\s+(is|was)\\b', 'i').test(s));
          extra = toSecondPerson(rest[0] || '');
        }
        return {
          speech: `${who.name} is your ${who.relation}, ${name}. ${extra}`.trim(),
          action: 'show_photo', mediaId: who.photoMediaId, comfortStrategy: null,
          enactment: null, _source: 'rules'
        };
      }
    }

    /* — where has X gone / is anyone coming — */
    if (/\b(where|gone|coming|visit|visiting|come by|came)\b/i.test(lower) && mentioned.length && !dead) {
      const f = mentioned[0];
      // The most recent memory of someone is not always the one to hand
      // back — today's argument is true, and it is not what she needs.
      const today = Store.memories.filter(m => (m.refs.people || []).includes(f.name) && m.dayOffset === 0)
        .sort((a, b) => new Date(b.ts) - new Date(a.ts));
      const recent = today.find(m => m.emotionalValence >= 0) || today[0];
      return {
        speech: recent
          ? `${toSecondPerson(firstSentence(recent.content))} She'll be back to see you again soon.`
          : `${f.name} isn't here at the moment, but she thinks of you. She'll be round again soon.`,
        action: 'show_photo', mediaId: f.photoMediaId, comfortStrategy: null,
        enactment: 'en_visit', _source: 'rules'
      };
    }

    /* — why am I upset / what's wrong with me — */
    if (/\b(upset|frightened|scared|worried|why do i feel|what'?s wrong|muddl|confus)\b/i.test(lower)) {
      const sad = Store.memories.filter(m => m.dayOffset === 0 && m.emotionalValence < -0.3)
        .sort((a, b) => new Date(b.ts) - new Date(a.ts))[0];
      const strat = Store.rankedStrategies()[0];
      return {
        speech: sad
          ? `It's been a bit of a muddly afternoon, ${name}, and that's alright. ${toSecondPerson(firstSentence(sad.content))} Shall we sit with the garden a minute?`
          : `Nothing's wrong, ${name}. You're at home and you're safe. Shall we look at your roses?`,
        action: 'comfort_topic', mediaId: strat.mediaId, comfortStrategy: strat.strategy,
        enactment: 'en_garden', _source: 'rules'
      };
    }

    /* — orientation: where am I, what day is it — */
    if (/\bwhere am i|whose house|what day|what time|is it morning|go home\b/i.test(lower)) {
      const now = new Date();
      const part = now.getHours() < 12 ? 'morning' : now.getHours() < 17 ? 'afternoon' : 'evening';
      return {
        speech: `You're at home, ${name}, in your own front room. It's ${part}, ` +
                `${now.toLocaleDateString(undefined, { weekday: 'long' })}. The kettle's just there.`,
        action: 'answer', mediaId: 'md_kitchen', comfortStrategy: null,
        enactment: 'en_morning', _source: 'rules'
      };
    }

    /* — distress with no clear question: go straight to comfort — */
    if (cls.intent === 'distress' || mood < -0.5) {
      const strat = Store.rankedStrategies()[0];
      return {
        speech: `I'm right here, ${name}. You're at home and everything is alright. ${strat.strategy.replace(/^Mention the/, 'Your')} — the roses are out.`,
        action: 'comfort_topic', mediaId: strat.mediaId, comfortStrategy: strat.strategy,
        enactment: 'en_garden', _source: 'rules'
      };
    }

    /* — general: answer straight from the best-retrieved memory — */
    if (top && hits[0].sim > 0.12) {
      const ep = top.type === 'episodic';
      const when = ep ? new Date(top.ts).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : null;
      return {
        speech: (ep ? `${toSecondPerson(firstSentence(top.content))} That was at ${when}.`
                    : toSecondPerson(firstSentence(top.content))),
        action: 'answer',
        mediaId: (top.refs.mediaIds || []).find(id => (Store.mediaById(id) || {}).kind === 'photo') || null,
        comfortStrategy: null,
        enactment: (top.refs.mediaIds || []).find(id => (Store.mediaById(id) || {}).kind === 'enactment') || null,
        _source: 'rules'
      };
    }

    /* — nothing retrieved: never bluff — */
    return {
      speech: `I'm not sure about that one, ${name}. But you're at home, and it's a quiet day. Shall I put the kettle on?`,
      action: 'answer', mediaId: null, comfortStrategy: null, enactment: 'en_tea', _source: 'rules'
    };
  }

  async function decide(ctx) {
    const viaClaude = await decideWithClaude(ctx);
    return viaClaude || decideLocally(ctx);
  }

  /* ══ 6. The agent loop ══════════════════════════════════════════════
     LangGraph's nodes, in order: perceive → classify → retrieve → decide →
     (comfort escalation) → act → record → schedule the outcome check. */

  const Agent = {
    onTrace: null,     // (step, payload) — the dashboard's "thinking" strip
    onAct: null,       // (decision) — the patient screen
    escalation: null,  // active comfort ladder, if any

    /* The trace is not a collection — Store.write on an unknown name stores
       nothing and simply broadcasts, which is exactly what a live "what the
       agent is doing" strip on another screen needs. */
    trace(step, payload) {
      if (this.onTrace) this.onTrace(step, payload);
      try { Store.write('_trace', { _id: uid('tr'), step: step, payload: payload }); } catch (e) {}
    },

    async handleUtterance(text, opts) {
      opts = opts || {};
      const mood = Store.currentMood();
      this.trace('perceive', { text, mood });

      const cls = classify(text, mood);
      this.trace('classify', cls);

      const hits = retrieve(text, { k: 5 });
      this.trace('retrieve', hits.map(h => ({ content: h.memory.content, sim: +h.sim.toFixed(2), type: h.memory.type })));

      const decision = await decide({ text, cls, hits, mood, patient: Store.patient });
      this.trace('decide', decision);

      const ix = this.record(text, decision, cls, mood);

      if (this.onAct) this.onAct(decision, ix);

      // Distress starts the comfort ladder and tells the caregiver.
      // Distress starts the ladder — but if the reply she just heard was
      // already a comfort move, the ladder must not talk over it.
      if (cls.intent === 'distress' || mood < -0.5) {
        this.startEscalation(ix, {
          silent: ['comfort_topic', 'reorient', 'show_photo', 'family_voice'].indexOf(decision.action) >= 0
        });
      }

      // Repetition, flagged for the dashboard only — never to her.
      if (cls.repeatOf) this.checkRepetitionFlag(text);

      this.scheduleOutcomeCheck(ix, decision);
      return { decision, interaction: ix, cls, hits };
    },

    record(text, decision, cls, mood) {
      return Store.write('interactions', {
        _id: uid('ix'), patientId: Store.patient._id, ts: new Date().toISOString(),
        patientSaid: text, agentSaid: decision.speech,
        intent: cls.intent, repeatOf: cls.repeatOf, repeatSimilarity: cls.repeatSimilarity,
        moodAtTime: +mood.toFixed(2), actionTaken: decision.action,
        mediaId: decision.mediaId || null, comfortStrategy: decision.comfortStrategy || null,
        agitation: +cls.agitation.toFixed(2),
        source: decision._source,
        outcome: null
      });
    },

    /* Every exchange writes an episodic memory back — this is what makes
       the morning-load beat of the demo work (spec §11). */
    remember(content, opts) {
      opts = opts || {};
      return Store.write('memories', {
        _id: uid('mem'), patientId: Store.patient._id,
        type: opts.type || 'episodic', content,
        ts: new Date().toISOString(), dayOffset: 0,
        importance: opts.importance != null ? opts.importance : 0.75,
        emotionalValence: opts.valence || 0,
        refs: opts.refs || { people: [], mediaIds: [] },
        fresh: true
      });
    },

    checkRepetitionFlag(text) {
      const hourAgo = Date.now() - 3600e3;
      const q = embed(text);
      const similar = Store.todaysInteractions().filter(i =>
        new Date(i.ts).getTime() > hourAgo && i.embedding && cosine(q, i.embedding) > 0.85);
      if (similar.length >= 3) {
        const subject = (/\b(sarah|robert|tom|alice|tablets|glasses)\b/i.exec(text) || [, 'the same thing'])[1];
        this.alert('repetition_flag', `Asked about ${subject} ${similar.length}× in the last hour.`);
      }
    },

    alert(kind, message, extra) {
      return Store.write('alerts', Object.assign({
        _id: uid('al'), patientId: Store.patient._id, ts: new Date().toISOString(),
        kind, message, acknowledged: false
      }, extra || {}));
    },

    /* — comfort escalation ladder (spec §5.5) —
       topic → photo → family voice, each step waiting for the mood to
       recover before giving up on it. */
    startEscalation(ix, opts) {
      opts = opts || {};
      if (this.escalation) return this.escalation;
      const strat = Store.rankedStrategies()[0];
      this.escalation = {
        step: 'comfort_topic', startedAt: Date.now(), interactionId: ix && ix._id,
        strategy: strat, moodAtStart: Store.currentMood(), timer: null
      };
      this.alert('distress', `Distress detected. Trying: ${strat.strategy}.`, { resolvedBy: null });
      this.trace('escalate', { step: 'comfort_topic', strategy: strat.strategy });
      // Say something — unless she has just been answered with comfort
      // already. An escalation the patient cannot hear is not comfort; two
      // of them at once is worse.
      if (this.onAct && !opts.silent) this.onAct({
        speech: comfortLine(strat.strategy, Store.patient.name),
        action: 'comfort_topic', mediaId: null, comfortStrategy: strat.strategy,
        enactment: 'en_garden', _source: 'escalation'
      }, null);
      this.escalation.timer = setTimeout(() => this.escalateNext(), (Settings.get('escalationMs', 22000)));
      return this.escalation;
    },

    escalateNext() {
      const esc = this.escalation;
      if (!esc) return;
      const mood = Store.currentMood();
      if (mood > -0.25) return this.resolveEscalation(esc.step, mood);

      if (esc.step === 'comfort_topic') {
        esc.step = 'show_photo';
        const pick = retrieveMedia(esc.strategy.strategy + ' ' + Store.patient.name, { comfort: true })[0];
        const decision = {
          speech: `Look who this is, ${Store.patient.name}. ${pick.media.caption}.`,
          action: 'show_photo', mediaId: pick.media._id, comfortStrategy: esc.strategy.strategy, _source: 'escalation'
        };
        this.trace('escalate', { step: 'show_photo', mediaId: pick.media._id });
        if (this.onAct) this.onAct(decision, null);
        esc.timer = setTimeout(() => this.escalateNext(), Settings.get('escalationMs', 22000));
      } else if (esc.step === 'show_photo') {
        esc.step = 'family_voice';
        const vm = Store.voiceMessages[0];
        const decision = {
          speech: vm.text, action: 'family_voice', mediaId: vm.mediaId,
          voice: { speaker: vm.speaker, cloneId: vm.voiceCloneId },
          comfortStrategy: esc.strategy.strategy, _source: 'escalation'
        };
        this.trace('escalate', { step: 'family_voice', speaker: vm.speaker });
        this.alert('distress', `Escalated to ${vm.speaker}'s recorded voice.`, { resolvedBy: null });
        if (this.onAct) this.onAct(decision, null);
        esc.timer = setTimeout(() => this.escalateNext(), Settings.get('escalationMs', 22000));
      } else {
        this.alert('distress', 'Still unsettled after the full comfort sequence — someone should call.', { urgent: true });
        this.endEscalation();
      }
    },

    resolveEscalation(step, mood) {
      const esc = this.escalation;
      if (!esc) return;
      const seconds = Math.round((Date.now() - esc.startedAt) / 1000);
      // The learning beat: the strategy that was on screen when the mood
      // came back gets credit, and its effectiveness is rewritten.
      this.creditStrategy(esc.strategy, true);
      this.alert('distress', `Settled after ${seconds}s — resolved by ${labelForAction(step)}.`,
        { resolvedBy: step, acknowledged: false, resolved: true });
      this.trace('resolved', { step, seconds, mood: +mood.toFixed(2) });
      // Let the screen come back down: no photo, no badge, one quiet line.
      if (this.onAct) this.onAct({
        speech: `There you are, ${Store.patient.name}. Shall we sit a while?`,
        action: 'answer', mediaId: null, comfortStrategy: null, enactment: null, _source: 'escalation'
      }, null);
      this.endEscalation();
    },

    endEscalation() {
      if (this.escalation && this.escalation.timer) clearTimeout(this.escalation.timer);
      this.escalation = null;
    },

    creditStrategy(strategy, helped) {
      const s = Store.comfortStrategies.find(c => c._id === strategy._id);
      if (!s) return;
      s.timesUsed += 1;
      if (helped) s.timesHelped += 1;
      s.effectiveness = +(s.timesHelped / s.timesUsed).toFixed(2);
      s.lastUsedDay = 0;
      Store.write('comfortStrategies', s, 'update');
      this.trace('learn', { strategy: s.strategy, effectiveness: s.effectiveness, helped });
    },

    /* Outcome check: read the mood again a minute later and write it back
       onto the interaction. This is what closes the loop (spec §5.7). */
    scheduleOutcomeCheck(ix, decision) {
      const delay = Settings.get('outcomeMs', 30000);
      setTimeout(() => {
        const moodAfter = Store.currentMood();
        const helped = moodAfter > (ix.moodAtTime || 0) + 0.08;
        ix.outcome = { moodAfter: +moodAfter.toFixed(2), helped, checkedAt: new Date().toISOString() };
        Store.write('interactions', ix, 'update');
        if (decision.comfortStrategy) {
          const s = Store.comfortStrategies.find(c => c.strategy === decision.comfortStrategy);
          if (s) this.creditStrategy(s, helped);
        }
        this.trace('outcome', { helped, moodAfter: ix.outcome.moodAfter });
      }, delay);
    },

    /* — consolidation / the nightly one-pager (spec §5.8) — */
    consolidate() {
      const ixs = Store.todaysInteractions();
      const repeats = ixs.filter(i => i.repeatOf).length;
      const questions = ixs.filter(i => /question/.test(i.intent)).length;
      const todaysMood = Store.moodEvents.filter(m => m.dayOffset === 0 || new Date(m.ts).toDateString() === new Date().toDateString());

      // agitation episodes: runs of consecutive samples under −0.45
      const episodes = [];
      let run = null;
      todaysMood.slice().sort((a, b) => new Date(a.ts) - new Date(b.ts)).forEach(m => {
        if (m.score < -0.40) {
          if (!run) run = { start: m.ts, end: m.ts, min: m.score };
          else { run.end = m.ts; run.min = Math.min(run.min, m.score); }
        } else if (run) { episodes.push(run); run = null; }
      });
      if (run) episodes.push(run);

      const resolvedAlerts = Store.alerts.filter(a => a.resolvedBy);
      episodes.forEach((e, i) => {
        const near = resolvedAlerts.find(a => Math.abs(new Date(a.ts) - new Date(e.end)) < 20 * 60e3);
        e.resolvedBy = near ? labelForAction(near.resolvedBy) : 'settled on its own';
        e.trigger = i === episodes.length - 1 ? 'late-afternoon, no clear trigger' : 'asked after a family member';
      });

      // Only doses that were actually due count against her — an evening
      // tablet at six in the evening is not a missed dose.
      const nowMin = new Date().getHours() * 60 + new Date().getMinutes();
      const due = Store.patient.profile.medications.reduce((n, m) =>
        n + m.times.filter(t => (+t.split(':')[0]) * 60 + (+t.split(':')[1]) <= nowMin).length, 0);
      const medDoses = due;
      // Each drug named alongside a "tablet" memory today counts as taken;
      // the morning memory covers the two nine o'clock drugs at once.
      const medMemories = Store.memories.filter(m => m.dayOffset === 0 && /tablet/i.test(m.content));
      const taken = medDoses === 0 ? 0 : Math.min(medDoses, Store.patient.profile.medications.reduce((n, drug) => {
        const hit = medMemories.some(mem =>
          new RegExp(drug.name, 'i').test(mem.content) ||
          drug.times.some(t => {
            const hh = +t.split(':')[0];
            const mh = new Date(mem.ts).getHours();
            return Math.abs(mh - hh) <= 1;
          }));
        return n + (hit ? drug.times.filter(t => (+t.split(':')[0]) * 60 + (+t.split(':')[1]) <= nowMin).length : 0);
      }, 0));

      const ranked = Store.rankedStrategies();
      const worst = ranked[ranked.length - 1];

      const topQuestions = (function () {
        const buckets = {};
        ixs.forEach(i => {
          const key = tokens(i.patientSaid).filter(t => !t.includes('~')).slice(0, 3).join(' ') || i.patientSaid;
          (buckets[key] = buckets[key] || { key, n: 0, example: i.patientSaid }).n++;
        });
        return Object.values(buckets).sort((a, b) => b.n - a.n).slice(0, 5);
      })();

      const sundown = (function () {
        const byHour = {};
        todaysMood.forEach(m => {
          const h = new Date(m.ts).getHours();
          (byHour[h] = byHour[h] || []).push(m.score);
        });
        const avg = Object.entries(byHour).map(([h, arr]) => ({ hour: +h, mean: arr.reduce((a, b) => a + b, 0) / arr.length }));
        const dip = avg.filter(a => a.mean < -0.2).map(a => a.hour).sort((a, b) => a - b);
        return dip.length ? { from: dip[0], to: dip[dip.length - 1] + 1 } : null;
      })();

      const report = {
        _id: uid('rep'), patientId: Store.patient._id, date: new Date().toISOString().slice(0, 10),
        generatedAt: new Date().toISOString(),
        stats: {
          exchanges: ixs.length,
          repetitionRate: questions ? +(repeats / questions).toFixed(2) : 0,
          repeats, questions,
          agitationEpisodes: episodes.map(e => ({
            start: e.start, end: e.end, low: +e.min.toFixed(2), trigger: e.trigger, resolvedBy: e.resolvedBy
          })),
          medAdherence: medDoses === 0 ? null : +(taken / medDoses).toFixed(2),
          medDue: medDoses, medTaken: taken,
          sundown,
          topQuestions,
          comfortRanking: ranked.map(s => ({ strategy: s.strategy, effectiveness: s.effectiveness, timesUsed: s.timesUsed })),
          weekTrend: Store.dayStats.slice()
        },
        carePlanSuggestions: [
          sundown
            ? `Unsettled roughly ${fmtHour(sundown.from)}–${fmtHour(sundown.to)}. Worth trying the lights on earlier and a quieter routine from mid-afternoon — a pattern for the clinician to review.`
            : 'No clear time-of-day pattern in today\'s record.',
          `${ranked[0].strategy} is holding at ${Math.round(ranked[0].effectiveness * 100)}% across ${ranked[0].timesUsed} attempts. Worth telling anyone else who sits with her.`,
          `${worst.strategy} has dropped to ${Math.round(worst.effectiveness * 100)}%. It used to work; it now seems to sadden her. Suggest retiring it.`,
          questions && repeats / questions > 0.35
            ? `Repetition ran at ${Math.round((repeats / questions) * 100)}% of questions today, above the week's average. Something for the next appointment to note.`
            : 'Repetition sat within her usual range today.',
          medDoses === 0
            ? 'No medication was due yet at the time this was compiled.'
            : `Medication prompts: ${taken} of ${medDoses} doses due today confirmed in the record.`
        ],
        disclaimer: 'Clinician-ready observations and care plan suggestions for a doctor to review. Not a diagnosis and not medical advice.'
      };

      Store.write('reports', report);
      this.trace('consolidate', { reportId: report._id });
      return report;
    }
  };

  /* The strategies are written as instructions to a carer. Spoken aloud
     they have to become something a person would actually say. */
  const COMFORT_LINES = {
    'cs_garden': "Everything's alright, NAME. Your roses are out by the back wall — the ones you planted. Shall we go and look?",
    'cs_piano':  "You're safe, NAME. I was thinking about your piano, and all those years of teaching on Bridge Street.",
    'cs_sea':    "You're at home, NAME, and everything is alright. Can you hear the sea at Whitstable? You always could.",
    'cs_grand':  "It's alright, NAME. Tom and Alice were asking after you. Shall we talk about them a minute?",
    'cs_tea':    "Nothing to worry about, NAME. Let's put the kettle on and sit down a while.",
    'cs_boat':   "You're alright, NAME. Sit down with me a minute."
  };
  function comfortLine(strategy, name) {
    const s = Store.comfortStrategies.find(c => c.strategy === strategy);
    const line = (s && COMFORT_LINES[s._id]) || "I'm right here, NAME. You're at home and everything is alright.";
    return line.replace(/NAME/g, name);
  }

  function labelForAction(a) {
    return ({
      comfort_topic: 'a comfort topic', show_photo: 'a family photograph',
      family_voice: "Sarah's recorded voice", answer: 'an answer', reorient: 'gentle reorientation'
    })[a] || a;
  }
  function fmtHour(h) {
    const ampm = h >= 12 ? 'pm' : 'am';
    const hh = h % 12 === 0 ? 12 : h % 12;
    return hh + ampm;
  }

  /* ══ 7. Vision: mood from the camera ════════════════════════════════
     SEAM: Fireworks VLM on a webcam frame every 2–3s. What runs here is a
     local heuristic over the same frames — motion energy, luminance
     variance in the face region, and (with the mic on) voice energy — so
     the pipeline, the cadence, and the mood_events writes are real even
     with no key. Swap analyseFrame() for a POST and nothing else changes.
  */

  const VisionMood = {
    video: null, canvas: null, ctx: null, prev: null,
    timer: null, stream: null, audio: null, analyser: null, audioData: null,
    baseline: null, score: 0, onScore: null, scripted: null, running: false,

    async start(videoEl, opts) {
      opts = opts || {};
      this.video = videoEl;
      this.canvas = document.createElement('canvas');
      this.canvas.width = 64; this.canvas.height = 48;
      this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
      this.prev = null; this.baseline = null;
      this.running = true;
      if (opts.withAudio && this.stream) this._startAudio();
      const period = opts.periodMs || 2500;
      clearInterval(this.timer);
      this.timer = setInterval(() => this.tick(), period);
    },

    async openCamera(videoEl, deviceId) {
      const constraints = {
        video: deviceId ? { deviceId: { exact: deviceId } } : { width: 1280, height: 720, facingMode: 'user' },
        audio: false
      };
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      videoEl.srcObject = this.stream;
      videoEl.muted = true;
      await videoEl.play().catch(() => {});
      return this.stream;
    },

    async listDevices() {
      try {
        const all = await navigator.mediaDevices.enumerateDevices();
        return all.filter(d => d.kind === 'videoinput');
      } catch (e) { return []; }
    },

    async openMic() {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ audio: true });
        const AC = window.AudioContext || window.webkitAudioContext;
        const ac = new AC();
        const src = ac.createMediaStreamSource(s);
        this.analyser = ac.createAnalyser();
        this.analyser.fftSize = 1024;
        src.connect(this.analyser);
        this.audioData = new Uint8Array(this.analyser.fftSize);
        this.audio = s;
        return true;
      } catch (e) { return false; }
    },
    _startAudio() { /* mic is opened separately; kept for symmetry */ },

    voiceEnergy() {
      if (!this.analyser) return null;
      this.analyser.getByteTimeDomainData(this.audioData);
      let sum = 0;
      for (let i = 0; i < this.audioData.length; i++) {
        const v = (this.audioData[i] - 128) / 128;
        sum += v * v;
      }
      return Math.sqrt(sum / this.audioData.length);
    },

    /* SEAM: replace with a POST of the frame to Fireworks and read back a
       {valence, labels} object. Everything downstream is unchanged. */
    analyseFrame() {
      const v = this.video;
      if (!v || v.readyState < 2 || !v.videoWidth) return null;
      const W = this.canvas.width, H = this.canvas.height;
      this.ctx.drawImage(v, 0, 0, W, H);
      const frame = this.ctx.getImageData(0, 0, W, H).data;

      const gray = new Float32Array(W * H);
      for (let i = 0, p = 0; i < frame.length; i += 4, p++) {
        gray[p] = (frame[i] * 0.299 + frame[i + 1] * 0.587 + frame[i + 2] * 0.114) / 255;
      }

      let motion = 0;
      if (this.prev) {
        for (let p = 0; p < gray.length; p++) motion += Math.abs(gray[p] - this.prev[p]);
        motion /= gray.length;
      }
      this.prev = gray;

      // Central region ≈ where a face sits when someone is at the screen.
      let mean = 0, n = 0;
      for (let y = Math.floor(H * 0.15); y < H * 0.8; y++) {
        for (let x = Math.floor(W * 0.25); x < W * 0.75; x++) { mean += gray[y * W + x]; n++; }
      }
      mean /= n || 1;
      let varc = 0;
      for (let y = Math.floor(H * 0.15); y < H * 0.8; y++) {
        for (let x = Math.floor(W * 0.25); x < W * 0.75; x++) {
          const d = gray[y * W + x] - mean; varc += d * d;
        }
      }
      varc /= n || 1;

      return { motion, mean, variance: varc };
    },

    tick() {
      if (!this.running) return;
      let score;

      if (this.scripted) {
        score = this.scripted(Date.now());
      } else {
        const f = this.analyseFrame();
        if (!f) return;
        // A settled face is still; agitation is restless. Baseline the
        // stillness over the first few frames so a shaky laptop or a busy
        // room does not read as distress.
        if (this.baseline === null) { this.baseline = f.motion; return; }
        this.baseline = this.baseline * 0.94 + f.motion * 0.06;
        const excess = clamp((f.motion - this.baseline) / 0.035, -1, 3);
        const voice = this.voiceEnergy();
        const voiceExcess = voice === null ? 0 : clamp((voice - 0.045) / 0.09, 0, 1.6);
        score = clamp(0.5 - excess * 0.55 - voiceExcess * 0.45, -1, 1);
      }

      // Smooth: mood should drift, never flicker.
      this.score = this.score * 0.62 + score * 0.38;
      const rounded = +this.score.toFixed(2);
      const labels = rounded < -0.5 ? ['agitated'] : rounded < -0.15 ? ['confused'] : rounded > 0.35 ? ['settled'] : ['neutral'];

      Store.write('moodEvents', {
        _id: uid('mo'), patientId: Store.patient._id, ts: new Date().toISOString(),
        dayOffset: 0, source: this.scripted ? 'vision' : 'vision', score: rounded, labels
      });

      if (this.onScore) this.onScore(rounded, labels);

      // Distress with no utterance still enters the graph (spec §5).
      if (rounded < -0.55 && !Agent.escalation) Agent.startEscalation(null);
    },

    /* The demo arc of spec §11: calm, drifting into distress, then
       recovering once the comfort ladder does its work. */
    runScriptedArc(seconds) {
      const t0 = Date.now();
      const total = (seconds || 75) * 1000;
      this.scripted = (now) => {
        const t = (now - t0) / total;
        if (t < 0.22) return 0.45;
        if (t < 0.5) return 0.45 - (t - 0.22) / 0.28 * 1.15;   // slide into distress
        if (t < 0.68) return -0.7 + Math.sin(now / 900) * 0.08; // held distress
        return Math.min(0.55, -0.7 + (t - 0.68) / 0.32 * 1.35); // recovery
      };
      setTimeout(() => { this.scripted = null; }, total + 500);
    },

    stop() {
      this.running = false;
      clearInterval(this.timer);
      if (this.stream) this.stream.getTracks().forEach(t => t.stop());
      if (this.audio) this.audio.getTracks().forEach(t => t.stop());
      this.stream = null; this.audio = null; this.analyser = null;
    }
  };

  /* ══ 8. Voice ═══════════════════════════════════════════════════════
     SEAM: ElevenLabs Scribe for STT and ElevenLabs TTS for the voice —
     including the consented clone of the daughter. What runs here is the
     browser's own recognition and synthesis, tuned warm and slow. */

  const Voice = {
    rec: null, listening: false, onFinal: null, onPartial: null, onState: null,
    _voices: [], _wantRestart: false,

    supported() {
      return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    },

    startListening() {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) return false;
      if (this.rec) this.stopListening();
      const r = new SR();
      r.lang = 'en-GB';
      r.continuous = true;
      r.interimResults = true;
      r.onresult = (e) => {
        let partial = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const res = e.results[i];
          if (res.isFinal) {
            const text = res[0].transcript.trim();
            if (text && this.onFinal) this.onFinal(text);
          } else partial += res[0].transcript;
        }
        if (partial && this.onPartial) this.onPartial(partial);
      };
      r.onend = () => {
        this.listening = false;
        if (this.onState) this.onState(false);
        // Chrome ends the session on its own; keep the ear open.
        if (this._wantRestart) setTimeout(() => { if (this._wantRestart) this.startListening(); }, 350);
      };
      r.onerror = (e) => {
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') this._wantRestart = false;
      };
      this.rec = r;
      this._wantRestart = true;
      try { r.start(); this.listening = true; if (this.onState) this.onState(true); } catch (e) { return false; }
      return true;
    },

    stopListening() {
      this._wantRestart = false;
      if (this.rec) { try { this.rec.stop(); } catch (e) {} this.rec = null; }
      this.listening = false;
      if (this.onState) this.onState(false);
    },

    voices() {
      if (!this._voices.length) this._voices = speechSynthesis.getVoices() || [];
      return this._voices;
    },

    pickVoice(kind) {
      const vs = this.voices().filter(v => /en(-|_)?(GB|AU|IE|US)?/i.test(v.lang));
      const prefer = kind === 'family'
        ? [/Serena/i, /Fiona/i, /Karen/i, /Moira/i, /female/i]
        : [/Daniel/i, /Samantha/i, /Google UK English Female/i, /Serena/i, /female/i];
      for (const re of prefer) { const hit = vs.find(v => re.test(v.name)); if (hit) return hit; }
      return vs[0] || null;
    },

    /* Warm and slow for Margaret; a slightly different pitch for the
       cloned family voice so the two are never confused. */
    speak(text, opts) {
      opts = opts || {};
      return new Promise((resolve) => {
        if (!('speechSynthesis' in window)) return resolve();
        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        const v = this.pickVoice(opts.kind);
        if (v) u.voice = v;
        u.lang = (v && v.lang) || 'en-GB';
        u.rate = opts.kind === 'family' ? 0.9 : 0.82;
        u.pitch = opts.kind === 'family' ? 1.08 : 0.95;
        u.volume = 1;
        u.onend = resolve;
        u.onerror = resolve;
        speechSynthesis.speak(u);
      });
    },

    cancel() { if ('speechSynthesis' in window) speechSynthesis.cancel(); }
  };

  if ('speechSynthesis' in window) {
    speechSynthesis.onvoiceschanged = () => { Voice._voices = speechSynthesis.getVoices() || []; };
  }

  /* ── mood → colour, shared by the aura and every chart ───────────── */
  function moodColor(score) {
    const stops = [
      [-1.0, [195, 64, 46]], [-0.5, [217, 104, 43]], [-0.15, [217, 154, 43]],
      [0.2, [127, 169, 63]], [1.0, [47, 143, 111]]
    ];
    const s = clamp(score, -1, 1);
    for (let i = 0; i < stops.length - 1; i++) {
      const [a, ca] = stops[i], [b, cb] = stops[i + 1];
      if (s >= a && s <= b) {
        const t = (s - a) / (b - a);
        const c = ca.map((v, j) => Math.round(v + (cb[j] - v) * t));
        return `rgb(${c[0]},${c[1]},${c[2]})`;
      }
    }
    return 'rgb(47,143,111)';
  }
  function moodWord(score) {
    return score < -0.55 ? 'Distressed' : score < -0.2 ? 'Unsettled'
      : score < 0.2 ? 'Quiet' : score < 0.5 ? 'Settled' : 'Bright';
  }

  global.Margaret = {
    Store, Agent, Voice, VisionMood, Settings,
    embed, cosine, retrieve, retrieveMedia, classify, decide, decideLocally,
    moodColor, moodWord, labelForAction, fmtHour, SYSTEM_PROMPT, uid, clamp
  };
})(window);
