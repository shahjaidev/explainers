/* ══════════════════════════════════════════════════════════════════════════
   Margaret — seed data.

   Stands in for the night-before seed script in §8 of the build spec: one
   patient (Eleanor), her profile and life facts, ~40 memories across five
   fictional days, a captioned family photo library, medication schedule,
   pre-ranked comfort strategies, and a seeded week of mood + interaction
   history so the dashboard's trends are never empty.

   Photographs are generated as painterly SVG data URIs. Nothing here is a
   real person: a synthetic patient and a synthetic family, which is also
   what we say on stage (spec §10).
   ══════════════════════════════════════════════════════════════════════ */

(function (global) {
  'use strict';

  /* ── image synthesis ───────────────────────────────────────────────────
     Photographic rather than illustrative. There is no drawn figure anywhere
     in here: a drawn person reads as a cartoon at any size, and a cartoon in
     a photo frame undoes the whole thing. What these paint instead is the
     part of a photograph that survives being out of focus — depth-of-field
     falloff, bokeh discs where the highlights were, a light leak from a
     window, film grain, a vignette. The eye reads that as a photograph taken
     with a wide aperture, which is exactly what it is a picture of.

     Everything is deterministic per seed, so a caption always paints the same
     picture and the two screens never disagree. */

  function svgURI(svg) {
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg.replace(/\s+/g, ' ').trim());
  }

  function rng(seed) {
    let s = 0;
    for (let i = 0; i < seed.length; i++) s = (s * 31 + seed.charCodeAt(i)) >>> 0;
    return function () {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  /* The out-of-focus masses: the furniture, the foliage, the coat someone is
     wearing — whatever was in the frame, reduced to soft blocks of colour. */
  function masses(r, palette, count) {
    let out = '';
    for (let i = 0; i < count; i++) {
      const cx = -40 + r() * 880, cy = -40 + r() * 680;
      const rx = 110 + r() * 300, ry = 90 + r() * 240;
      const rot = r() * 180;
      out += `<ellipse cx="${cx.toFixed(0)}" cy="${cy.toFixed(0)}" rx="${rx.toFixed(0)}" ry="${ry.toFixed(0)}"
              transform="rotate(${rot.toFixed(0)} ${cx.toFixed(0)} ${cy.toFixed(0)})"
              fill="${palette[Math.floor(r() * palette.length)]}"
              opacity="${(0.30 + r() * 0.42).toFixed(2)}"/>`;
    }
    return out;
  }

  /* Bokeh: where a highlight fell outside the plane of focus, a lens leaves a
     soft disc, brighter at the rim than the centre. Larger and more numerous
     toward the bottom of the frame, where the foreground is. */
  function bokeh(r, count, tint) {
    let out = '';
    for (let i = 0; i < count; i++) {
      const depth = r();
      const cx = r() * 800;
      const cy = 40 + Math.pow(r(), 0.65) * 560;
      const rad = 14 + depth * depth * 96;
      out += `<circle cx="${cx.toFixed(0)}" cy="${cy.toFixed(0)}" r="${rad.toFixed(0)}"
              fill="url(#bok)" opacity="${(0.10 + (1 - depth) * 0.30).toFixed(2)}"/>`;
      if (r() > 0.72) {
        out += `<circle cx="${cx.toFixed(0)}" cy="${cy.toFixed(0)}" r="${rad.toFixed(0)}"
                fill="none" stroke="${tint}" stroke-width="${(rad * 0.10).toFixed(1)}" opacity="0.16"/>`;
      }
    }
    return out;
  }

  /* opts:
       palette   4+ colours, darkest first — the ground reads as depth
       light     where the window is: 'left' | 'right' | 'top'
       warmth    strength of the light leak, 0..1
       focus     0 = wide open and dreamy, 1 = nearly sharp
       grain     film grain strength                                     */
  function plate(seed, opts) {
    const r = rng(seed);
    const p = opts.palette;
    const focus = opts.focus == null ? 0.35 : opts.focus;
    const blur = 46 - focus * 26;
    const warmth = opts.warmth == null ? 0.55 : opts.warmth;
    const light = opts.light || 'left';
    const lx = light === 'right' ? 84 : light === 'top' ? 50 : 16;
    const ly = light === 'top' ? 8 : 22;
    const id = 'p' + Math.floor(r() * 1e6).toString(36);

    return svgURI(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
      <defs>
        <linearGradient id="ground${id}" x1="0" y1="0" x2="0.35" y2="1">
          <stop offset="0" stop-color="${p[0]}"/>
          <stop offset="0.55" stop-color="${p[1]}"/>
          <stop offset="1" stop-color="${p[2] || p[1]}"/>
        </linearGradient>
        <radialGradient id="bok">
          <stop offset="0" stop-color="#fff" stop-opacity="0.55"/>
          <stop offset="0.72" stop-color="#fff" stop-opacity="0.30"/>
          <stop offset="0.94" stop-color="#fff" stop-opacity="0.62"/>
          <stop offset="1" stop-color="#fff" stop-opacity="0"/>
        </radialGradient>
        <radialGradient id="leak${id}" cx="${lx}%" cy="${ly}%" r="78%">
          <stop offset="0" stop-color="${opts.leak || '#fff6e6'}" stop-opacity="${(0.62 * warmth).toFixed(2)}"/>
          <stop offset="0.45" stop-color="${opts.leak || '#ffeccf'}" stop-opacity="${(0.24 * warmth).toFixed(2)}"/>
          <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
        </radialGradient>
        <radialGradient id="vig${id}" cx="50%" cy="46%" r="72%">
          <stop offset="0.52" stop-color="#000" stop-opacity="0"/>
          <stop offset="1" stop-color="#000" stop-opacity="${(0.30 + (1 - warmth) * 0.16).toFixed(2)}"/>
        </radialGradient>
        <filter id="dof${id}" x="-12%" y="-12%" width="124%" height="124%">
          <feGaussianBlur stdDeviation="${blur.toFixed(0)}"/>
        </filter>
        <filter id="near${id}" x="-12%" y="-12%" width="124%" height="124%">
          <feGaussianBlur stdDeviation="${(blur * 0.42).toFixed(0)}"/>
        </filter>
        <filter id="grain${id}">
          <feTurbulence type="fractalNoise" baseFrequency="0.82" numOctaves="4" seed="${Math.floor(r() * 99)}"/>
          <feColorMatrix type="saturate" values="0"/>
          <feComponentTransfer><feFuncA type="linear" slope="${(opts.grain || 0.11).toFixed(2)}"/></feComponentTransfer>
        </filter>
      </defs>

      <rect width="800" height="600" fill="url(#ground${id})"/>
      <g filter="url(#dof${id})">${masses(r, p, opts.massCount || 9)}</g>
      <g filter="url(#near${id})">${masses(r, p.slice(1), 3)}</g>
      <g filter="url(#near${id})">${bokeh(r, opts.bokehCount == null ? 16 : opts.bokehCount, p[p.length - 1])}</g>
      <rect width="800" height="600" fill="url(#leak${id})"/>
      <rect width="800" height="600" fill="url(#vig${id})"/>
      <rect width="800" height="600" filter="url(#grain${id})" opacity="0.9"/>
    </svg>`);
  }

  // Kept as the old name so the library below reads unchanged.
  const scene = plate;

  const PORTRAIT = { eleanor: ['#efe0d2', '#d9bfa6', '#c8a98e'], sarah: ['#f2e4d8', '#e2c3ae'] };

  const IMG = {
    /* Warm interior, window on the left, shallow depth of field. */
    eleanorPortrait: plate('eleanor-portrait', {
      palette: ['#8a6f57', '#c3a483', '#e6d2b8', '#f3e6d2'],
      light: 'left', warmth: 0.7, focus: 0.45, massCount: 10, bokehCount: 14
    }),
    /* The face the screen rests on: softer, closer, lit from the front. */
    companionFace: plate('companion-face', {
      palette: ['#9b7a60', '#d4b193', '#eeddc6', '#fbf1e4'],
      light: 'top', warmth: 0.8, focus: 0.3, massCount: 8, bokehCount: 10
    }),
    sarahWedding: plate('sarah-wedding', {
      palette: ['#a08a74', '#ddc9b0', '#f2e7d8', '#fffaf2'],
      light: 'right', warmth: 0.85, focus: 0.5, massCount: 11, bokehCount: 24
    }),
    sarahTea: plate('sarah-tea', {
      palette: ['#7f7360', '#bfb094', '#e4d8c2', '#f6efe2'],
      light: 'left', warmth: 0.6, focus: 0.45, massCount: 9, bokehCount: 15
    }),
    garden: plate('garden', {
      palette: ['#3f5b3a', '#6d8f57', '#a8c47e', '#dbe8b8'],
      light: 'top', warmth: 0.7, focus: 0.35, massCount: 12, bokehCount: 26
    }),
    piano: plate('piano', {
      palette: ['#2f2a26', '#6b5c4c', '#c0ab8e', '#efe3cd'],
      light: 'left', warmth: 0.5, focus: 0.55, massCount: 9, bokehCount: 12
    }),
    robert: plate('robert', {
      palette: ['#6d6455', '#a3958a', '#cfc2ab', '#eae0cd'],
      light: 'right', warmth: 0.45, focus: 0.45, massCount: 9, bokehCount: 11
    }),
    boat: plate('boat', {
      palette: ['#3d6272', '#6f9aab', '#a9c9d4', '#e2eef2'],
      light: 'top', warmth: 0.4, focus: 0.4, massCount: 10, bokehCount: 20
    }),
    grandchildren: plate('grandchildren', {
      palette: ['#8b7355', '#c9ab86', '#e8d6bd', '#faf1e3'],
      light: 'left', warmth: 0.8, focus: 0.4, massCount: 10, bokehCount: 22
    }),
    kitchen: plate('kitchen', {
      palette: ['#7d7361', '#bcae95', '#e2d7c1', '#f7f0e2'],
      light: 'right', warmth: 0.75, focus: 0.5, massCount: 9, bokehCount: 18
    }),
    seaside: plate('seaside', {
      palette: ['#54798a', '#8fb3c0', '#c9dde3', '#eef4f2'],
      light: 'top', warmth: 0.35, focus: 0.3, massCount: 8, bokehCount: 14
    }),

    /* Enactments are not photographs and must never pass for one: no bokeh,
       wide open, heavier grain. A memory, not footage. */
    enactTea:     plate('enact-tea',     { palette: ['#a89272', '#d9c8a8', '#efe4cf'], focus: 0, warmth: 0.5, bokehCount: 0, grain: 0.16 }),
    enactPills:   plate('enact-pills',   { palette: ['#9a9a8e', '#cdcbba', '#e8e5d6'], focus: 0, warmth: 0.4, bokehCount: 0, grain: 0.16 }),
    enactGarden:  plate('enact-garden',  { palette: ['#6f8a5b', '#a9c48c', '#dceac2'], focus: 0, warmth: 0.5, bokehCount: 0, grain: 0.16 }),
    enactVisit:   plate('enact-visit',   { palette: ['#a58d72', '#d4bb9c', '#ece0cd'], focus: 0, warmth: 0.5, bokehCount: 0, grain: 0.16 }),
    enactMorning: plate('enact-morning', { palette: ['#b39a76', '#e2caa4', '#f6ead2'], focus: 0, warmth: 0.7, bokehCount: 0, grain: 0.16 })
  };

  /* ── the patient ──────────────────────────────────────────────────── */

  const patient = {
    _id: 'pt_eleanor',
    name: 'Eleanor',
    profile: {
      age: 82,
      family: [
        { name: 'Sarah',  relation: 'daughter',    photoMediaId: 'md_sarah_wedding', voiceCloneId: 'vc_sarah', consented: true },
        { name: 'Robert', relation: 'husband',     photoMediaId: 'md_robert',        voiceCloneId: null, deceased: 2022 },
        { name: 'Tom',    relation: 'grandson',    photoMediaId: 'md_grandchildren', voiceCloneId: null },
        { name: 'Alice',  relation: 'granddaughter', photoMediaId: 'md_grandchildren', voiceCloneId: null }
      ],
      lifeFacts: [
        'Taught piano for thirty years at the school on Bridge Street.',
        'Husband Robert, passed 2022 — handle with reorientation toward a warm memory, never blunt correction.',
        'Grew up by the sea in Whitstable; the smell of salt air settles her.',
        'Keeps a small garden; the roses by the back wall are hers.',
        'Sarah is her daughter and primary carer, visits most afternoons.',
        'Was a great sailor with Robert once — the boat has stopped comforting her since 2024.'
      ],
      medications: [
        { name: 'Donepezil', times: ['09:00'] },
        { name: 'Vitamin D', times: ['09:00'] },
        { name: 'Memantine', times: ['21:00'] }
      ]
    }
  };

  /* ── media library ────────────────────────────────────────────────── */

  const media = [
    { _id: 'md_sarah_wedding',  kind: 'photo', url: IMG.sarahWedding,  caption: "Sarah's wedding, 2019",              refs: ['Sarah'],            comfortScore: 0.92 },
    { _id: 'md_sarah_tea',      kind: 'photo', url: IMG.sarahTea,      caption: 'Tea with Sarah in the front room',   refs: ['Sarah'],            comfortScore: 0.78 },
    { _id: 'md_garden',         kind: 'photo', url: IMG.garden,        caption: 'The roses by the back wall',          refs: ['garden'],           comfortScore: 0.88 },
    { _id: 'md_piano',          kind: 'photo', url: IMG.piano,         caption: 'At the piano, Bridge Street school',  refs: ['piano'],            comfortScore: 0.81 },
    { _id: 'md_robert',         kind: 'photo', url: IMG.robert,        caption: 'Robert in the garden, 1998',          refs: ['Robert'],           comfortScore: 0.64 },
    { _id: 'md_boat',           kind: 'photo', url: IMG.boat,          caption: 'The boat at Whitstable, 1979',        refs: ['Robert', 'boat'],   comfortScore: 0.21 },
    { _id: 'md_grandchildren',  kind: 'photo', url: IMG.grandchildren, caption: 'Tom and Alice on the back step',      refs: ['Tom', 'Alice'],     comfortScore: 0.83 },
    { _id: 'md_kitchen',        kind: 'photo', url: IMG.kitchen,       caption: 'Her kitchen, morning light',          refs: ['home'],             comfortScore: 0.66 },
    { _id: 'md_seaside',        kind: 'photo', url: IMG.seaside,       caption: 'Whitstable beach, where she grew up', refs: ['sea', 'Whitstable'], comfortScore: 0.79 },
    { _id: 'md_eleanor',        kind: 'photo', url: IMG.eleanorPortrait, caption: 'Eleanor at home',                   refs: ['Eleanor'],          comfortScore: 0.5 },

    { _id: 'en_tea',     kind: 'enactment', url: IMG.enactTea,     caption: 'tea in the garden',        refs: [], comfortScore: 0.4 },
    { _id: 'en_pills',   kind: 'enactment', url: IMG.enactPills,   caption: 'the morning tablets',      refs: [], comfortScore: 0.4 },
    { _id: 'en_garden',  kind: 'enactment', url: IMG.enactGarden,  caption: 'the garden this morning',  refs: [], comfortScore: 0.4 },
    { _id: 'en_visit',   kind: 'enactment', url: IMG.enactVisit,   caption: 'a visit this afternoon',   refs: [], comfortScore: 0.4 },
    { _id: 'en_morning', kind: 'enactment', url: IMG.enactMorning, caption: 'this morning at home',     refs: [], comfortScore: 0.4 }
  ];

  const companionFace = IMG.companionFace;

  /* ── memories ─────────────────────────────────────────────────────────
     dayOffset 0 = today. Episodic memories decay in retrieval weight with
     age; semantic and procedural ones do not. */

  const M = (type, dayOffset, hhmm, content, opts) => Object.assign({
    type, dayOffset, hhmm, content, importance: 0.6, emotionalValence: 0, refs: { people: [], mediaIds: [] }
  }, opts || {});

  const memories = [
    // ── today ──
    M('episodic', 0, '09:05', 'Eleanor took her morning tablets — donepezil and vitamin D — with a glass of orange juice.', { importance: 0.95, emotionalValence: 0.1, refs: { people: [], mediaIds: ['en_pills'] } }),
    M('episodic', 0, '09:40', 'She had tea in the garden and looked at the roses by the back wall. She stayed out about twenty minutes.', { importance: 0.8, emotionalValence: 0.55, refs: { people: [], mediaIds: ['md_garden', 'en_tea'] } }),
    M('episodic', 0, '10:30', 'She played a little on the piano — the Chopin she taught for years — and got the middle section right.', { importance: 0.7, emotionalValence: 0.6, refs: { people: [], mediaIds: ['md_piano'] } }),
    M('episodic', 0, '11:15', 'Post came. A card from her neighbour Jean. She read it twice and put it on the mantelpiece.', { importance: 0.5, emotionalValence: 0.3 }),
    M('episodic', 0, '13:00', 'Lunch was soup and bread. She ate about half and left the crusts, as she usually does.', { importance: 0.55, emotionalValence: 0.05 }),
    M('episodic', 0, '14:00', 'Sarah visited at two. They had tea in the front room and talked about the grandchildren.', { importance: 0.95, emotionalValence: 0.4, refs: { people: ['Sarah'], mediaIds: ['md_sarah_tea', 'en_visit'] } }),
    M('episodic', 0, '14:35', 'Sarah raised moving to a place with more help. Eleanor did not want to talk about it and was upset afterwards. Sarah left at three, and they parted kindly.', { importance: 0.9, emotionalValence: -0.55, refs: { people: ['Sarah'], mediaIds: [] } }),
    M('episodic', 0, '15:20', 'She looked for her reading glasses for a while. They were on the windowsill in the kitchen.', { importance: 0.4, emotionalValence: -0.2, refs: { people: [], mediaIds: ['md_kitchen'] } }),
    M('episodic', 0, '16:10', 'She watched the birds on the feeder from the back window and named two of them out loud.', { importance: 0.45, emotionalValence: 0.35, refs: { people: [], mediaIds: ['md_garden'] } }),

    // ── yesterday ──
    M('episodic', 1, '09:05', 'She took her morning tablets on time.', { importance: 0.7 }),
    M('episodic', 1, '11:00', 'Tom, her grandson, rang. They spoke for about ten minutes about his new job.', { importance: 0.8, emotionalValence: 0.6, refs: { people: ['Tom'], mediaIds: ['md_grandchildren'] } }),
    M('episodic', 1, '15:30', 'She became anxious in the late afternoon and asked several times where Robert had gone.', { importance: 0.85, emotionalValence: -0.7, refs: { people: ['Robert'], mediaIds: [] } }),
    M('episodic', 1, '15:50', 'Talking about the garden settled her, and she went out to look at the roses.', { importance: 0.8, emotionalValence: 0.45, refs: { people: [], mediaIds: ['md_garden'] } }),
    M('episodic', 1, '18:30', 'She had fish and potatoes for supper and finished the plate.', { importance: 0.4 }),
    M('episodic', 1, '21:10', 'Evening tablet taken. She went up at about half nine.', { importance: 0.6 }),

    // ── two days ago ──
    M('episodic', 2, '10:00', 'Sarah took her to the hairdresser on the high street. She liked how it was set.', { importance: 0.75, emotionalValence: 0.6, refs: { people: ['Sarah'], mediaIds: [] } }),
    M('episodic', 2, '13:30', 'Alice, her granddaughter, sent photographs from her holiday. Eleanor looked at them twice.', { importance: 0.6, emotionalValence: 0.55, refs: { people: ['Alice'], mediaIds: ['md_grandchildren'] } }),
    M('episodic', 2, '16:45', 'She was frightened by a knock at the door — a delivery. It took a while to settle her.', { importance: 0.7, emotionalValence: -0.6 }),
    M('episodic', 2, '17:10', 'Playing her old recording of the sea at Whitstable brought her back around.', { importance: 0.75, emotionalValence: 0.5, refs: { people: [], mediaIds: ['md_seaside'] } }),
    M('episodic', 2, '21:00', 'Evening tablet taken with a biscuit.', { importance: 0.5 }),

    // ── three days ago ──
    M('episodic', 3, '09:15', 'Morning tablets were late — about a quarter past nine — but she took them.', { importance: 0.6 }),
    M('episodic', 3, '11:30', 'She sorted through a box of photographs and found her wedding pictures.', { importance: 0.7, emotionalValence: 0.5, refs: { people: ['Robert'], mediaIds: ['md_robert'] } }),
    M('episodic', 3, '14:20', 'Sarah came with shopping and put it away with her.', { importance: 0.65, emotionalValence: 0.4, refs: { people: ['Sarah'], mediaIds: [] } }),
    M('episodic', 3, '16:00', 'She asked about the boat several times and became low when the answers did not fit.', { importance: 0.7, emotionalValence: -0.5, refs: { people: ['Robert'], mediaIds: ['md_boat'] } }),
    M('episodic', 3, '19:00', 'She watched a programme about gardens and enjoyed it.', { importance: 0.45, emotionalValence: 0.4 }),

    // ── four days ago ──
    M('episodic', 4, '09:00', 'Morning tablets taken on time.', { importance: 0.55 }),
    M('episodic', 4, '10:45', 'Jean from next door came for coffee. They talked about the street as it used to be.', { importance: 0.7, emotionalValence: 0.6 }),
    M('episodic', 4, '15:15', 'She grew agitated before tea and paced the hall for about ten minutes.', { importance: 0.7, emotionalValence: -0.65 }),
    M('episodic', 4, '15:40', 'Sarah rang and her voice settled her quickly.', { importance: 0.8, emotionalValence: 0.55, refs: { people: ['Sarah'], mediaIds: ['md_sarah_wedding'] } }),
    M('episodic', 4, '21:05', 'Evening tablet taken.', { importance: 0.5 }),

    // ── semantic: the durable facts of her life ──
    M('semantic', 5, '00:00', 'Eleanor taught piano for thirty years at the school on Bridge Street. Music is the thing she is proudest of.', { importance: 0.95, emotionalValence: 0.7, refs: { people: [], mediaIds: ['md_piano'] } }),
    M('semantic', 5, '00:00', 'Robert was her husband. They were married fifty-one years. He died in 2022. She loved him and speaks of him often in the present tense.', { importance: 0.98, emotionalValence: -0.2, refs: { people: ['Robert'], mediaIds: ['md_robert'] } }),
    M('semantic', 5, '00:00', 'Sarah is her daughter. She is her main carer and visits most afternoons. Sarah married in 2019.', { importance: 0.97, emotionalValence: 0.6, refs: { people: ['Sarah'], mediaIds: ['md_sarah_wedding'] } }),
    M('semantic', 5, '00:00', 'Tom is her grandson and Alice her granddaughter. Tom has just started a new job.', { importance: 0.85, emotionalValence: 0.6, refs: { people: ['Tom', 'Alice'], mediaIds: ['md_grandchildren'] } }),
    M('semantic', 5, '00:00', 'She grew up in Whitstable by the sea and still talks about the smell of the salt air.', { importance: 0.85, emotionalValence: 0.65, refs: { people: [], mediaIds: ['md_seaside'] } }),
    M('semantic', 5, '00:00', 'Her garden matters to her, especially the roses by the back wall that she planted with Robert.', { importance: 0.9, emotionalValence: 0.7, refs: { people: [], mediaIds: ['md_garden'] } }),
    M('semantic', 5, '00:00', 'She takes donepezil and vitamin D at nine in the morning, and memantine at nine at night.', { importance: 0.9, emotionalValence: 0 }),
    M('semantic', 5, '00:00', 'She lives in her own home. Sarah has been raising the idea of a place with more help, which distresses her.', { importance: 0.8, emotionalValence: -0.4, refs: { people: ['Sarah'], mediaIds: [] } }),

    // ── procedural: what has been learned about handling her ──
    M('procedural', 5, '00:00', 'When she asks where Robert is, do not correct her bluntly. Move gently toward the garden they planted, or the music. Never say the word dead.', { importance: 1.0, emotionalValence: 0 }),
    M('procedural', 5, '00:00', 'The garden is the most reliable way to settle her. The boat used to work and no longer does — it has made her sad since 2024.', { importance: 0.95, emotionalValence: 0 }),
    M('procedural', 5, '00:00', "Sarah's recorded voice settles her faster than anything else, but keep it for real distress so it stays special.", { importance: 0.9, emotionalValence: 0 }),
    M('procedural', 5, '00:00', 'She becomes unsettled between four and seven in the evening. Lower the lights, keep the answers short and warm.', { importance: 0.9, emotionalValence: 0 })
  ];

  /* ── comfort strategies (procedural memory, ranked by outcome) ─────── */

  const comfortStrategies = [
    { _id: 'cs_garden', strategy: 'Mention the garden and the roses by the back wall', mediaId: 'md_garden',        timesUsed: 24, timesHelped: 21, lastUsedDay: 0 },
    { _id: 'cs_piano',  strategy: 'Talk about the piano and the years of teaching',     mediaId: 'md_piano',        timesUsed: 17, timesHelped: 13, lastUsedDay: 1 },
    { _id: 'cs_sea',    strategy: 'Bring up Whitstable and the sound of the sea',       mediaId: 'md_seaside',      timesUsed: 12, timesHelped: 9,  lastUsedDay: 2 },
    { _id: 'cs_grand',  strategy: 'Ask about Tom and Alice',                            mediaId: 'md_grandchildren',timesUsed: 14, timesHelped: 10, lastUsedDay: 1 },
    { _id: 'cs_tea',    strategy: 'Offer to make a cup of tea and sit a while',         mediaId: 'md_kitchen',      timesUsed: 19, timesHelped: 11, lastUsedDay: 0 },
    { _id: 'cs_boat',   strategy: 'Mention the boat at Whitstable',                     mediaId: 'md_boat',         timesUsed: 9,  timesHelped: 2,  lastUsedDay: 3 }
  ];

  /* ── the cloned-voice comfort messages (pre-generated, consented) ──── */

  const voiceMessages = [
    { _id: 'vm_sarah_1', voiceCloneId: 'vc_sarah', speaker: 'Sarah', mediaId: 'md_sarah_wedding',
      text: "Hi Mum, it's me, Sarah. I know it's a muddly afternoon. You're at home and you're safe, and I'll be round tomorrow. Put the kettle on and look at your roses for me." },
    { _id: 'vm_sarah_2', voiceCloneId: 'vc_sarah', speaker: 'Sarah', mediaId: 'md_sarah_tea',
      text: "Mum, it's Sarah. Everything is alright. You've had your tablets and you've had your tea. I love you. I'll see you very soon." },
    { _id: 'vm_sarah_3', voiceCloneId: 'vc_sarah', speaker: 'Sarah', mediaId: 'md_grandchildren',
      text: "Hello Mum. Tom sends his love, and Alice drew you something. Nothing to worry about today. Sit down and rest your feet." }
  ];

  /* ── seeded week of mood + interaction history ─────────────────────── */

  // Mood follows a daily arc: settled in the morning, dipping into the
  // late afternoon (sundowning), recovering after supper. Noise is seeded
  // so week-over-week trend lines are stable across reloads.
  function seedWeek() {
    const moodEvents = [], dayStats = [];
    const r = rng('week-seed');
    for (let day = 6; day >= 0; day--) {
      let episodes = 0, repeats = 0, questions = 0;
      for (let h = 7; h <= 21; h++) {
        for (let q = 0; q < 2; q++) {
          const hour = h + q * 0.5;
          // baseline arc
          let m = 0.45 - 1.35 * Math.exp(-Math.pow(hour - 17.2, 2) / 4.4);
          m += (r() - 0.5) * 0.28;
          // the week trends slightly better as the agent learns
          m += (6 - day) * 0.012;
          m = Math.max(-1, Math.min(1, m));
          if (m < -0.40) episodes++;
          moodEvents.push({
            dayOffset: day, hour,
            score: +m.toFixed(2),
            source: q === 0 ? 'vision' : 'transcript',
            labels: m < -0.45 ? ['agitated'] : m < -0.15 ? ['confused'] : ['settled']
          });
        }
        if (h >= 8) { questions += Math.round(r() * 4); repeats += Math.round(r() * 2.4); }
      }
      dayStats.push({
        dayOffset: day,
        questions, repeats,
        repetitionRate: +(repeats / Math.max(1, questions)).toFixed(2),
        agitationEpisodes: Math.max(1, Math.round(episodes / 2)),
        medAdherence: day === 3 ? 0.67 : day === 5 ? 0.67 : 1.0
      });
    }
    return { moodEvents, dayStats };
  }

  /* Interactions already logged today, before the demo starts. */
  const seededInteractions = [
    { hhmm: '09:12', patientSaid: 'Have I had my tablets?',        agentSaid: 'You have, Eleanor. You took them at five past nine with your orange juice.', intent: 'question',        mood: 0.3,  action: 'answer' },
    { hhmm: '09:48', patientSaid: 'Have I had my tablets?',        agentSaid: 'Yes, you took them this morning with your juice. All done for now.',          intent: 'repeat_question', mood: 0.25, action: 'answer', repeat: true },
    { hhmm: '10:32', patientSaid: 'I used to teach, didn’t I?',    agentSaid: 'You did — piano, for thirty years, at the school on Bridge Street.',          intent: 'question',        mood: 0.55, action: 'answer' },
    { hhmm: '12:05', patientSaid: 'Is anyone coming today?',       agentSaid: 'Sarah is coming this afternoon. She usually arrives around two.',             intent: 'question',        mood: 0.2,  action: 'answer' },
    { hhmm: '13:10', patientSaid: 'Is anyone coming today?',       agentSaid: 'Sarah will be here this afternoon. You’ll have tea together.',                intent: 'repeat_question', mood: 0.15, action: 'answer', repeat: true },
    { hhmm: '15:05', patientSaid: 'Where has Sarah gone?',         agentSaid: 'Sarah went home a little while ago. You had tea together in the front room.',  intent: 'question',        mood: -0.2, action: 'answer' },
    { hhmm: '15:22', patientSaid: 'I can’t find my glasses.',      agentSaid: 'They’re on the kitchen windowsill, by the kettle. Shall we go and look?',      intent: 'question',        mood: -0.35, action: 'answer' },
    { hhmm: '16:12', patientSaid: 'Where is Robert?',              agentSaid: 'Robert isn’t here just now. He planted those roses with you — they’re out by the wall. Shall we look at them?', intent: 'distress', mood: -0.62, action: 'reorient' }
  ];

  global.MargaretSeed = {
    patient, media, memories, comfortStrategies, voiceMessages,
    seededInteractions, seedWeek, companionFace, IMG, svgURI, rng
  };
})(window);
