const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/root/.claude/skills/synced/d6a93145-db65-4bf4-9b5f-928afa575e71_5d9aa122-6f85-4e49-bba8-254a3dc253f9/pptx/scripts/apply_theme.js");

const THEME = {
  name: "Memory Weights",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "14181F", lt1: "FFFFFF", dk2: "3A4250", lt2: "F1EEE8",
    accent1: "C2410C", accent2: "7C3AED", accent3: "0F766E",
    accent4: "F59E0B", accent5: "64748B", accent6: "FDE4D3",
    hlink: "C2410C", folHlink: "7C3AED",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Jaidev Shah";
pres.title = "Memory as Weights — Panel Prep";
const C = pres.SchemeColor;

// ---------- Layouts ----------
pres.defineSlideMaster({
  title: "DARK_TITLE",
  background: { color: THEME.colors.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.1, w: 11.7, h: 1.6, fontSize: 48, bold: true, color: C.background1, align: "left", margin: 0 } } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.9, w: 11.0, h: 1.6, fontSize: 20, color: C.accent6, align: "left", margin: 0 } } },
  ],
});
pres.defineSlideMaster({
  title: "DARK_SECTION",
  background: { color: THEME.colors.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.2, w: 11.7, h: 1.6, fontSize: 38, bold: true, color: C.background1, align: "left", margin: 0 } } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.15, w: 11.0, h: 1.4, fontSize: 20, color: C.accent6, align: "left", margin: 0 } } },
  ],
});
pres.defineSlideMaster({
  title: "LIGHT_CONTENT",
  background: { color: THEME.colors.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 0.5, w: 11.9, h: 0.85, fontSize: 26, bold: true, color: C.text1, align: "left", margin: 0 } } },
    { text: { text: "Jaidev Shah · Frontier Models in Production · Oct 5, 2026", options: { x: 0.7, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.3, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent5 },
});

// ---------- helpers ----------
function card(slide, x, y, w, h, head, body, opts = {}) {
  const fill = opts.fill || THEME.colors.lt2;
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.12, objectName: head + " card" });
  slide.addText(head, { x: x + 0.25, y: y + 0.18, w: w - 0.5, h: 0.45, fontSize: 16, bold: true, color: opts.headColor || C.accent1, margin: 0, isTextBox: true, objectName: head + " head" });
  const items = Array.isArray(body) ? body.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < body.length - 1, paraSpaceAfter: 4 } })) : body;
  slide.addText(items, { x: x + 0.25, y: y + 0.68, w: w - 0.5, h: h - 0.85, fontSize: opts.fontSize || 13, color: opts.bodyColor || C.text1, margin: 0, isTextBox: true, valign: "top", objectName: head + " body" });
}
function stat(slide, x, y, w, big, label, color) {
  slide.addText(big, { x, y, w, h: 0.9, fontSize: 40, bold: true, color: color || C.accent1, margin: 0, isTextBox: true, objectName: "stat " + big });
  slide.addText(label, { x, y: y + 0.9, w, h: 0.7, fontSize: 12, color: C.text2, margin: 0, isTextBox: true, valign: "top", objectName: "stat label " + big });
}
function talk(slide, text) {
  // "Talking point" strip at bottom
  slide.addShape(pres.ShapeType.roundRect, { x: 0.7, y: 6.05, w: 11.9, h: 0.8, fill: { color: THEME.colors.accent6 }, line: { color: THEME.colors.accent6 }, rectRadius: 0.1, objectName: "talk strip" });
  slide.addText([{ text: "Say: ", options: { bold: true, color: C.accent1 } }, { text, options: { color: C.text1 } }], { x: 0.9, y: 6.1, w: 11.5, h: 0.7, fontSize: 13, italic: true, margin: 0, isTextBox: true, valign: "middle", objectName: "talk text" });
}
function bullets(arr) { return arr.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < arr.length - 1, paraSpaceAfter: 6 } })); }

// ====================================================================
// 1. Title
pres.addSection({ title: "Open" });
let s = pres.addSlide({ masterName: "DARK_TITLE", sectionTitle: "Open" });
s.addText("Memory as Weights", { placeholder: "title" });
s.addText("Panel prep: Frontier Models in Production · Codex Community Meetup · Mon Oct 5, 2026\nJaidev Shah · Google DeepMind (personal views, not Google's)", { placeholder: "body" });
s.addText("Round 1 · continual learning  |  Round 2 · memory inside vs. outside the model  |  Round 3 · memory for help vs. ads", { x: 0.8, y: 6.3, w: 11.7, h: 0.5, fontSize: 13, color: C.accent5, margin: 0, isTextBox: true, objectName: "rounds" });
s.addNotes("Deck purpose: prep + talking points. Panel is 30 min, 3 rounds x 8 min, A/B picks per round, audience votes. Send A/B picks to Zidi before Monday.");

// 2. Warm-up + A/B picks
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Open" });
s.addText("Warm-up line and my A/B picks", { placeholder: "title" });
s.addShape(pres.ShapeType.roundRect, { x: 0.7, y: 1.5, w: 11.9, h: 1.15, fill: { color: THEME.colors.dk1 }, line: { color: THEME.colors.dk1 }, rectRadius: 0.12, objectName: "intro box" });
s.addText([{ text: "Warm-up (2 sentences): ", options: { bold: true, color: C.accent4 } }, { text: "\"I'm Jaidev, at Google DeepMind. I work on how models remember: the line between what lives in the context window, what lives in an external store, and what gets baked into the weights, and how that changes what a product can be.\"", options: { color: C.background1 } }], { x: 0.95, y: 1.6, w: 11.4, h: 0.95, fontSize: 15, margin: 0, isTextBox: true, valign: "middle", objectName: "intro text" });
const picks = [
  ["Round 1 · How fast?", "Lean A, with a caveat", "Models are a step change at the capability frontier. The gap is memory and continual learning: a model that forgets you is a demo, not a colleague."],
  ["Round 2 · Model or system", "B today, A over time", "The system wins now because memory must update live, auditably, per user. Over 3 to 5 years the winning stack trains the system's learnings back into weights."],
  ["Round 3 · Who runs it?", "B, with an A-shaped future", "Personal memory should be user-owned and portable. Ad-funded memory is coming anyway, so the design question is consent and separation of memory for help vs. memory for ads."],
];
picks.forEach((p, i) => {
  const x = 0.7 + i * 4.05, w = 3.8;
  s.addShape(pres.ShapeType.roundRect, { x, y: 2.95, w, h: 2.85, fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.lt2 }, rectRadius: 0.12, objectName: "pick card " + i });
  s.addText(p[0], { x: x + 0.25, y: 3.1, w: w - 0.5, h: 0.4, fontSize: 15, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: "pick head " + i });
  s.addText(p[1], { x: x + 0.25, y: 3.5, w: w - 0.5, h: 0.35, fontSize: 13, bold: true, color: C.accent2, margin: 0, isTextBox: true, objectName: "pick " + i });
  s.addText(p[2], { x: x + 0.25, y: 3.95, w: w - 0.5, h: 1.75, fontSize: 12.5, color: C.text1, margin: 0, isTextBox: true, valign: "top", objectName: "pick body " + i });
});
talk(s, "Picks are personal takes, not DeepMind positions. Each pick is a springboard into one story, not a debate position to defend to the death.");
s.addNotes("Guide says: pick A or B, personal take, use as springboard. Audience votes after each round, so a clear stance helps. Caveat on Round 1 is what makes the memory story land.");

// ====================================================================
// 3. The landscape map
pres.addSection({ title: "Landscape" });
s = pres.addSlide({ masterName: "DARK_SECTION", sectionTitle: "Landscape" });
s.addText("Where memory lives: three substrates", { placeholder: "title" });
s.addText("Context (working memory) · External store (notes, vectors, graphs) · Weights (parametric). Every product in 2026 is a bet on how to split across these.", { placeholder: "body" });

// 4. Three substrates comparison
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Landscape" });
s.addText("Three places to remember, three different trade-offs", { placeholder: "title" });
const cols = [
  { h: "In context", c: THEME.colors.accent3, who: "KV cache, 1M+ token windows (Gemini, Kimi K3, DeepSeek V4)", pro: ["Lossless: every token at full detail", "Zero training, instant to update", "Fully inspectable"], con: ["Wiped at session end", "Attention is >90% of the forward pass at 1M tokens", "Long-context recall still degrades"] },
  { h: "In an external store", c: THEME.colors.accent2, who: "ChatGPT / Claude / Gemini memory; Mem0, Letta, Zep; Claude Managed Agents memory + Dreaming", pro: ["Persists across sessions and models", "Human-readable: edit, delete", "~7K tokens/call vs 25K+ full-context"], con: ["Retrieval is the new bottleneck", "Staleness and contradictions", "Poisoning: OWASP ASI06"] },
  { h: "In the weights", c: THEME.colors.accent1, who: "Fine-tuning, per-user LoRA, model editing, test-time training (TTT-E2E, Titans, Hope)", pro: ["Compounds every forward pass", "Constant latency, any history", "Skills, not just facts"], con: ["Catastrophic forgetting", "Opaque: hard to audit or delete", "Serving cost: 1000 LoRAs on 13B ≈ 1.3 TB"] },
];
cols.forEach((col, i) => {
  const x = 0.7 + i * 4.05, w = 3.8;
  s.addShape(pres.ShapeType.roundRect, { x, y: 1.5, w, h: 4.4, fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.lt2 }, rectRadius: 0.12, objectName: "col " + i });
  s.addShape(pres.ShapeType.ellipse, { x: x + 0.25, y: 1.7, w: 0.42, h: 0.42, fill: { color: col.c }, line: { color: col.c }, objectName: "dot " + i });
  s.addText(String(i + 1), { x: x + 0.25, y: 1.7, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "num " + i });
  s.addText(col.h, { x: x + 0.8, y: 1.7, w: w - 1.0, h: 0.42, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, valign: "middle", objectName: "colhead " + i });
  s.addText(col.who, { x: x + 0.25, y: 2.25, w: w - 0.5, h: 0.75, fontSize: 11, italic: true, color: C.text2, margin: 0, isTextBox: true, valign: "top", objectName: "who " + i });
  s.addText("Strengths", { x: x + 0.25, y: 3.0, w: 2, h: 0.3, fontSize: 12, bold: true, color: C.accent3, margin: 0, isTextBox: true, objectName: "pro h " + i });
  s.addText(col.pro.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < 2, paraSpaceAfter: 2 } })), { x: x + 0.25, y: 3.3, w: w - 0.5, h: 1.15, fontSize: 11.5, color: C.text1, margin: 0, isTextBox: true, valign: "top", objectName: "pro " + i });
  s.addText("Weaknesses", { x: x + 0.25, y: 4.45, w: 2, h: 0.3, fontSize: 12, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: "con h " + i });
  s.addText(col.con.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < 2, paraSpaceAfter: 2 } })), { x: x + 0.25, y: 4.75, w: w - 0.5, h: 1.15, fontSize: 11.5, color: C.text1, margin: 0, isTextBox: true, valign: "top", objectName: "con " + i });
});
talk(s, "\"Context is RAM, the store is disk, weights are the OS. Everyone agrees on the metaphor; nobody agrees on what should go where.\"");
s.addNotes("Karpathy/Dwarkesh framing: Llama 3 70B trained on 15T tokens stores ~0.07 bits per token in weights, whereas the KV cache stores every token at full detail (~320KB per token). Weights are lossy compression of the world; context is lossless but ephemeral. External memory sits between.");

// 5. Timeline: what shipped
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Landscape" });
s.addText("Memory went from research topic to table stakes in 18 months", { placeholder: "title" });
const tl = [
  ["Dec 2025", "TTT-E2E & Nested Learning / Hope", "Context compressed into weights at inference; multi-timescale continuum memory. Google + NVIDIA/Stanford/Berkeley."],
  ["Feb 2026", "ChatGPT ads use memory", "Personalized ads can draw on past chats and stored memory for Free/Go users. GPT-5.3-Codex 'instrumental in creating itself'."],
  ["Mar 2026", "Claude memory for all tiers", "Automatic cross-chat synthesis every 24h; unified across Chat and Cowork; user can view/edit/delete."],
  ["May 2026", "Claude 'Dreaming'", "Managed Agents review up to 100 past sessions offline, write playbooks. No weight updates. Harvey reports 6x task completion."],
  ["Jun 2026", "Gemini Personal Intelligence; OpenAI memory refresh", "Gemini connects Gmail/Photos/Live; ChatGPT reduces stale and contradictory memories."],
  ["Now", "Memory as a market", "Mem0 at 51K+ stars, 14M downloads, AWS integration; Letta, Zep; ICLR MemAgents workshop; OWASP ASI06 memory poisoning."],
];
s.addShape(pres.ShapeType.line, { x: 1.35, y: 1.75, w: 0, h: 4.1, line: { color: THEME.colors.accent5, width: 1.5 }, objectName: "timeline axis" });
tl.forEach((t, i) => {
  const y = 1.55 + i * 0.72;
  s.addShape(pres.ShapeType.ellipse, { x: 1.22, y: y + 0.1, w: 0.26, h: 0.26, fill: { color: i === 5 ? THEME.colors.accent1 : THEME.colors.accent2 }, line: { color: THEME.colors.lt1, width: 1.5 }, objectName: "tl dot " + i });
  s.addText(t[0], { x: 0.3, y: y + 0.05, w: 0.85, h: 0.35, fontSize: 11, bold: true, color: C.accent1, align: "right", margin: 0, isTextBox: true, objectName: "tl date " + i });
  s.addText([{ text: t[1] + "  ", options: { bold: true, color: C.text1 } }, { text: t[2], options: { color: C.text2 } }], { x: 1.7, y, w: 10.9, h: 0.62, fontSize: 13, margin: 0, isTextBox: true, valign: "middle", objectName: "tl text " + i });
});
talk(s, "\"Every frontier assistant now ships cross-session memory. The differentiation moved from 'do you remember' to 'what do you do with it, and who controls it.'\"");
s.addNotes("Use this to answer Round 1 Q1 'what's newly possible'. Dates: TTT-E2E arXiv 2512.23675 (Dec 2025); Nested Learning NeurIPS 2025, arXiv 2512.24695; ChatGPT ads test Feb 9 2026; Claude Chat Memory all plans Mar 2 2026; Dreaming announced Code with Claude May 6 2026; Gemini Live memory Jun 18 2026.");

// ====================================================================
// Round 1
pres.addSection({ title: "Round 1" });
s = pres.addSlide({ masterName: "DARK_SECTION", sectionTitle: "Round 1" });
s.addText("Round 1 · How fast are frontier models really moving?", { placeholder: "title" });
s.addText("My angle: continual learning and memory across sessions. Pick: A, step change, with the caveat that the gap is learning, not reasoning.", { placeholder: "body" });

// 6. Continual learning is the bottleneck
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Round 1" });
s.addText("The step change is real; the gap is learning on the job", { placeholder: "title" });
stat(s, 0.7, 1.55, 3.6, "0.07 bits", "stored per training token in a 70B model's weights (Karpathy). Weights are a lossy sketch; context is lossless but wiped.", C.accent1);
stat(s, 4.6, 1.55, 3.6, "~10 yrs", "Karpathy's estimate to fix 'no continual learning' and related cognitive deficits (Oct 2025). Dwarkesh: the biggest bottleneck to usefulness.", C.accent2);
stat(s, 8.5, 1.55, 3.9, "Feb 2026", "OpenAI says early GPT-5.3-Codex was 'instrumental in creating itself'. RSI is in the pipeline, not yet in the deployed model.", C.accent3);
card(s, 0.7, 3.45, 5.8, 2.4, "What's newly possible (Q1)", [
  "Hours-long agent runs with memory that survives the run (Claude Managed Agents, Codex, Gemini agents)",
  "Agents that improve between sessions without retraining: Dreaming, Letta sleep-time compute, A-MEM memory tools",
  "Research models that update weights at inference: TTT-E2E matches full attention at 128K with 2.7x lower latency",
], { fontSize: 12.5 });
card(s, 6.8, 3.45, 5.8, 2.4, "What still breaks with real users (Q3)", [
  "Stale and contradictory memories: OpenAI shipped a fix in Jun 2026, it is still the top complaint",
  "Memory that locks you in: no assistant remembers you across vendors",
  "Memory poisoning: Microsoft logged 50+ real cases across 31 companies (Feb 2026); OWASP ASI06",
], { fontSize: 12.5, headColor: C.accent2 });
talk(s, "\"Benchmarks measure what a model can do in one sitting. Users judge what it remembers next Tuesday. The second number is where the frontier actually is.\"");
s.addNotes("Round 1 Q2 'what's next': continual learning. Distinguish three things that get conflated: (1) RSI = models improving the training pipeline, happening now at labs; (2) continual learning = the deployed model updating from experience, mostly in token space today; (3) memory = persistence without learning. Founders over-trust (2) and under-use (3).\nQ4 founders over-trusting or under-using: both. Over-trust the model's one-shot judgment; under-use cheap memory + eval loops that would make it reliable.");

// 7. Taxonomy of continual learning approaches
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Round 1" });
s.addText("Continual learning: token space to weight space", { placeholder: "title" });
const spec = [
  ["Token space", "Memory notes, playbooks, skills files", "Letta 'continual learning in token space'; Claude Dreaming; Claude Code memory & skills; A-MEM", "Shipping at scale", THEME.colors.accent3],
  ["Retrieved experience", "Store trajectories, retrieve on new task", "'Learning on the Job' (frozen-weights agents); experience reuse studies; MemPro evolvable memory programs", "Production pilots", THEME.colors.accent2],
  ["Lightweight parametric", "Per-user or per-task adapters, local edits", "User-as-Engram parametric edits; hypernetwork-emitted LoRA; PRISP; S-LoRA / PLoRA serving", "Research, early products", THEME.colors.accent4],
  ["Weights at inference", "Model compresses context into its own parameters", "TTT-E2E (NVIDIA/Stanford/Berkeley); Titans, Nested Learning / Hope, CMS (Google); Memoir", "Research, scaling up", THEME.colors.accent1],
];
spec.forEach((r, i) => {
  const y = 1.55 + i * 1.08;
  s.addShape(pres.ShapeType.roundRect, { x: 0.7, y, w: 11.9, h: 0.95, fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.lt2 }, rectRadius: 0.1, objectName: "spec row " + i });
  s.addShape(pres.ShapeType.roundRect, { x: 0.85, y: y + 0.15, w: 2.3, h: 0.65, fill: { color: r[4] }, line: { color: r[4] }, rectRadius: 0.08, objectName: "spec tag " + i });
  s.addText(r[0], { x: 0.85, y: y + 0.15, w: 2.3, h: 0.65, fontSize: 13, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "spec name " + i });
  s.addText(r[1], { x: 3.35, y: y + 0.1, w: 2.9, h: 0.75, fontSize: 12.5, bold: true, color: C.text1, margin: 0, isTextBox: true, valign: "middle", objectName: "spec what " + i });
  s.addText(r[2], { x: 6.4, y: y + 0.1, w: 4.3, h: 0.75, fontSize: 11.5, color: C.text2, margin: 0, isTextBox: true, valign: "middle", objectName: "spec ex " + i });
  s.addText(r[3], { x: 10.85, y: y + 0.1, w: 1.65, h: 0.75, fontSize: 11.5, italic: true, color: C.accent1, margin: 0, isTextBox: true, valign: "middle", align: "right", objectName: "spec status " + i });
});
talk(s, "\"The industry is climbing this ladder bottom-up. Token-space learning won 2026 because it is auditable and reversible. Weight-space learning wins when it compounds, and we are not there in production yet.\"");
s.addNotes("Key research refs: TTT-E2E arXiv 2512.23675: 3B models, 164B tokens, updates only the MLP layers in the last quarter of the network per chunk; scales with context like full attention while Mamba 2 and Gated DeltaNet do not; constant latency, 2.7x faster than full attention at 128K. Nested Learning (Behrouz et al., Google, NeurIPS 2025): optimizers and architectures as nested optimization problems; Hope = self-modifying Titans + Continuum Memory System where memory blocks update at different frequencies, so no single update wipes everything. 'Learning on the Job' arXiv 2607.22157; 'When Continual Learning Moves to Memory' arXiv 2604.27003 (external memory relocates the problem to retrieval budget); 'Modular Memory is the Key to Continual Learning Agents' arXiv 2603.01761 (combine in-weight and in-context learning).");

// ====================================================================
// Round 2
pres.addSection({ title: "Round 2" });
s = pres.addSlide({ masterName: "DARK_SECTION", sectionTitle: "Round 2" });
s.addText("Round 2 · Smarter model or smarter system?", { placeholder: "title" });
s.addText("My angle: memory inside vs. outside the model, open vs. closed. Pick: B today, A over time. The system is where learning happens now; the model is where it gets amortized.", { placeholder: "body" });

// 8. Inside vs outside: the decision rule
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Round 2" });
s.addText("Agentic memory or post-training? A decision rule", { placeholder: "title" });
const rows = [
  ["Changes often, per user", "Preferences, projects, names, open threads", "Outside (store)", "Must be editable and deletable; privacy law requires it"],
  ["Stable, shared across users", "Domain conventions, house style, tool quirks", "Inside (post-train)", "Amortize once, serve to everyone, cheaper per token"],
  ["Procedural skill", "How to do a task well in this harness", "Both: notes first, weights later", "Dreaming/skills capture it in text; next model release trains it in"],
  ["Needs provenance", "Anything an auditor, lawyer, or user will ask about", "Outside", "Weights cannot answer 'why did you believe that'"],
  ["Latency-critical, long history", "Months of context on every call", "Inside (TTT / compression)", "Constant-latency weight updates beat re-reading 1M tokens"],
];
s.addTable([
  [{ text: "Knowledge type", options: { bold: true, color: C.background1, fill: { color: THEME.colors.dk1 } } }, { text: "Example", options: { bold: true, color: C.background1, fill: { color: THEME.colors.dk1 } } }, { text: "Put it", options: { bold: true, color: C.background1, fill: { color: THEME.colors.dk1 } } }, { text: "Why", options: { bold: true, color: C.background1, fill: { color: THEME.colors.dk1 } } }],
  ...rows.map((r, i) => r.map((c, j) => ({ text: c, options: { bold: j === 2, color: j === 2 ? C.accent1 : C.text1, fill: { color: i % 2 ? THEME.colors.lt1 : THEME.colors.lt2 } } }))),
], { x: 0.7, y: 1.5, w: 11.9, colW: [2.5, 3.4, 2.4, 3.6], fontSize: 12, fontFace: "Calibri", border: { type: "solid", color: "FFFFFF", pt: 1 }, rowH: 0.62, valign: "middle", margin: 0.08, objectName: "decision table" });
talk(s, "\"Workflows become weights on a release cadence. Memory becomes weights on a per-user cadence only when it is cheap to serve and safe to forget. Neither is true at scale yet, so the system is the product in 2026.\"");
s.addNotes("Round 2 Q1 directly. Also Q3 'tokens cheaper, bills growing': memory is the reason. Agents re-read history; full-context costs 25K+ tokens per call vs ~7K with a memory layer (Mem0 numbers on LongMemEval: 93.4%, LoCoMo: 91.6%). Cost-aware eval ('When Does Memory Help?', arXiv 2609.05441) shows memory only pays when retrieval is budgeted. Bills grow because tasks got longer, not because tokens got dearer.");

// 9. Memory as weights: what the research actually shows
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Round 2" });
s.addText("Memory as weights: what the research shows", { placeholder: "title" });
card(s, 0.7, 1.5, 3.8, 4.35, "TTT-E2E (Dec 2025)", [
  "Model trains on its own context at inference; updates only MLP layers in the last quarter of the net",
  "Scales with context like full attention; Mamba 2 and Gated DeltaNet do not",
  "Constant latency; 2.7x faster than full attention at 128K",
  "Caveat: 3B models, 164B tokens. Not yet a frontier-scale result",
], { fontSize: 12, headColor: C.accent1 });
card(s, 4.75, 1.5, 3.8, 4.35, "Nested Learning / Hope", [
  "Architecture and optimizer as nested optimization levels, each with its own update frequency",
  "Continuum Memory System: banks that update fast (facts) to slow (abstractions)",
  "Forgetting is mitigated because nothing updates everywhere at once",
  "Beats Titans and transformers on LM perplexity and needle-in-haystack at research scale",
], { fontSize: 12, headColor: C.accent2 });
card(s, 8.8, 1.5, 3.8, 4.35, "Per-user parametric", [
  "User-as-Engram: per-user facts as local parametric edits on a frozen base",
  "Hypernetworks emit a LoRA from user history in one shot, no per-user training loop",
  "Serving reality: S-LoRA / PLoRA pool thousands of adapters; 1000 adapters on 13B at 4K ctx ≈ 1.3 TB",
  "Open problems: deletion guarantees, audit, cross-user leakage",
], { fontSize: 12, headColor: C.accent3 });
talk(s, "\"Memory as weights is the most exciting direction in the field and the least ready for production. The honest line: it works at 3B, the serving math is brutal, and nobody can yet prove a fact was deleted.\"");
s.addNotes("If asked about DeepMind specifically: speak only to published work (Titans, Nested Learning / Hope by Behrouz et al.) and say personal views. Memoir (arXiv 2607.20792) asks whether a model should write to memory while it thinks. Federated Nested Learning (2605.16350) trains self-referential memories collaboratively for test-time adaptation.");

// 10. Open vs closed + routing
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Round 2" });
s.addText("Does open routing close the gap for open models?", { placeholder: "title" });
s.addShape(pres.ShapeType.roundRect, { x: 0.7, y: 1.5, w: 5.8, h: 4.35, fill: { color: THEME.colors.dk1 }, line: { color: THEME.colors.dk1 }, rectRadius: 0.12, objectName: "open box" });
s.addText("Yes, for memory outside the model", { x: 0.95, y: 1.65, w: 5.3, h: 0.5, fontSize: 18, bold: true, color: C.accent4, margin: 0, isTextBox: true, objectName: "open head" });
s.addText(bullets([
  "A memory layer is model-agnostic by construction: the same notes feed Gemini, Claude, Kimi K3, DeepSeek V4",
  "Open weights now ship 1M context (Kimi K3 2.8T MoE, DeepSeek V4 Pro 1.6T), MLA and sparse attention (DSA in DeepSeek V3.2, GLM-5) cut KV cost",
  "If your learning lives in token space, switching models is a routing change, not a migration",
  "Letta, Mem0, Zep all pitch exactly this: portable memory, swap the brain",
]), { x: 0.95, y: 2.2, w: 5.3, h: 3.5, fontSize: 12.5, color: C.background1, margin: 0, isTextBox: true, valign: "top", objectName: "open body" });
s.addShape(pres.ShapeType.roundRect, { x: 6.8, y: 1.5, w: 5.8, h: 4.35, fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.lt2 }, rectRadius: 0.12, objectName: "closed box" });
s.addText("No, for memory inside the model", { x: 7.05, y: 1.65, w: 5.3, h: 0.5, fontSize: 18, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: "closed head" });
s.addText(bullets([
  "Weight-space memory is not portable: a LoRA or TTT state is tied to one base model",
  "Closed labs train workflows into the next release (Brenda's 'workflows becoming model features'); open models inherit them 6 to 12 months later",
  "Harness-model fit is real: the same memory layer scores differently per model, so eval per pair, not per component",
  "The moat moves from 'who has the model' to 'who has the longest learning loop with real users'",
]), { x: 7.05, y: 2.2, w: 5.3, h: 3.5, fontSize: 12.5, color: C.text1, margin: 0, isTextBox: true, valign: "top", objectName: "closed body" });
talk(s, "\"Open routing commoditizes memory outside the model. It does nothing for memory inside the model. So the question for a founder is: which kind of memory is your product?\"");
s.addNotes("Round 2 Q2 picking a model: quality, cost, speed, stability. Add 'memory compatibility': does the model follow memory notes faithfully, and does its tokenizer/context cost make your retrieval budget work. Q4 harness-model fit eval: run the same memory benchmark (LongMemEval-V2, BEAM up to 10M tokens) across model x harness pairs; note LoCoMo's answer key fails audit at 6.4% and LLM judges accept 62.8% of deliberately wrong answers, so build your own eval from real logs.");

// ====================================================================
// Round 3
pres.addSection({ title: "Round 3" });
s = pres.addSlide({ masterName: "DARK_SECTION", sectionTitle: "Round 3" });
s.addText("Round 3 · Who runs your AI, and who pays for it?", { placeholder: "title" });
s.addText("My angle: personalization design, memory for help vs. memory for ads. Pick: B, bring your own context, with the honest admission that A is what most people will get.", { placeholder: "body" });

// 11. Memory for help vs ads
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Round 3" });
s.addText("Memory for help vs. memory for ads: opposite incentives", { placeholder: "title" });
stat(s, 0.7, 1.5, 3.7, "Feb 2026", "Feb 9: ChatGPT begins ads for US Free and Go users; with Personalized Ads on, targeting can use the current thread, past chats, and memory.", C.accent1);
stat(s, 4.7, 1.5, 3.7, "Mar 2026", "Mar 2: Claude turns on automatic cross-chat memory for every plan including free, with view, edit, and delete controls.", C.accent2);
stat(s, 8.7, 1.5, 3.9, "Jun 2026", "Gemini Personal Intelligence connects Gmail, Photos, and Live; ChatGPT memory refresh targets stale and contradictory entries.", C.accent3);
card(s, 0.7, 3.5, 5.8, 2.35, "Design principles I'd defend", [
  "Two stores, two consents: memory that helps you and memory that targets you never share a table",
  "Every memory is a sentence the user can read, correct, or delete; no opaque embeddings as the source of truth",
  "Memory for help is a loyalty asset: it is the one thing a competitor cannot copy",
], { fontSize: 12.5 });
card(s, 6.8, 3.5, 5.8, 2.35, "Where trust breaks", [
  "OpenAI's own line: advertisers never see chat content. True and insufficient: the model sees it, and picks the ad",
  "Users cannot tell whether a recommendation came from memory-for-help or memory-for-ads",
  "Poisoned memory is a persistent ad: a planted note survives sessions and restarts (OWASP ASI06)",
], { fontSize: 12.5, headColor: C.accent2 });
talk(s, "\"The moment memory funds itself through ads, every 'you might like' answer is suspect. Keep help memory and ads memory in different rooms with different keys, and show the user which door the answer came through.\"");
s.addNotes("Round 3 Q3 directly. Q2 who manages context: product by default, user by right; the product curates, the user can override and export. Reference OpenAI ads principles and Sponsored Agents as Brenda's lane; stay on design, not on OpenAI's policy specifics.");

// 12. Device vs cloud
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Round 3" });
s.addText("Device or cloud? Memory local, learning central", { placeholder: "title" });
const dc = [
  ["Store (facts, prefs)", "Device-first", "Apple's 2026 SDK: ~3B on-device model answers first, cloud is fallback; local embed/store/retrieve/generate for personal data. Gemini Nano / Gemma 3n on Android.", THEME.colors.accent3],
  ["Retrieval", "Device, with cloud assist", "Index on the Neural Engine (38 TOPS on M4/A18). Hard queries go up with a minimal, consented slice.", THEME.colors.accent2],
  ["Learning into weights", "Cloud, aggregated", "Per-user adapters are too heavy to serve on a phone fleet today. Federated Nested Learning is the research path: train memories collaboratively, keep data local.", THEME.colors.accent1],
  ["Portability", "User-owned export", "No assistant remembers you across vendors in 2026. The 'bring your own context' world needs a memory file format, like a password manager for who you are.", THEME.colors.accent4],
];
dc.forEach((r, i) => {
  const y = 1.5 + i * 1.1;
  s.addShape(pres.ShapeType.roundRect, { x: 0.7, y, w: 11.9, h: 0.98, fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.lt2 }, rectRadius: 0.1, objectName: "dc row " + i });
  s.addShape(pres.ShapeType.ellipse, { x: 0.9, y: y + 0.26, w: 0.46, h: 0.46, fill: { color: r[3] }, line: { color: r[3] }, objectName: "dc dot " + i });
  s.addText(r[0], { x: 1.55, y: y + 0.1, w: 2.4, h: 0.78, fontSize: 13, bold: true, color: C.text1, margin: 0, isTextBox: true, valign: "middle", objectName: "dc what " + i });
  s.addText(r[1], { x: 4.0, y: y + 0.1, w: 2.1, h: 0.78, fontSize: 13, bold: true, color: C.accent1, margin: 0, isTextBox: true, valign: "middle", objectName: "dc where " + i });
  s.addText(r[2], { x: 6.2, y: y + 0.1, w: 6.2, h: 0.78, fontSize: 11.5, color: C.text2, margin: 0, isTextBox: true, valign: "middle", objectName: "dc why " + i });
});
talk(s, "\"Who pays? If the memory is on your device and the tokens are yours, you pay and it works for you. If the memory is in their cloud and the tokens are free, you are the inventory.\"");
s.addNotes("Round 3 Q1 and Q5. Q4 assistants as the front door for apps: yes, and memory is the doorman. Whoever holds the memory decides which app gets surfaced. That is why the store location is a business-model question, not a storage question.");

// ====================================================================
// 13. Hard questions I might get
pres.addSection({ title: "Close" });
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Close" });
s.addText("Hard questions I might get, and the short answers", { placeholder: "title" });
const qa = [
  ["Isn't 1M+ context the end of memory systems?", "No. Longer context enlarges working memory; it does not give persistence, selective retrieval over months, or governance. And attention is >90% of the forward pass at 1M tokens."],
  ["Does 'memory as weights' work today?", "At 3B scale in papers, yes. In production, memory lives in text. Weight-space memory lacks deletion guarantees and serving economics."],
  ["Why do bills grow when tokens get cheaper?", "Tasks got longer and agents re-read history. A memory layer cuts ~25K to ~7K tokens per call, so memory is a cost feature, not just a UX feature."],
  ["Should founders fine-tune or build memory?", "Build memory first, log everything, fine-tune what stops changing. Dreaming-style offline consolidation is the cheap middle step."],
  ["How do you evaluate memory?", "Not with LoCoMo alone: its answer key fails audit at 6.4%. Use LongMemEval-V2 / BEAM plus your own logs, and test the model x harness pair."],
  ["What is DeepMind doing?", "I can speak to published work: Titans, Nested Learning, Hope. Personal views only on the rest."],
];
qa.forEach((q, i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = 0.7 + col * 6.05, y = 1.5 + row * 1.5;
  s.addShape(pres.ShapeType.roundRect, { x, y, w: 5.85, h: 1.35, fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.lt2 }, rectRadius: 0.1, objectName: "qa " + i });
  s.addText(q[0], { x: x + 0.2, y: y + 0.1, w: 5.45, h: 0.35, fontSize: 13, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: "q " + i });
  s.addText(q[1], { x: x + 0.2, y: y + 0.47, w: 5.45, h: 0.82, fontSize: 11.5, color: C.text1, margin: 0, isTextBox: true, valign: "top", objectName: "a " + i });
});
talk(s, "Keep answers under 30 seconds. Audience votes after each round, so land one memorable line per round.");

// 14. Wrap-up bet + sound bites
s = pres.addSlide({ masterName: "DARK_TITLE", sectionTitle: "Close" });
s.addText("Wrap-up: my six-month bet", { placeholder: "title" });
s.addText("\"By spring, the best agents will learn from every session without a single gradient update, and the first frontier model to ship test-time weight updates will make that look quaint.\"", { placeholder: "body" });
s.addText([
  { text: "One-liners to reuse", options: { bold: true, color: C.accent4, breakLine: true } },
  { text: "Context is RAM, the store is disk, weights are the OS.", options: { bullet: true, breakLine: true, paraSpaceAfter: 4 } },
  { text: "Benchmarks measure one sitting; users judge next Tuesday.", options: { bullet: true, breakLine: true, paraSpaceAfter: 4 } },
  { text: "Open routing commoditizes memory outside the model, never inside it.", options: { bullet: true, breakLine: true, paraSpaceAfter: 4 } },
  { text: "If the tokens are free, you are the inventory.", options: { bullet: true } },
], { x: 0.8, y: 5.35, w: 11.7, h: 1.8, fontSize: 13, color: C.background1, margin: 0, isTextBox: true, valign: "top", objectName: "one liners" });
s.addNotes("Alternative bet if you want it safer: 'Memory portability becomes a product category: by spring someone ships the password manager for your AI context.'");

// 15. Sources
s = pres.addSlide({ masterName: "LIGHT_CONTENT", sectionTitle: "Close" });
s.addText("Sources", { placeholder: "title" });
const src = [
  "TTT-E2E: End-to-End Test-Time Training for Long Context, arXiv 2512.23675 (NVIDIA, Stanford, Berkeley, UCSD, Astera); The Batch summary",
  "Nested Learning: The Illusion of Deep Learning Architectures, Behrouz et al., Google, NeurIPS 2025, arXiv 2512.24695; Titans, arXiv 2501.00663",
  "Learning on the Job: Continual Learning from Deployment Feedback for Frozen-Weights Agents, arXiv 2607.22157; When Continual Learning Moves to Memory, arXiv 2604.27003",
  "Position: Modular Memory is the Key to Continual Learning Agents, arXiv 2603.01761; Letta, Continual Learning in Token Space (blog)",
  "User as Engram, arXiv 2606.19172; Instant Personalized LLM Adaptation via Hypernetwork, arXiv 2510.16282; S-LoRA (MLSys 2024); PLoRA, arXiv 2608.05483",
  "OpenAI Help Center: Ads in ChatGPT; ChatGPT release notes (Jun 2026 memory update). Engadget: Claude memory across Chat and Cowork; Anthropic Managed Agents memory beta; Claude Dreaming coverage (May 2026)",
  "9to5Google: Gemini Live memory (Jun 18 2026); Android Authority: Gemini Personal Intelligence rollout",
  "Mem0, State of AI Agent Memory 2026 and benchmark guide; LongMemEval-V2, arXiv 2605.12493; When Does Memory Help?, arXiv 2609.05441",
  "Memory poisoning: From Untrusted Input to Trusted Memory, ICML 2026, arXiv 2606.04329; OWASP Top 10 for Agentic Applications ASI06; Microsoft Threat Intelligence (Feb 2026)",
  "Dwarkesh Patel x Andrej Karpathy interview (Oct 2025); Dwarkesh on continual learning as bottleneck; CACM, Is Recursive Self-Improvement Really Here?",
];
s.addText(src.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < src.length - 1, paraSpaceAfter: 5 } })), { x: 0.7, y: 1.45, w: 11.9, h: 5.4, fontSize: 11.5, color: C.text2, margin: 0, isTextBox: true, valign: "top", objectName: "sources" });

(async () => {
  await pres.writeFile({ fileName: "memory-as-weights-panel-prep.pptx" });
  await applyTheme("memory-as-weights-panel-prep.pptx", THEME);
  console.log("done");
})();
