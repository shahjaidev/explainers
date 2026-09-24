"""MiMo-V2.6 RL — a 3Blue1Brown-style explainer.

Render (Manim Community 0.21, no LaTeX needed; uses the CMU fonts):
    manim -qh explainer.py MiMoRL          # 1080p30
    manim -ql explainer.py MiMoRL          # quick 480p preview

Numbers come from the MiMo-V2.6 technical report ("Scaling Reinforcement
Learning Towards Self-Improvement") and the live RL dashboard at
mimo.xiaomi.com/rl. Anything drawn as a curve without a quoted number is
labelled "schematic" on screen.
"""

from manim import *
import numpy as np

config.background_color = "#0c0f14"

FONT = "CMU Serif"
MONO = "CMU Typewriter Text"
SYM = "DejaVu Sans"

BLUE_3B = "#58C4DD"
YELLOW_3B = "#F4D35E"
GREEN_3B = "#83C167"
RED_3B = "#FC6255"
TEAL_3B = "#5CD0B3"
PURPLE_3B = "#9A72AC"
ORANGE_3B = "#F39C4A"
DIM = "#6b7280"


def T(s, size=36, color=WHITE, font=FONT, **kw):
    return Text(s, font=font, font_size=size, color=color, **kw)


class MiMoRL(Scene):
    # ------------------------------------------------------------ helpers
    def setup(self):
        self.cap = None
        self.cap_start = 0.0
        self.cap_need = 0.0
        self.header = None

    def now(self):
        return self.renderer.time

    def say(self, text, pad=0.8):
        """Show a narration caption; settle() later waits until it has been readable long enough."""
        self.settle()
        cap = T(text, 27, GREY_A, line_spacing=0.9)
        if cap.width > 12.6:
            cap.scale_to_fit_width(12.6)
        cap.to_edge(DOWN, buff=0.3)
        if self.cap is not None:
            self.play(FadeOut(self.cap, shift=UP * 0.08), FadeIn(cap, shift=UP * 0.08), run_time=0.45)
        else:
            self.play(FadeIn(cap, shift=UP * 0.08), run_time=0.45)
        self.cap = cap
        self.cap_start = self.now()
        self.cap_need = len(text.split()) / 2.7 + pad

    def settle(self):
        left = self.cap_need - (self.now() - self.cap_start)
        if left > 0.05:
            self.wait(left)
        self.cap_need = 0.0

    def chapter(self, num, title):
        h = VGroup(
            T(f"{num:02d}", 26, BLUE_3B, font=MONO),
            T(title, 30, WHITE),
        ).arrange(RIGHT, buff=0.3)
        h.to_corner(UL, buff=0.4)
        line = Line(h.get_left(), h.get_left() + RIGHT * 13.2, stroke_width=1, color=DIM)
        line.next_to(h, DOWN, buff=0.15, aligned_edge=LEFT)
        grp = VGroup(h, line)
        self.play(FadeIn(h, shift=RIGHT * 0.2), Create(line), run_time=0.8)
        self.header = grp
        return grp

    def clear_all(self):
        self.settle()
        mobs = [m for m in self.mobjects]
        if mobs:
            self.play(*[FadeOut(m) for m in mobs], run_time=0.7)
        self.cap = None
        self.header = None

    def dial(self, label, color, radius=1.0):
        arc = Arc(radius=radius, start_angle=PI, angle=-PI, stroke_width=6, color=GREY_D)
        ticks = VGroup()
        for k in range(11):
            a = PI - k * PI / 10
            d = np.array([np.cos(a), np.sin(a), 0])
            ticks.add(Line(d * radius * 0.86, d * radius * (1.0 if k % 5 else 1.08), stroke_width=2, color=GREY_B))
        needle = Line(ORIGIN, LEFT * radius * 0.85, stroke_width=5, color=color)
        hub = Dot(ORIGIN, radius=0.07, color=color)
        lab = T(label, 28, color).next_to(arc, DOWN, buff=0.35)
        g = VGroup(arc, ticks, needle, hub, lab)
        g.needle = needle
        g.hub = hub
        return g

    # ------------------------------------------------------------ chapters
    def construct(self):
        self.intro()
        self.loop_and_grpo()
        self.scale_numbers()
        self.asynchrony()
        self.yoro()
        self.grading()
        self.stability()
        self.results()
        self.recap()

    # 00 ----------------------------------------------------------------
    def intro(self):
        title = T("MiMo-V2.6", 84)
        sub = T("Scaling Reinforcement Learning Towards Self-Improvement", 32, GREY_B)
        by = T("Xiaomi MiMo  ·  technical report + live RL dashboard", 24, DIM)
        g = VGroup(title, sub, by).arrange(DOWN, buff=0.35)
        self.play(Write(title), run_time=1.6)
        self.play(FadeIn(sub, shift=UP * 0.2), FadeIn(by, shift=UP * 0.2))
        self.wait(1.8)
        self.play(g.animate.scale(0.55).to_edge(UP, buff=0.35), run_time=1.0)

        dials = VGroup(
            self.dial("RL compute", BLUE_3B),
            self.dial("environment diversity", GREEN_3B),
            self.dial("grader compute", YELLOW_3B),
        ).arrange(RIGHT, buff=1.3).shift(UP * 0.25)
        self.play(LaggedStart(*[FadeIn(d) for d in dials], lag_ratio=0.25))
        self.say("Most reinforcement-learning recipes turn one knob: more steps, more rollouts.")
        self.play(Rotate(dials[0].needle, -PI * 0.55, about_point=dials[0].hub.get_center()), run_time=1.5)
        self.say("MiMo-V2.6 turns three knobs together: how much RL compute,\nhow many kinds of environments, and how much compute goes into grading.")
        self.play(
            Rotate(dials[0].needle, -PI * 0.35, about_point=dials[0].hub.get_center()),
            Rotate(dials[1].needle, -PI * 0.85, about_point=dials[1].hub.get_center()),
            Rotate(dials[2].needle, -PI * 0.85, about_point=dials[2].hub.get_center()),
            run_time=2.2,
        )
        tag = VGroup(
            T("one run", 28, WHITE), T("·", 28, DIM), T("streamed live", 28, WHITE), T("·", 28, DIM),
            T("open weights, code and environments", 28, WHITE),
        ).arrange(RIGHT, buff=0.25).next_to(dials, DOWN, buff=0.6)
        url = T("mimo.xiaomi.com/rl", 24, BLUE_3B, font=MONO).next_to(tag, DOWN, buff=0.2)
        self.play(FadeIn(tag, shift=UP * 0.15))
        self.play(FadeIn(url))
        self.say("And they did it in public: every training step appeared on a live dashboard.\nLet's walk through the ideas that made it work.")
        self.clear_all()

    # 01 ----------------------------------------------------------------
    def loop_and_grpo(self):
        self.chapter(1, "The basic loop: group-relative advantages")
        prompt = VGroup(
            RoundedRectangle(width=2.2, height=1.1, corner_radius=0.15, color=BLUE_3B),
            T("prompt", 30, BLUE_3B),
        )
        prompt[1].move_to(prompt[0])
        prompt.move_to(LEFT * 5.4 + UP * 1.2)
        self.play(FadeIn(prompt))
        self.say("Start with one task: a prompt plus an environment the model can act in.")

        rewards = [1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0]
        cells = VGroup()
        for r in rewards:
            box = RoundedRectangle(width=0.5, height=0.5, corner_radius=0.08, stroke_width=2,
                                   color=GREEN_3B if r else RED_3B,
                                   fill_opacity=0.25)
            lab = T(str(r), 24, WHITE).move_to(box)
            cells.add(VGroup(box, lab))
        cells.arrange(RIGHT, buff=0.1).move_to(RIGHT * 1.0 + UP * 1.2)
        arrow = Arrow(prompt.get_right(), cells.get_left(), buff=0.2, color=GREY_B)
        g_lab = T("G = 16 rollouts", 26, GREY_B).next_to(cells, UP, buff=0.3)
        self.play(GrowArrow(arrow), FadeIn(g_lab))
        self.say("The policy attempts it 16 times. Each attempt is graded: here, pass = 1, fail = 0.")
        self.play(LaggedStart(*[FadeIn(c, shift=RIGHT * 0.2) for c in cells], lag_ratio=0.06), run_time=2)

        formula = T("Aᵢ  =  ( rᵢ − mean(r) ) / std(r)", 34, YELLOW_3B).move_to(DOWN * 0.05)
        self.say("GRPO needs no value network. Each attempt is scored against its own siblings:\nbetter than the group average gets pushed up, worse gets pushed down.")
        self.play(Write(formula))

        base_y = -1.45
        baseline = DashedLine(cells.get_left() + DOWN * 0 + UP * (base_y - 1.2), cells.get_right() + UP * (base_y - 1.2),
                              color=GREY_B, dash_length=0.08)
        baseline.set_y(base_y)
        r = np.array(rewards, dtype=float)
        adv = (r - r.mean()) / r.std()
        bars = VGroup()
        for c, a in zip(cells, adv):
            h = abs(a) * 0.55
            bar = Rectangle(width=0.36, height=max(h, 0.01), stroke_width=0,
                            fill_color=GREEN_3B if a > 0 else RED_3B, fill_opacity=0.85)
            bar.move_to([c.get_x(), base_y + (h / 2 if a > 0 else -h / 2), 0])
            bars.add(bar)
        adv_lab = T("advantage", 24, GREY_B).next_to(baseline, LEFT, buff=0.3)
        self.play(Create(baseline), FadeIn(adv_lab))
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN if a > 0 else UP) for b, a in zip(bars, adv)], lag_ratio=0.04), run_time=1.6)

        self.say("Now the catch. What if all 16 attempts pass?")
        self.play(*[c[0].animate.set_color(GREEN_3B) for c in cells],
                  *[Transform(c[1], T("1", 24, WHITE).move_to(c[1])) for c in cells], run_time=1.0)
        flat = VGroup(*[Rectangle(width=0.36, height=0.01, stroke_width=0, fill_color=GREY_B, fill_opacity=1).move_to([b.get_x(), base_y, 0]) for b in bars])
        self.play(Transform(bars, flat), run_time=1.0)
        zero = T("every advantage = 0   →   zero gradient", 30, RED_3B).next_to(baseline, DOWN, buff=0.35)
        self.play(FadeIn(zero, shift=UP * 0.1))
        self.say("Every advantage is zero. The same happens if all 16 fail.\nThose rollouts cost real compute and teach the model nothing.")
        self.clear_keep_header()

        # dynamic sampler
        self.say("So the run uses a dynamic sampler. It keeps pulling prompt groups and throws away\nthe all-fail and all-pass ones until the batch holds 1,568 useful prompts.")
        bins = VGroup()
        specs = [("all fail", "≈15% of prompts", RED_3B), ("mixed: kept", "learning signal", GREEN_3B), ("all pass", "≈23% of prompts", GREY_B)]
        for name, sub, col in specs:
            box = RoundedRectangle(width=3.3, height=2.3, corner_radius=0.2, color=col)
            t1 = T(name, 30, col)
            t2 = T(sub, 22, GREY_B)
            VGroup(t1, t2).arrange(DOWN, buff=0.12).next_to(box.get_top(), DOWN, buff=0.25)
            bins.add(VGroup(box, t1, t2))
        bins.arrange(RIGHT, buff=0.7).shift(DOWN * 0.9)
        self.play(FadeIn(bins))

        def glyph(kind):
            cols = {"fail": [RED_3B] * 8, "pass": [GREEN_3B] * 8}.get(kind)
            if cols is None:
                cols = [GREEN_3B if k in (0, 3, 4, 6) else RED_3B for k in range(8)]
            return VGroup(*[Square(0.13, stroke_width=0, fill_color=c, fill_opacity=0.9) for c in cols]).arrange(RIGHT, buff=0.03)

        counter_t = ValueTracker(0)
        counter = always_redraw(lambda: T(f"accepted  {int(counter_t.get_value()):,}  /  1,568", 30, WHITE, font=MONO).move_to(UP * 1.75))
        self.add(counter)
        kinds = ["mix", "fail", "mix", "pass", "mix", "mix", "pass", "fail", "mix", "mix", "pass", "mix"]
        dest = {"fail": 0, "mix": 1, "pass": 2}
        source = UP * 0.9
        stacks = [0, 0, 0]
        anims = []
        for i, k in enumerate(kinds):
            gl = glyph(k).move_to(source)
            j = dest[k]
            col = stacks[j] // 4
            n_cols = 2 if kinds.count(k) > 4 else 1
            x_off = (col - (n_cols - 1) / 2) * 1.4
            target = bins[j][0].get_bottom() + UP * (0.3 + 0.2 * (stacks[j] % 4)) + RIGHT * x_off
            stacks[j] += 1
            anims.append(Succession(FadeIn(gl, run_time=0.15), gl.animate(run_time=0.55).move_to(target)))
        self.play(LaggedStart(*anims, lag_ratio=0.35), counter_t.animate.set_value(1568), run_time=5.5, rate_func=linear)
        self.say("Only groups with some passes and some failures survive:\nthe prompts sitting right at the edge of what the model can currently do.")
        self.clear_all()

    def clear_keep_header(self):
        self.settle()
        keep = set(self.header.get_family()) if self.header is not None else set()
        mobs = [m for m in self.mobjects if m not in keep and m is not self.cap]
        if mobs:
            self.play(*[FadeOut(m) for m in mobs], run_time=0.6)

    # 02 ----------------------------------------------------------------
    def scale_numbers(self):
        self.chapter(2, "How big is one step?")
        grid = VGroup(*[Square(0.075, stroke_width=0, fill_color=BLUE_3B, fill_opacity=0.85) for _ in range(1568)])
        grid.arrange_in_grid(rows=32, cols=49, buff=0.03).move_to(LEFT * 4.1 + UP * 0.35)
        self.play(LaggedStart(*[FadeIn(s) for s in grid], lag_ratio=0.0015), run_time=2.0)
        lab = T("1,568 prompts", 30, BLUE_3B).next_to(grid, DOWN, buff=0.25)
        self.play(FadeIn(lab))
        self.say("One optimisation step: 1,568 prompts, each attempted 16 times.")

        shadows = VGroup(*[grid.copy().set_opacity(0.18 - 0.012 * k).shift((k + 1) * 0.06 * (UR)) for k in range(6)])
        self.play(LaggedStart(*[FadeIn(s) for s in shadows], lag_ratio=0.15), run_time=1.2)

        rows = VGroup(
            T("1,568 × 16", 36, WHITE), T("=  25,088 trajectories", 36, YELLOW_3B),
            T("× ≈110K–150K tokens each", 30, GREY_B), T("≈  2.7–3.7 B tokens per step", 36, YELLOW_3B),
            T("contexts up to 1M tokens", 30, GREY_B), T("", 10),
        )
        eq = VGroup(
            VGroup(rows[0], rows[1]).arrange(RIGHT, buff=0.25),
            rows[2],
            rows[3],
            rows[4],
        ).arrange(DOWN, buff=0.35, aligned_edge=LEFT)
        if eq.width > 6.2:
            eq.scale_to_fit_width(6.2)
        eq.next_to(grid, RIGHT, buff=0.9).shift(UP * 0.1)
        self.play(Write(eq[0]))
        self.say("That's about 25 thousand agent trajectories per step,\nmost of them long, multi-turn tool use.")
        self.play(FadeIn(eq[1], shift=UP * 0.1))
        self.play(Write(eq[2]))
        self.say("Billions of tokens go into every single gradient update.")
        self.play(FadeIn(eq[3], shift=UP * 0.1))
        self.clear_keep_header()

        # compute split donut
        parts = [("rollouts", 43.8, BLUE_3B), ("training", 43.5, GREEN_3B), ("grading", 12.7, YELLOW_3B)]
        start = PI / 2
        donut = VGroup()
        labels = VGroup()
        center = LEFT * 3.4 + DOWN * 0.25
        for name, pct, col in parts:
            ang = -2 * PI * pct / 100
            sec = AnnularSector(inner_radius=0.85, outer_radius=1.6, angle=ang, start_angle=start,
                                fill_color=col, fill_opacity=0.85, stroke_color=config.background_color, stroke_width=4)
            sec.shift(center)
            mid = start + ang / 2
            d = np.array([np.cos(mid), np.sin(mid), 0])
            lt = VGroup(T(name, 26, col), T(f"{pct}%", 26, WHITE)).arrange(DOWN, buff=0.08)
            lt.move_to(center + d * 2.3)
            donut.add(sec)
            labels.add(lt)
            start += ang
        title = T("where the RL compute went (Pro)", 24, GREY_B).move_to([center[0], 2.5, 0])
        self.play(FadeIn(title), LaggedStart(*[Create(s) for s in donut], lag_ratio=0.3), run_time=2.0)
        self.play(LaggedStart(*[FadeIn(l) for l in labels], lag_ratio=0.2))
        self.say("Where did the compute go? Rollouts and training split it almost evenly,\nand grading got a real share: about one dollar in eight.")

        cost_t = T("total RL bill", 26, GREY_B)
        def cost_row(name, amt, col, y):
            nm = T(name, 28, WHITE)
            nm.move_to([1.2, y, 0], aligned_edge=LEFT)
            bar = Rectangle(width=amt * 1.15, height=0.45, stroke_width=0, fill_color=col, fill_opacity=0.9)
            bar.move_to([2.4 + bar.width / 2, y, 0])
            lab = T(f"${amt}M", 28, col).next_to(bar, RIGHT, buff=0.25)
            return VGroup(nm, bar, lab)
        pro = cost_row("Pro", 2.6, BLUE_3B, 0.2)
        fl = cost_row("Flash", 0.9, TEAL_3B, -0.5)
        cost_t.move_to([1.2, 0.95, 0], aligned_edge=LEFT)
        self.play(FadeIn(cost_t), GrowFromEdge(pro[1], LEFT), FadeIn(pro[0]), FadeIn(pro[2]))
        self.play(GrowFromEdge(fl[1], LEFT), FadeIn(fl[0]), FadeIn(fl[2]))
        self.say("The whole run cost about 2.6 million dollars for Pro and 0.9 million for Flash.\nSpending grader compute on purpose is one of the paper's central bets.")
        self.clear_all()

    # 03 ----------------------------------------------------------------
    def asynchrony(self):
        self.chapter(3, "Fully asynchronous RL")
        lens = [2.2, 3.4, 1.6, 7.6, 2.8]
        x0 = -5.2
        rows = VGroup()
        idle = VGroup()
        tmax = max(lens)
        for i, L in enumerate(lens):
            y = 1.6 - i * 0.55
            bar = Rectangle(width=L, height=0.34, stroke_width=0, fill_color=BLUE_3B, fill_opacity=0.85)
            bar.move_to([x0 + L / 2, y, 0])
            rows.add(bar)
            if L < tmax:
                gap = Rectangle(width=tmax - L, height=0.34, stroke_width=1, stroke_color=GREY_D, fill_color=GREY_D, fill_opacity=0.25)
                gap.move_to([x0 + L + (tmax - L) / 2, y, 0])
                idle.add(gap)
        wl = T("rollout workers", 22, GREY_B).next_to(rows, LEFT, buff=0.25).shift(LEFT * 0.0)
        wl.rotate(PI / 2).next_to(rows, LEFT, buff=0.2)
        train = Rectangle(width=1.4, height=0.34, stroke_width=0, fill_color=GREEN_3B, fill_opacity=0.9)
        train.move_to([x0 + tmax + 0.7, 1.6 - 5 * 0.55 - 0.15, 0])
        tl = T("train", 22, GREEN_3B).next_to(train, RIGHT, buff=0.15)
        sync_t = T("synchronous", 28, WHITE).move_to(UP * 2.35 + RIGHT * 4.3)
        self.play(FadeIn(sync_t), FadeIn(wl))
        self.say("Agent rollouts have a long tail.\nMost finish quickly; a few run toward a million tokens.")
        self.play(LaggedStart(*[GrowFromEdge(b, LEFT) for b in rows], lag_ratio=0.1), run_time=2.0)
        self.play(FadeIn(idle), GrowFromEdge(train, LEFT), FadeIn(tl))
        idle_lab = T("idle GPUs, waiting on the slowest rollout", 24, GREY_B).next_to(idle, DOWN, buff=0.15).align_to(idle, RIGHT).shift(DOWN * 0.45 + LEFT * 0.4)
        self.play(FadeIn(idle_lab))
        self.say("In synchronous RL, everyone waits for the slowest trajectory before training.\nAt this scale, that gray area is millions of dollars.")
        self.clear_keep_header()

        # async: in-flight weight updates, one long trajectory colored by version
        async_t = T("asynchronous: weights update while rollouts are still running", 28, WHITE).move_to(UP * 2.2)
        self.play(FadeIn(async_t))
        n = 40
        vers = [0] * 18 + [1] * 12 + [2] * 10
        vcol = [PURPLE_3B, BLUE_3B, YELLOW_3B]
        toks = VGroup(*[Square(0.26, stroke_width=0, fill_color=vcol[v], fill_opacity=0.9) for v in vers]).arrange(RIGHT, buff=0.04)
        toks.move_to(UP * 0.95)
        self.say("MiMo-V2.6 never stops generating. New weights are pushed to the inference engines\nmid-rollout, so one long trajectory can be written by several policy versions.")
        self.play(LaggedStart(*[FadeIn(t) for t in toks], lag_ratio=0.03), run_time=2.0)
        legend = VGroup(*[
            VGroup(Square(0.22, stroke_width=0, fill_color=c, fill_opacity=0.9), T(f"policy v{k + 1}", 22, GREY_B)).arrange(RIGHT, buff=0.12)
            for k, c in enumerate(vcol)
        ]).arrange(RIGHT, buff=0.6).next_to(toks, UP, buff=0.3)
        self.play(FadeIn(legend))

        br1 = Brace(toks[:18], DOWN, color=GREY_B)
        br2 = Brace(toks[18:], DOWN, color=YELLOW_3B)
        l1 = T("stale prefix: kept as context, masked from the loss", 22, GREY_B).next_to(br1, DOWN, buff=0.12)
        l2 = T("fresh tokens: 22 / 40 = 55%", 22, YELLOW_3B).next_to(br2, DOWN, buff=0.12)
        self.say("Each token is stamped with the policy version that produced it. A gateway admits a\ntrajectory only if enough of its tokens are fresh; the stale prefix is masked from the loss.")
        self.play(GrowFromCenter(br2), FadeIn(l2))
        self.play(GrowFromCenter(br1), FadeIn(l1), toks[:18].animate.set_opacity(0.3))
        self.settle()
        self.play(FadeOut(VGroup(br1, br2, l1, l2)), run_time=0.5)

        # double-sided IS
        nl = NumberLine(x_range=[0, 2.4, 0.5], length=9, include_numbers=False, color=GREY_B).move_to(DOWN * 1.5)
        nums = VGroup(*[T(f"{v:g}", 22, GREY_B).next_to(nl.n2p(v), DOWN, buff=0.15) for v in [0, 0.5, 1, 1.5, 2]])
        lo, hi = 0.8, 1.28
        band = Rectangle(width=nl.n2p(hi)[0] - nl.n2p(lo)[0], height=0.5, stroke_width=0, fill_color=GREEN_3B, fill_opacity=0.18)
        band.move_to([(nl.n2p(lo)[0] + nl.n2p(hi)[0]) / 2, nl.get_y(), 0])
        rl = T("per-token ratio   rₜ = π_train(token) / π_rollout(token)", 26, WHITE).next_to(nl, UP, buff=0.55)
        self.play(FadeOut(async_t), Create(nl), FadeIn(nums), FadeIn(rl))
        self.say("Rollout and trainer policies differ, so every token gets an importance ratio.\nMiMo bounds it on both sides, so no single off-policy token can dominate the update.")
        rng = np.random.default_rng(3)
        vals = np.concatenate([rng.normal(1.0, 0.12, 14), [0.35, 0.55, 1.7, 2.1, 1.55, 0.6]])
        dots = VGroup(*[Dot(nl.n2p(v) + UP * 0.0, radius=0.07, color=YELLOW_3B if lo <= v <= hi else RED_3B) for v in vals])
        self.play(FadeIn(band), LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.05), run_time=1.5)
        clipped = [d.animate.move_to(nl.n2p(np.clip(v, lo, hi))).set_color(ORANGE_3B) for d, v in zip(dots, vals) if not (lo <= v <= hi)]
        self.play(*clipped, run_time=1.2)
        bl = T("bounded on both sides", 24, GREEN_3B).next_to(band, DOWN, buff=0.55)
        self.play(FadeIn(bl))
        self.clear_all()

    # 04 ----------------------------------------------------------------
    def yoro(self):
        self.chapter(4, "You Only RL Once")
        left_t = T("the usual recipe", 28, GREY_B).move_to(LEFT * 3.6 + UP * 2.1)
        right_t = T("MiMo-V2.6", 28, WHITE).move_to(RIGHT * 3.6 + UP * 2.1)
        doms = [("code", BLUE_3B), ("visual", PURPLE_3B), ("agent", GREEN_3B), ("cyber", RED_3B)]
        runs = VGroup(*[
            VGroup(RoundedRectangle(width=1.35, height=0.6, corner_radius=0.1, color=c), T(n, 22, c)) for n, c in doms
        ])
        for r in runs:
            r[1].move_to(r[0])
        runs.arrange(RIGHT, buff=0.15).move_to(LEFT * 3.6 + UP * 1.1)
        merge = RoundedRectangle(width=2.3, height=0.6, corner_radius=0.1, color=GREY_B)
        merge_t = T("merge experts", 22, GREY_B).move_to(merge)
        mg = VGroup(merge, merge_t).move_to(LEFT * 3.6 + DOWN * 0.6)
        arrows = VGroup(*[Arrow(r.get_bottom(), mg.get_top(), buff=0.1, stroke_width=2, color=GREY_D, max_tip_length_to_length_ratio=0.12) for r in runs])
        self.play(FadeIn(left_t), FadeIn(runs))
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.1), FadeIn(mg))
        self.say("A common recipe trains a separate specialist per domain,\nthen merges or distils them.")

        # mixed batch mosaic
        shares = [("code", 68, BLUE_3B), ("visual", 13, PURPLE_3B), ("general agent", 12, GREEN_3B), ("cyber", 4, RED_3B), ("chat", 3, TEAL_3B)]
        order = []
        for _, k, c in shares:
            order += [c] * k
        rng = np.random.default_rng(7)
        rng.shuffle(order)
        mosaic = VGroup(*[Square(0.27, stroke_width=0, fill_color=c, fill_opacity=0.9) for c in order])
        mosaic.arrange_in_grid(rows=10, cols=10, buff=0.04).move_to(RIGHT * 2.1 + DOWN * 0.1)
        self.play(FadeIn(right_t), LaggedStart(*[FadeIn(s) for s in mosaic], lag_ratio=0.01), run_time=2.0)
        leg = VGroup(*[
            VGroup(Square(0.2, stroke_width=0, fill_color=c, fill_opacity=0.9), T(f"{n}  {k}%", 20, GREY_B)).arrange(RIGHT, buff=0.12)
            for n, k, c in shares
        ]).arrange(DOWN, buff=0.16, aligned_edge=LEFT).next_to(mosaic, RIGHT, buff=0.35)
        self.play(FadeIn(leg))
        one = T("one run · one mixed batch · 50 datasets", 24, WHITE).next_to(mosaic, DOWN, buff=0.3)
        self.play(FadeIn(one))
        self.say("MiMo-V2.6 does one run. Every batch mixes all 50 datasets:\nroughly two-thirds code, the rest visual, general agent, cybersecurity and chat.")
        self.say("Skills learned in one domain get to reinforce the others inside the same update,\ninstead of being stitched together afterwards.")
        self.clear_keep_header()

        # harnesses
        self.say("There's a second kind of diversity: the harness. A harness is the scaffolding\naround the model: its system prompt, its tools, and how context is managed.")
        piece_names = [("system prompt", BLUE_3B), ("tools", GREEN_3B), ("context mgmt", YELLOW_3B)]

        def harness(variant, label, col=WHITE):
            parts = VGroup()
            for k, (n, c) in enumerate(piece_names):
                w = [1.6, 1.1, 1.5][k] + 0.25 * ((variant + k) % 3 - 1)
                parts.add(VGroup(Rectangle(width=w, height=0.42, stroke_width=0, fill_color=c, fill_opacity=0.25 + 0.2 * ((variant * 2 + k) % 3)),))
            parts.arrange(RIGHT, buff=0.05)
            lab = T(label, 22, col).next_to(parts, LEFT, buff=0.25)
            return VGroup(lab, parts)

        key = VGroup(*[VGroup(Square(0.2, stroke_width=0, fill_color=c, fill_opacity=0.7), T(n, 20, GREY_B)).arrange(RIGHT, buff=0.1) for n, c in piece_names]).arrange(RIGHT, buff=0.5).move_to(UP * 2.0)
        hs = VGroup(*[harness(v, f"train harness {v + 1}") for v in range(4)]).arrange(DOWN, buff=0.18, aligned_edge=RIGHT).move_to(LEFT * 3.2 + UP * 0.1)
        held = harness(5, "held-out harness", YELLOW_3B).next_to(hs, DOWN, buff=0.45, aligned_edge=RIGHT)
        self.play(FadeIn(key), LaggedStart(*[FadeIn(h, shift=RIGHT * 0.2) for h in hs], lag_ratio=0.15))
        self.say("They train across many lightweight, composable mini-harnesses in the same batch,\nand check performance on harnesses the model never trained on.")
        self.play(FadeIn(held, shift=UP * 0.1))

        ax = Axes(x_range=[0, 10, 2], y_range=[0, 10, 2], x_length=4.6, y_length=2.9, tips=False,
                  axis_config={"color": GREY_D, "include_ticks": False}).move_to(RIGHT * 3.6 + DOWN * 0.1)
        xl = T("RL steps", 20, GREY_B).next_to(ax, DOWN, buff=0.12)
        yl = T("score", 20, GREY_B).rotate(PI / 2).next_to(ax, LEFT, buff=0.12)
        c_train = ax.plot(lambda x: 3.0 + 5.5 * (1 - np.exp(-x / 3.5)), color=WHITE)
        c_held = ax.plot(lambda x: 1.6 + 6.4 * (1 - np.exp(-x / 3.2)), color=YELLOW_3B)
        lt = T("train harnesses", 20, WHITE).next_to(ax.c2p(10, 8.5), UP, buff=0.12).shift(LEFT * 0.6)
        lh = T("held-out", 20, YELLOW_3B).next_to(ax.c2p(10, 7.9), DOWN, buff=0.12).shift(LEFT * 0.4)
        sch = T("schematic", 18, DIM).next_to(ax, UP, buff=0.1).align_to(ax, RIGHT)
        self.play(Create(ax), FadeIn(xl), FadeIn(yl), FadeIn(sch))
        self.play(Create(c_train), Create(c_held), run_time=2.0)
        self.play(FadeIn(lt), FadeIn(lh))
        self.say("The gap between trained and held-out harnesses narrows as RL goes on:\nthe coding skill transfers across scaffolds rather than overfitting to one.")
        self.clear_all()

    # 05 ----------------------------------------------------------------
    def grading(self):
        self.chapter(5, "Groupwise agentic grading")
        specs = [("A", 2.0, "clean fix"), ("B", 3.6, "fix + detours"), ("C", 6.2, "flails, then passes"), ("D", 3.0, "fix, untested")]
        rows = VGroup()
        for name, L, desc in specs:
            n = T(name, 28, WHITE)
            bar = Rectangle(width=L, height=0.38, stroke_width=0, fill_color=BLUE_3B, fill_opacity=0.8)
            d = T(desc, 20, GREY_B)
            chk = T("✓ pass → r = 1", 22, GREEN_3B, font=SYM)
            rows.add(VGroup(n, bar, d, chk))
        for i, r in enumerate(rows):
            y = 1.75 - i * 0.55
            r[0].move_to([-6.0, y, 0])
            r[1].move_to([-5.6 + r[1].width / 2, y, 0])
            r[2].next_to(r[1], RIGHT, buff=0.2)
            r[3].move_to([4.9, y, 0])
        tl = T("trajectory length", 20, DIM).next_to(rows[0][1], UP, buff=0.25).align_to(rows[0][1], LEFT)
        self.play(FadeIn(tl), LaggedStart(*[FadeIn(r[:3], shift=RIGHT * 0.2) for r in rows], lag_ratio=0.15))
        self.play(LaggedStart(*[FadeIn(r[3]) for r in rows], lag_ratio=0.1))
        self.say("Four attempts at the same task. All four pass the tests, so a pass/fail grader\ngives them identical reward, and GRPO gives them identical advantage.")
        self.say("Nothing tells the model that A is better than C. Worse: long, flailing trajectories\nare never penalised, so length and turn counts drift upward.")

        grader = VGroup(RoundedRectangle(width=3.0, height=0.8, corner_radius=0.15, color=YELLOW_3B), T("agentic grader", 26, YELLOW_3B))
        grader[1].move_to(grader[0])
        grader.move_to(DOWN * 1.05 + LEFT * 4.2)
        self.play(FadeIn(grader), *[r[3].animate.set_opacity(0.25) for r in rows])
        lines = VGroup(*[Line(r[1].get_right(), grader.get_top(), stroke_width=1.5, color=YELLOW_3B, stroke_opacity=0.5) for r in rows])
        self.play(Create(lines), run_time=0.8)
        self.say("MiMo adds an agentic grader that reads the whole group side by side. Step one,\nGroupwise Reward Synthesis: contrast the attempts to write a task-specific rubric.")
        rub = VGroup(
            T("GRS: rubric for this task", 22, YELLOW_3B),
            T("• fixes the root cause", 20, GREY_A),
            T("• no redundant tool calls", 20, GREY_A),
            T("• verifies the fix", 20, GREY_A),
            T("example items", 16, DIM),
        ).arrange(DOWN, buff=0.08, aligned_edge=LEFT).next_to(grader, RIGHT, buff=0.5)
        self.play(FadeIn(rub, shift=LEFT * 0.2))
        self.settle()
        self.play(FadeOut(lines), run_time=0.4)

        # GAR: redistribute advantage among passers, conserving the total
        base_y = -2.35
        ax0 = 1.7
        xs = [ax0 + k * 0.9 for k in range(4)]
        base = Line([ax0 - 0.5, base_y, 0], [xs[-1] + 0.5, base_y, 0], color=GREY_B, stroke_width=2)
        before = [1.0, 1.0, 1.0, 1.0]
        after = [1.75, 0.95, 0.35, 0.95]
        def bars_for(vals, col):
            return VGroup(*[Rectangle(width=0.5, height=v * 0.55, stroke_width=0, fill_color=col, fill_opacity=0.9).move_to([x, base_y + v * 0.55 / 2, 0]) for x, v in zip(xs, vals)])
        b0 = bars_for(before, GREEN_3B)
        nms = VGroup(*[T(n, 20, GREY_B).next_to([x, base_y, 0], DOWN, buff=0.12) for x, (n, _, _) in zip(xs, specs)])
        gl = T("GAR: advantage among passers", 22, GREEN_3B).next_to(base, UP, buff=1.15)
        self.play(FadeOut(rub), FadeIn(gl), Create(base), FadeIn(nms), LaggedStart(*[GrowFromEdge(b, DOWN) for b in b0], lag_ratio=0.1))
        self.say("Step two, Groupwise Advantage Redistribution: among the attempts that passed,\nshift credit toward the shorter, better ones. Total credit is only redistributed.")
        self.play(Transform(b0, bars_for(after, GREEN_3B)), run_time=1.6)
        sum_t = T("Σ unchanged", 20, GREY_B).next_to(base, RIGHT, buff=0.2)
        self.play(FadeIn(sum_t))
        self.clear_keep_header()

        # dynamics, schematic
        self.say("What that buys during training, as the report describes it:")
        names = [("pass rate", lambda x: 0.35 + 0.25 * (1 - np.exp(-x / 2.5)), lambda x: 0.35 + 0.42 * (1 - np.exp(-x / 5))),
                 ("turns", lambda x: 1 + 0.18 * x, lambda x: 1 + 0.02 * x),
                 ("tokens", lambda x: 1 + 0.2 * x, lambda x: 1 + 0.07 * x)]
        panels = VGroup()
        for n, f_bad, f_good in names:
            ax = Axes(x_range=[0, 10, 5], y_range=[0, 3 if n != "pass rate" else 1, 1], x_length=3.4, y_length=2.4, tips=False,
                      axis_config={"color": GREY_D, "include_ticks": False})
            t = T(n, 24, WHITE).next_to(ax, UP, buff=0.15)
            cb = ax.plot(f_bad, color=RED_3B, x_range=[0, 10])
            cg = ax.plot(f_good, color=GREEN_3B, x_range=[0, 10])
            panels.add(VGroup(ax, t, cb, cg))
        panels.arrange(RIGHT, buff=0.8).shift(UP * 0.3)
        for p in panels:
            self.play(Create(p[0]), FadeIn(p[1]), run_time=0.4)
        leg = VGroup(
            VGroup(Line(ORIGIN, RIGHT * 0.5, color=RED_3B, stroke_width=4), T("pass / fail only", 22, GREY_B)).arrange(RIGHT, buff=0.15),
            VGroup(Line(ORIGIN, RIGHT * 0.5, color=GREEN_3B, stroke_width=4), T("groupwise grading", 22, GREY_B)).arrange(RIGHT, buff=0.15),
            T("schematic", 18, DIM),
        ).arrange(RIGHT, buff=0.6).next_to(panels, DOWN, buff=0.35)
        self.play(FadeIn(leg))
        self.play(*[Create(p[2]) for p in panels], *[Create(p[3]) for p in panels], run_time=2.5)
        self.say("With pass/fail rewards, turns and token counts balloon while pass rate plateaus.\nWith groupwise grading, pass rate keeps climbing, turns stay flat, length grows slowly.")
        self.clear_all()

    # 06 ----------------------------------------------------------------
    def stability(self):
        self.chapter(6, "Keeping a trillion-parameter run stable")
        n = 64
        rng = np.random.default_rng(11)
        before = rng.lognormal(0, 0.62, n)
        before[17] = 0
        before = before / before.mean()
        before[40] = 6.0
        before = before / before.mean()
        after = rng.lognormal(0, 1.1, n)
        cold = rng.choice([i for i in range(n) if i != 40], size=14, replace=False)
        after[cold] = 0
        after = after / after.mean()
        after[40] = 16.0
        after = after / after.mean()
        H = 0.19
        base_y = -1.9
        x_left = -6.0
        w = 0.12

        def bars(vals, col=BLUE_3B):
            return VGroup(*[
                Rectangle(width=w, height=max(v * H, 0.01), stroke_width=0,
                          fill_color=(GREY_D if v < 0.05 else col), fill_opacity=0.9).move_to([x_left + i * (w + 0.03), base_y + max(v * H, 0.01) / 2, 0])
                for i, v in enumerate(vals)
            ])

        b = bars(before)
        axis = Line([x_left - 0.2, base_y, 0], [x_left + n * (w + 0.03), base_y, 0], color=GREY_B, stroke_width=2)
        mean_l = DashedLine([x_left - 0.2, base_y + H, 0], [x_left + n * (w + 0.03), base_y + H, 0], color=GREY_B, dash_length=0.06, stroke_width=1.5)
        ml = T("mean load", 18, GREY_B).next_to(mean_l, RIGHT, buff=0.1)
        xl = T("experts", 20, GREY_B).next_to(axis, DOWN, buff=0.15)
        self.play(Create(axis), FadeIn(xl), Create(mean_l), FadeIn(ml), LaggedStart(*[GrowFromEdge(r, DOWN) for r in b], lag_ratio=0.01), run_time=1.6)
        stats = VGroup(
            T("load CV", 22, GREY_B), T("0.78", 26, WHITE, font=MONO),
            T("busiest expert", 22, GREY_B), T("6× mean", 26, WHITE, font=MONO),
            T("cold experts", 22, GREY_B), T("0.5%", 26, WHITE, font=MONO),
        )
        grid = VGroup(*[VGroup(stats[2 * k], stats[2 * k + 1]).arrange(DOWN, buff=0.06, aligned_edge=LEFT) for k in range(3)]).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        grid.move_to(RIGHT * 5.3 + UP * 0.3)
        self.play(FadeIn(grid))
        self.say("A Mixture-of-Experts model routes each token to a few experts.\nWith a trainable router, RL made the load drift badly within twenty steps.")
        new_vals = [T("2.0", 26, RED_3B, font=MONO), T("16× mean", 26, RED_3B, font=MONO), T("22%", 26, RED_3B, font=MONO)]
        self.play(Transform(b, bars(after, RED_3B)),
                  *[Transform(stats[2 * k + 1], new_vals[k].move_to(stats[2 * k + 1], aligned_edge=LEFT)) for k in range(3)],
                  run_time=2.5)
        self.say("Load imbalance nearly tripled, one expert took sixteen times its share,\nand more than a fifth of the experts went cold.")

        # padlock
        body = RoundedRectangle(width=0.9, height=0.7, corner_radius=0.1, fill_color=YELLOW_3B, fill_opacity=0.9, stroke_width=0)
        shackle = Arc(radius=0.3, start_angle=0, angle=PI, stroke_width=8, color=YELLOW_3B).next_to(body, UP, buff=-0.02)
        lock = VGroup(shackle, body).move_to(UP * 1.4 + LEFT * 1.0)
        lt = T("freeze the router", 28, YELLOW_3B).next_to(lock, RIGHT, buff=0.3)
        self.play(FadeIn(lock, scale=1.4), FadeIn(lt))
        orig = [T("0.78", 26, WHITE, font=MONO), T("6× mean", 26, WHITE, font=MONO), T("0.5%", 26, WHITE, font=MONO)]
        self.play(Transform(b, bars(before)),
                  *[Transform(stats[2 * k + 1], orig[k].move_to(stats[2 * k + 1], aligned_edge=LEFT)) for k in range(3)], run_time=1.8)
        self.say("Their fix is blunt: freeze the router. Routing is a training-dynamics problem,\nand the router is not where RL is doing its useful work.")
        self.clear_keep_header()

        # reward-hacking defense rings
        layers = [("reward design", BLUE_3B), ("adversarial evaluation", GREEN_3B), ("anomaly detection", YELLOW_3B), ("cross-verified validators", PURPLE_3B)]
        center = LEFT * 1.6 + DOWN * 0.25
        rings = VGroup()
        labs = VGroup()
        for k, (n, c) in enumerate(layers):
            rad = 2.2 - k * 0.45
            ring = Circle(radius=rad, color=c, stroke_width=5).move_to(center)
            rings.add(ring)
            lab = T(n, 26, c)
            labs.add(lab)
        core = VGroup(Circle(radius=0.55, color=WHITE, fill_opacity=0.08), T("reward", 24, WHITE)).move_to(center)
        labs.arrange(DOWN, buff=0.35, aligned_edge=LEFT).move_to(RIGHT * 3.8 + DOWN * 0.1)
        self.say("The other failure mode at scale is reward hacking: the policy finds a way to score\nwithout solving the task. MiMo stacks several independent defenses.")
        self.play(FadeIn(core))
        for ring, lab in zip(rings, labs):
            self.play(Create(ring), FadeIn(lab, shift=LEFT * 0.2), run_time=0.6)
        hack = Arrow(center + LEFT * 4.4 + UP * 1.7, center + LEFT * 1.6 + UP * 0.75, color=RED_3B, buff=0, stroke_width=5)
        ht = T("exploit", 22, RED_3B).next_to(hack.get_start(), UP, buff=0.1)
        self.play(GrowArrow(hack), FadeIn(ht))
        x = T("✕", 40, RED_3B, font=SYM).move_to(hack.get_end())
        self.play(FadeIn(x, scale=1.5), rings[0].animate.set_stroke(width=9), run_time=0.5)
        self.play(rings[0].animate.set_stroke(width=5), run_time=0.3)
        self.say("A hack has to beat every layer at once, and the validators check each other.")
        self.clear_all()

    # 07 ----------------------------------------------------------------
    def results(self):
        self.chapter(7, "Did scaling pay off?")
        ax = Axes(x_range=[0, 2.8, 0.5], y_range=[45, 76, 5], x_length=8.0, y_length=3.9, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": True, "tick_size": 0.05}).move_to(LEFT * 1.6 + UP * 0.2)
        xn = VGroup(*[T(f"${v:g}M", 20, GREY_B).next_to(ax.c2p(v, 45), DOWN, buff=0.15) for v in [0, 0.5, 1, 1.5, 2, 2.5]])
        yn = VGroup(*[T(f"{v}", 20, GREY_B).next_to(ax.c2p(0, v), LEFT, buff=0.15) for v in [45, 50, 55, 60, 65, 70, 75]])
        xl = T("cumulative RL cost", 22, GREY_B).next_to(xn, DOWN, buff=0.15)
        yl = T("DeepSWE avg@3", 22, GREY_B).rotate(PI / 2).next_to(yn, LEFT, buff=0.15)
        self.play(Create(ax), FadeIn(xn), FadeIn(yn), FadeIn(xl), FadeIn(yl))

        def curve(y0, y1, xend, k):
            b = (y1 - y0) / np.log(1 + k * xend)
            return lambda x: y0 + b * np.log(1 + k * x)

        f_pro = curve(58.4, 72.6, 2.6, 4.0)
        f_fl = curve(48.7, 65.7, 0.9, 10.0)
        cp = ax.plot(f_pro, x_range=[0, 2.6], color=BLUE_3B, stroke_width=5)
        cf = ax.plot(f_fl, x_range=[0, 0.9], color=TEAL_3B, stroke_width=5)
        self.say("Here is the headline plot: a hard agentic coding benchmark versus money spent on RL.")
        self.play(Create(cp), Create(cf), run_time=3.0)
        dots = VGroup(
            Dot(ax.c2p(0, 58.4), color=BLUE_3B), Dot(ax.c2p(2.6, 72.6), color=BLUE_3B),
            Dot(ax.c2p(0, 48.7), color=TEAL_3B), Dot(ax.c2p(0.9, 65.7), color=TEAL_3B),
        )
        labs = VGroup(
            T("Pro  58.4 → 72.6", 24, BLUE_3B).next_to(dots[1], UP, buff=0.15).shift(LEFT * 0.6),
            T("Flash  48.7 → 65.7", 24, TEAL_3B).next_to(dots[3], RIGHT, buff=0.15).shift(DOWN * 0.1),
        )
        self.play(FadeIn(dots), FadeIn(labs))
        note = T("endpoints from the report; curve shape schematic", 18, DIM).next_to(ax, UP, buff=0.15).align_to(ax, RIGHT)
        self.play(FadeIn(note))
        self.say("Pro climbs from 58.4 to 72.6, Flash from 48.7 to 65.7,\nand both are still rising at the end of the run.")

        cards = VGroup()
        for name, tot, act, col in [("MiMo-V2.6-Pro", "1.02T params", "42B active", BLUE_3B), ("MiMo-V2.6-Flash", "309B params", "15B active", TEAL_3B)]:
            box = RoundedRectangle(width=3.3, height=1.35, corner_radius=0.15, color=col)
            txt = VGroup(T(name, 24, col), T(tot, 22, WHITE), T(act, 22, GREY_B)).arrange(DOWN, buff=0.08).move_to(box)
            cards.add(VGroup(box, txt))
        aa = VGroup(RoundedRectangle(width=3.3, height=1.35, corner_radius=0.15, color=YELLOW_3B),
                    VGroup(T("46", 40, YELLOW_3B), T("Artificial Analysis index", 17, GREY_B), T("top open-weights at launch", 17, GREY_B)).arrange(DOWN, buff=0.05))
        aa[1].move_to(aa[0])
        cards.add(aa)
        cards.arrange(DOWN, buff=0.25).move_to(RIGHT * 5.1 + DOWN * 0.1)
        self.play(LaggedStart(*[FadeIn(c, shift=LEFT * 0.2) for c in cards], lag_ratio=0.25))
        self.say("Both models are sparse MoEs released with open weights under MIT,\nand at launch Pro was the top open-weights model on Artificial Analysis.")
        self.clear_all()

    # 08 ----------------------------------------------------------------
    def recap(self):
        dials = VGroup(
            self.dial("RL compute", BLUE_3B),
            self.dial("environment diversity", GREEN_3B),
            self.dial("grader compute", YELLOW_3B),
        ).arrange(RIGHT, buff=2.0).shift(UP * 1.3)
        for d in dials:
            d.needle.rotate(-PI * 0.85, about_point=d.hub.get_center())
        notes = [
            ["fully async, 1,568 × 16", "fresh-token gate, bounded IS", "sampler keeps the frontier"],
            ["one run, 50 datasets", "many mini-harnesses", "transfers to unseen harnesses"],
            ["grader reads the group", "rubrics + redistribution", "shorter, better solutions"],
        ]
        cols = VGroup()
        for d, ns in zip(dials, notes):
            c = VGroup(*[T(s, 20, GREY_A) for s in ns]).arrange(DOWN, buff=0.14)
            c.next_to(d, DOWN, buff=0.35)
            cols.add(c)
        self.play(LaggedStart(*[FadeIn(d) for d in dials], lag_ratio=0.2))
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.1) for c in cols], lag_ratio=0.25), run_time=1.5)
        self.say("Three dials, turned together. Scale compute, but keep the batch full of signal.\nWiden environments so skills transfer. Spend on grading so reward means what you want.")
        guard = T("…and keep it stable: frozen router, layered defenses against reward hacking.", 24, GREY_B).move_to(DOWN * 1.9)
        self.play(FadeIn(guard))
        self.say("Scaled that way, RL kept improving the model for as long as they kept paying for it.")
        self.clear_all()
        end = VGroup(T("MiMo-V2.6", 56), T("Scaling Reinforcement Learning Towards Self-Improvement", 26, GREY_B),
                     T("mimo.xiaomi.com/rl", 24, BLUE_3B, font=MONO)).arrange(DOWN, buff=0.3)
        self.play(FadeIn(end))
        self.wait(2.5)
        self.play(FadeOut(end))
