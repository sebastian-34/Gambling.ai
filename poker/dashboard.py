from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any


class ScrollableFrame(tk.Frame):
    def __init__(self, master: tk.Misc, bg: str) -> None:
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(self.window_id, width=event.width),
        )


class PokerResultsDashboard:
    BG = "#F6F3ED"
    PANEL = "#FFFFFF"
    PANEL_ALT = "#FFF8EF"
    HEADER = "#12343B"
    HEADER_2 = "#1F4E5F"
    TEXT = "#1F2933"
    MUTED = "#6B7280"
    GOLD = "#D4A373"
    EMERALD = "#2A9D8F"
    CORAL = "#E76F51"
    INDIGO = "#355070"
    AMBER = "#E9C46A"
    PLAYER_COLORS = ["#2A9D8F", "#E76F51", "#355070", "#D4A373", "#8A5CF6"]

    def __init__(self, report: dict[str, Any], title: str = "Poker Results") -> None:
        self.report = report
        self.leaderboard: list[dict[str, Any]] = report.get("leaderboard", [])
        self.hand_history: list[dict[str, Any]] = report.get("hand_history", [])
        self.table_talk: dict[str, int] = report.get("table_talk", {})
        self.chip_history: list[dict[str, int]] = report.get("chip_history", [])
        self.pot_history: list[dict[str, Any]] = report.get("pot_history", [])
        self.summary: dict[str, Any] = report.get("summary", {})
        self.replay_text: str = report.get("replay_text", "")

        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("1600x1020")
        self.root.configure(bg=self.BG)

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self._configure_styles()
        self._build_shell()

    def show(self) -> None:
        self.root.mainloop()

    def _configure_styles(self) -> None:
        self.style.configure("Dashboard.TNotebook", background=self.BG, borderwidth=0)
        self.style.configure("Dashboard.TNotebook.Tab", padding=(18, 10), font=("Segoe UI", 10, "bold"))
        self.style.map(
            "Dashboard.TNotebook.Tab",
            background=[("selected", self.PANEL), ("active", self.PANEL_ALT)],
            foreground=[("selected", self.TEXT), ("active", self.TEXT)],
        )
        self.style.configure("Treeview", font=("Segoe UI", 10), rowheight=28, background=self.PANEL, fieldbackground=self.PANEL)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=(8, 10))
        self.style.map("Treeview", background=[("selected", self.AMBER)])
        self.style.configure("Horizontal.TProgressbar", troughcolor="#E9ECEF", background=self.EMERALD, thickness=12)

    def _build_shell(self) -> None:
        header = tk.Frame(self.root, bg=self.HEADER, height=140)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=self.HEADER)
        left.pack(side="left", fill="both", expand=True, padx=28, pady=22)
        tk.Label(
            left,
            text="Gambling.ai Results Dashboard",
            bg=self.HEADER,
            fg="white",
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Leaderboard, replay highlights, table-talk impact, and tournament learning in one view.",
            bg=self.HEADER,
            fg="#D9E6EA",
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(8, 0))

        right = tk.Frame(header, bg=self.HEADER)
        right.pack(side="right", padx=28, pady=18)
        top_name = self.leaderboard[0]["name"] if self.leaderboard else "No winner"
        self._mini_card(right, "Champion", top_name, self.GOLD)
        self._mini_card(right, "Hands", str(self.summary.get("hands_played", len(self.hand_history))), self.EMERALD)
        self._mini_card(right, "Biggest Pot", str(self.summary.get("biggest_pot", 0)), self.CORAL)

        tabs = ttk.Notebook(self.root, style="Dashboard.TNotebook")
        tabs.pack(fill="both", expand=True, padx=18, pady=18)

        self.overview_tab = tk.Frame(tabs, bg=self.BG)
        self.leaderboard_tab = tk.Frame(tabs, bg=self.BG)
        self.cards_tab = tk.Frame(tabs, bg=self.BG)
        self.replay_tab = tk.Frame(tabs, bg=self.BG)
        self.talk_tab = tk.Frame(tabs, bg=self.BG)
        self.charts_tab = tk.Frame(tabs, bg=self.BG)
        self.summary_tab = tk.Frame(tabs, bg=self.BG)

        tabs.add(self.overview_tab, text="Overview")
        tabs.add(self.leaderboard_tab, text="Leaderboard")
        tabs.add(self.cards_tab, text="Player Cards")
        tabs.add(self.replay_tab, text="Replay")
        tabs.add(self.talk_tab, text="Table Talk")
        tabs.add(self.charts_tab, text="Charts")
        tabs.add(self.summary_tab, text="Summary")

        self._build_overview_tab()
        self._build_leaderboard_tab()
        self._build_player_cards_tab()
        self._build_replay_tab()
        self._build_talk_tab()
        self._build_charts_tab()
        self._build_summary_tab()

    def _mini_card(self, parent: tk.Misc, title: str, value: str, color: str) -> None:
        card = tk.Frame(parent, bg=self.PANEL, bd=0, highlightthickness=0)
        card.pack(side="left", padx=8)
        tk.Frame(card, bg=color, width=8, height=58).pack(side="left", fill="y")
        content = tk.Frame(card, bg=self.PANEL)
        content.pack(side="left", padx=14, pady=8)
        tk.Label(content, text=title, bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(content, text=value, bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 16, "bold")).pack(anchor="w")

    def _panel(self, parent: tk.Misc, title: str, subtitle: str | None = None) -> tk.Frame:
        frame = tk.Frame(parent, bg=self.PANEL, bd=0, highlightthickness=1, highlightbackground="#E5E7EB")
        frame.pack(fill="x", padx=12, pady=12)
        header = tk.Frame(frame, bg=self.PANEL)
        header.pack(fill="x", padx=18, pady=(16, 0))
        tk.Label(header, text=title, bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(header, text=subtitle, bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))
        return frame

    def _build_overview_tab(self) -> None:
        frame = self._panel(
            self.overview_tab,
            "Tournament Snapshot",
            "The top line, the main ranking, and the strongest single-player story from the tournament.",
        )
        stats = tk.Frame(frame, bg=self.PANEL)
        stats.pack(fill="x", padx=18, pady=16)
        metrics = [
            ("Hands Played", str(self.summary.get("hands_played", len(self.hand_history))), self.EMERALD),
            ("Largest Pot", str(self.summary.get("biggest_pot", 0)), self.CORAL),
            ("Chat Reactions", str(sum(self.table_talk.values())), self.GOLD),
            ("Top Stack", str(self.leaderboard[0]["final_chips"] if self.leaderboard else 0), self.INDIGO),
        ]
        for title, value, color in metrics:
            self._mini_metric(stats, title, value, color)

        lower = tk.Frame(frame, bg=self.PANEL)
        lower.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        left = tk.Frame(lower, bg=self.PANEL)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = tk.Frame(lower, bg=self.PANEL)
        right.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self._leaderboard_tree(left)
        self._leader_card(right)

    def _mini_metric(self, parent: tk.Misc, label: str, value: str, color: str) -> None:
        card = tk.Frame(parent, bg=self.PANEL_ALT, bd=0, highlightthickness=0)
        card.pack(side="left", fill="x", expand=True, padx=8, pady=6)
        tk.Frame(card, bg=color, height=6).pack(fill="x")
        tk.Label(card, text=label, bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(12, 0))
        tk.Label(card, text=value, bg=self.PANEL_ALT, fg=self.TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=14, pady=(4, 14))

    def _leaderboard_tree(self, parent: tk.Misc) -> None:
        box = self._panel(parent, "Final Leaderboard", "Ranked by ending chip count.")
        table = ttk.Treeview(
            box,
            columns=("rank", "player", "chips", "won", "net", "net_per_hand"),
            show="headings",
            height=8,
        )
        headings = [
            ("rank", "Rank", 70),
            ("player", "Player", 180),
            ("chips", "Chips", 120),
            ("won", "Hands Won", 100),
            ("net", "Net Profit", 110),
            ("net_per_hand", "Net / Hand", 110),
        ]
        for key, text, width in headings:
            table.heading(key, text=text)
            table.column(key, width=width, anchor="center")
        for index, row in enumerate(self.leaderboard, start=1):
            table.insert(
                "",
                "end",
                values=(
                    index,
                    row["name"],
                    row["final_chips"],
                    row["hands_won"],
                    self._signed(row["net_profit"]),
                    self._signed(row["net_profit_per_hand"]),
                ),
                tags=("odd" if index % 2 else "even",),
            )
        table.tag_configure("odd", background="#F8FAFC")
        table.tag_configure("even", background="#FFFFFF")
        table.pack(fill="both", expand=True, padx=18, pady=(12, 18))

    def _leader_card(self, parent: tk.Misc) -> None:
        box = self._panel(parent, "Top Line Story", "The player summary worth reading first.")
        if not self.leaderboard:
            tk.Label(box, text="No data available.", bg=self.PANEL, fg=self.MUTED).pack(padx=18, pady=18)
            return

        leader = self.leaderboard[0]
        lead = tk.Frame(box, bg=self.PANEL_ALT, highlightthickness=1, highlightbackground="#E5E7EB")
        lead.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(lead, text=leader["name"], bg=self.PANEL_ALT, fg=self.TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(lead, text=f"Final chips: {leader['final_chips']}", bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=18)
        tk.Label(
            lead,
            text=f"Aggression {self._pct(leader['aggression_rate'])} | Bluff success {self._pct(leader['bluff_success_rate'])} | Pressure success {self._pct(leader['pressure_success_rate'])}",
            bg=self.PANEL_ALT,
            fg=self.TEXT,
            font=("Segoe UI", 11, "bold"),
            wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(10, 4))

        summary_lines = [
            f"Hands won: {leader['hands_won']}",
            f"Net per hand: {self._signed(leader['net_profit_per_hand'])}",
            f"Volatility: {leader['volatility']:.2f}",
        ]
        for line in summary_lines:
            tk.Label(lead, text=line, bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=18, pady=2)

    def _build_leaderboard_tab(self) -> None:
        frame = self._panel(self.leaderboard_tab, "Leaderboard Table", "All seats ranked by chips, with the key profitability metrics beside them.")
        self._leaderboard_tree(frame)

    def _build_player_cards_tab(self) -> None:
        frame = ScrollableFrame(self.cards_tab, self.BG)
        frame.pack(fill="both", expand=True)

        if not self.leaderboard:
            tk.Label(frame.inner, text="No player data available.", bg=self.BG, fg=self.MUTED).pack(pady=18)
            return

        for index, row in enumerate(self.leaderboard):
            card = tk.Frame(frame.inner, bg=self.PANEL, highlightthickness=1, highlightbackground="#E5E7EB")
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=12, pady=12)
            frame.inner.grid_columnconfigure(index % 2, weight=1)
            self._player_card(card, row, self.PLAYER_COLORS[index % len(self.PLAYER_COLORS)])

    def _player_card(self, parent: tk.Misc, row: dict[str, Any], accent: str) -> None:
        tk.Frame(parent, bg=accent, height=8).pack(fill="x")
        body = tk.Frame(parent, bg=self.PANEL)
        body.pack(fill="both", expand=True, padx=18, pady=16)
        tk.Label(body, text=row["name"], bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(body, text=f"Final chips {row['final_chips']} | Net {self._signed(row['net_profit'])}", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 12))

        metrics = [
            ("Aggression", row["aggression_rate"], accent),
            ("Fold rate", row["fold_rate"], self.CORAL),
            ("Raise frequency", min(1.0, row["raise_frequency"] / max(1, row["hands_played"] * 2)), self.GOLD),
            ("Showdown win", row["showdown_win_rate"], self.EMERALD),
            ("Bluff success", row["bluff_success_rate"], self.INDIGO),
        ]
        for label, value, color in metrics:
            self._metric_bar(body, label, value, color)

        extra = tk.Frame(body, bg=self.PANEL)
        extra.pack(fill="x", pady=(10, 0))
        extra.grid_columnconfigure(0, weight=1)
        extra.grid_columnconfigure(1, weight=1)
        self._tiny_stat(extra, 0, "Recovery", f"{row['recovery_score']:+.2f}")
        self._tiny_stat(extra, 1, "Volatility", f"{row['volatility']:.2f}")

    def _metric_bar(self, parent: tk.Misc, label: str, value: float, color: str) -> None:
        row = tk.Frame(parent, bg=self.PANEL)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9, "bold"), width=16, anchor="w").pack(side="left")
        bar = ttk.Progressbar(row, maximum=100, value=max(0.0, min(100.0, value * 100.0)), style="Horizontal.TProgressbar")
        bar.pack(side="left", fill="x", expand=True, padx=(6, 8))
        tk.Label(row, text=self._pct(value), bg=self.PANEL, fg=color, font=("Segoe UI", 9, "bold"), width=7, anchor="e").pack(side="right")

    def _tiny_stat(self, parent: tk.Misc, column: int, label: str, value: str) -> None:
        cell = tk.Frame(parent, bg=self.PANEL_ALT, highlightthickness=1, highlightbackground="#E5E7EB")
        cell.grid(row=0, column=column, sticky="ew", padx=4)
        tk.Label(cell, text=label, bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 0))
        tk.Label(cell, text=value, bg=self.PANEL_ALT, fg=self.TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=12, pady=(2, 10))

    def _build_replay_tab(self) -> None:
        scroll = ScrollableFrame(self.replay_tab, self.BG)
        scroll.pack(fill="both", expand=True)

        if not self.hand_history:
            tk.Label(scroll.inner, text="No replay data available.", bg=self.BG, fg=self.MUTED).pack(pady=18)
            return

        for index, hand in enumerate(self.hand_history):
            card = tk.Frame(scroll.inner, bg=self.PANEL, highlightthickness=1, highlightbackground="#E5E7EB")
            card.pack(fill="x", padx=14, pady=10)
            accent = self.PLAYER_COLORS[index % len(self.PLAYER_COLORS)]
            tk.Frame(card, bg=accent, height=8).pack(fill="x")
            body = tk.Frame(card, bg=self.PANEL)
            body.pack(fill="x", padx=18, pady=16)

            board = ", ".join(hand.get("board", [])) or "--"
            winners = ", ".join(hand.get("winner_names", [])) or "Unknown"
            header = f"Hand {hand.get('hand_number', index + 1)} | Pot {hand.get('pot', 0)} | Board {board} | Winner {winners}"
            tk.Label(body, text=header, bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 12, "bold"), wraplength=1460, justify="left").pack(anchor="w")

            hole_cards = hand.get("hole_cards", {})
            if isinstance(hole_cards, dict) and hole_cards:
                reveal = " | ".join(f"{name}: {' '.join(cards)}" for name, cards in hole_cards.items())
                tk.Label(
                    body,
                    text=f"Hands: {reveal}",
                    bg=self.PANEL,
                    fg=self.MUTED,
                    font=("Segoe UI", 9),
                    wraplength=1460,
                    justify="left",
                ).pack(anchor="w", pady=(4, 0))

            highlight_box = tk.Frame(body, bg=self.PANEL)
            highlight_box.pack(fill="x", pady=(8, 0))
            highlights = hand.get("highlights", [])
            if not highlights:
                tk.Label(highlight_box, text="No high-impact moments recorded.", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10)).pack(anchor="w")
            else:
                for moment in highlights[:6]:
                    self._highlight_label(highlight_box, moment)
                if len(highlights) > 6:
                    tk.Label(highlight_box, text=f"+{len(highlights) - 6} more key moments", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(4, 0))

    def _highlight_label(self, parent: tk.Misc, moment: dict[str, Any]) -> None:
        kind = moment.get("kind", "")
        palette = {
            "big_raise": self.CORAL,
            "pressure_fold": self.GOLD,
            "showdown_winner": self.EMERALD,
            "chat": self.INDIGO,
        }
        color = palette.get(kind, self.INDIGO)
        frame = tk.Frame(parent, bg=color)
        frame.pack(fill="x", pady=4)
        tk.Label(frame, text=moment.get("text", ""), bg=color, fg="white", font=("Segoe UI", 10, "bold"), anchor="w", wraplength=1400, justify="left").pack(fill="x", padx=10, pady=6)

    def _build_talk_tab(self) -> None:
        frame = self._panel(
            self.talk_tab,
            "Table Talk Impact",
            "How often the next visible action after chat was a fold, call, or raise.",
        )
        inner = tk.Frame(frame, bg=self.PANEL)
        inner.pack(fill="both", expand=True, padx=18, pady=16)

        total = sum(self.table_talk.values()) or 1
        for column, key, color in zip((0, 1, 2), ("fold", "call", "raise"), (self.CORAL, self.EMERALD, self.GOLD)):
            value = self.table_talk.get(key, 0)
            card = tk.Frame(inner, bg=self.PANEL_ALT, highlightthickness=1, highlightbackground="#E5E7EB")
            card.grid(row=0, column=column, sticky="nsew", padx=8)
            inner.grid_columnconfigure(column, weight=1)
            tk.Frame(card, bg=color, height=8).pack(fill="x")
            tk.Label(card, text=key.title(), bg=self.PANEL_ALT, fg=self.TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=14, pady=(12, 0))
            tk.Label(card, text=str(value), bg=self.PANEL_ALT, fg=color, font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=14, pady=(4, 0))
            tk.Label(card, text=self._pct(value / total), bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=14, pady=(0, 12))

        chart = tk.Canvas(frame, bg=self.PANEL_ALT, height=220, highlightthickness=1, highlightbackground="#E5E7EB")
        chart.pack(fill="x", padx=18, pady=(0, 18))
        self._draw_bar_chart(chart, ["fold", "call", "raise"], [self.table_talk.get("fold", 0), self.table_talk.get("call", 0), self.table_talk.get("raise", 0)], [self.CORAL, self.EMERALD, self.GOLD], title="Responses triggered after table talk")

    def _build_charts_tab(self) -> None:
        if not self.leaderboard:
            tk.Label(self.charts_tab, text="No chart data available.", bg=self.BG, fg=self.MUTED).pack(pady=18)
            return

        chip_series = self._chip_series()
        labels = [str(hand.get("hand", index + 1)) for index, hand in enumerate(self.pot_history)]

        top = tk.Canvas(self.charts_tab, bg=self.PANEL, height=360, highlightthickness=1, highlightbackground="#E5E7EB")
        top.pack(fill="both", expand=True, padx=14, pady=(14, 10))
        top.bind("<Configure>", lambda _event: self._draw_line_chart(top, title="Chip stack over time", series=chip_series, labels=labels))

        bottom = tk.Frame(self.charts_tab, bg=self.BG)
        bottom.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        left = tk.Canvas(bottom, bg=self.PANEL, height=320, highlightthickness=1, highlightbackground="#E5E7EB")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        left.bind(
            "<Configure>",
            lambda _event: self._draw_bar_chart(
                left,
                labels,
                [hand.get("pot", 0) for hand in self.pot_history],
                [self.INDIGO] * max(1, len(self.pot_history)),
                title="Pot size by hand",
            ),
        )

        right = tk.Canvas(bottom, bg=self.PANEL, height=320, highlightthickness=1, highlightbackground="#E5E7EB")
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))
        volatility_rows = [(row["name"], row["volatility"]) for row in self.leaderboard]
        right.bind("<Configure>", lambda _event: self._draw_horizontal_bars(right, volatility_rows, title="Volatility by player"))

        self.root.after(
            50,
            lambda: (
                self._draw_line_chart(top, title="Chip stack over time", series=chip_series, labels=labels),
                self._draw_bar_chart(
                    left,
                    labels,
                    [hand.get("pot", 0) for hand in self.pot_history],
                    [self.INDIGO] * max(1, len(self.pot_history)),
                    title="Pot size by hand",
                ),
                self._draw_horizontal_bars(right, volatility_rows, title="Volatility by player"),
            ),
        )

    def _build_summary_tab(self) -> None:
        frame = self._panel(
            self.summary_tab,
            "Match Summary",
            "Direct answers to the strategic questions the tournament can answer.",
        )
        inner = tk.Frame(frame, bg=self.PANEL)
        inner.pack(fill="both", expand=True, padx=18, pady=18)

        if not self.leaderboard:
            tk.Label(inner, text="No summary data available.", bg=self.PANEL, fg=self.MUTED).pack(pady=18)
            return

        preflop = self.summary.get("preflop_dominator") or self.leaderboard[0]
        recovery = self.summary.get("recovery_leader") or self.leaderboard[0]
        pressure = self.summary.get("pressure_leader") or self.leaderboard[0]

        cards = [
            ("Who dominated preflop?", preflop["name"], f"{preflop['preflop_wins']} preflop wins and {preflop['preflop_raises']} preflop raises."),
            ("Who recovered best from losses?", recovery["name"], f"Average rebound after a loss: {recovery['recovery_score']:+.2f} chips."),
            ("Who performed best under pressure?", pressure["name"], f"Pressure success rate: {self._pct(pressure['pressure_success_rate'])}."),
        ]
        for row, (question, answer, explanation) in enumerate(cards):
            card = tk.Frame(inner, bg=self.PANEL_ALT, highlightthickness=1, highlightbackground="#E5E7EB")
            card.grid(row=row, column=0, sticky="ew", pady=8)
            inner.grid_columnconfigure(0, weight=1)
            tk.Label(card, text=question, bg=self.PANEL_ALT, fg=self.MUTED, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
            tk.Label(card, text=answer, bg=self.PANEL_ALT, fg=self.TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=16, pady=(4, 0))
            tk.Label(card, text=explanation, bg=self.PANEL_ALT, fg=self.TEXT, font=("Segoe UI", 10), wraplength=1450, justify="left").pack(anchor="w", padx=16, pady=(4, 12))

        note = tk.Frame(inner, bg=self.PANEL, highlightthickness=1, highlightbackground="#E5E7EB")
        note.grid(row=3, column=0, sticky="ew", pady=(18, 0))
        text = (
            "Takeaway: the model is most interesting when you compare chip results to behavior. "
            "Aggression, bluff success, table-talk response, and recovery are more informative than the final stack alone."
        )
        tk.Label(note, text=text, bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 11), wraplength=1450, justify="left").pack(anchor="w", padx=16, pady=16)

    def _chip_series(self) -> dict[str, list[float]]:
        if not self.chip_history:
            return {}
        names = list(self.chip_history[0].keys())
        series = {name: [] for name in names}
        for snapshot in self.chip_history:
            for name in names:
                series[name].append(snapshot.get(name, 0))
        return series

    def _draw_line_chart(self, canvas: tk.Canvas, title: str, series: dict[str, list[float]], labels: list[str]) -> None:
        canvas.delete("all")
        width = max(int(canvas.cget("width") or 0), canvas.winfo_width(), canvas.winfo_reqwidth(), 400)
        height = max(int(canvas.cget("height") or 0), canvas.winfo_height(), canvas.winfo_reqheight(), 260)
        pad_left, pad_right, pad_top, pad_bottom = 72, 28, 42, 48
        canvas.create_text(20, 18, text=title, anchor="w", fill=self.TEXT, font=("Segoe UI", 13, "bold"))

        if not series:
            canvas.create_text(width / 2, height / 2, text="No chart data.", fill=self.MUTED, font=("Segoe UI", 11))
            return

        values = [value for points in series.values() for value in points]
        if not values:
            return
        min_value = min(values)
        max_value = max(values)
        if min_value == max_value:
            min_value -= 10
            max_value += 10
        plot_width = max(1, width - pad_left - pad_right)
        plot_height = max(1, height - pad_top - pad_bottom)
        step = plot_width / max(1, len(labels) - 1)

        canvas.create_line(pad_left, pad_top, pad_left, height - pad_bottom, fill="#CBD5E1", width=2)
        canvas.create_line(pad_left, height - pad_bottom, width - pad_right, height - pad_bottom, fill="#CBD5E1", width=2)

        for index in range(5):
            y = pad_top + plot_height * index / 4
            value = max_value - (max_value - min_value) * index / 4
            canvas.create_line(pad_left, y, width - pad_right, y, fill="#EEF2F7")
            canvas.create_text(12, y, text=f"{int(value)}", anchor="w", fill=self.MUTED, font=("Segoe UI", 9))

        tick_count = min(12, len(labels))
        tick_step = max(1, len(labels) // max(1, tick_count))
        for index in range(0, len(labels), tick_step):
            x = pad_left + index * step
            canvas.create_text(x, height - pad_bottom + 18, text=labels[index], fill=self.MUTED, font=("Segoe UI", 9))

        legend_x = width - 260
        legend_y = 16
        for index, (name, points) in enumerate(series.items()):
            color = self.PLAYER_COLORS[index % len(self.PLAYER_COLORS)]
            coords = []
            for point_index, point in enumerate(points):
                x = pad_left + point_index * step
                y = pad_top + (max_value - point) / (max_value - min_value) * plot_height
                coords.extend([x, y])
                canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline=color)
            if len(coords) >= 4:
                canvas.create_line(*coords, fill=color, width=3, smooth=True)
            canvas.create_rectangle(legend_x, legend_y + index * 22, legend_x + 12, legend_y + 12 + index * 22, fill=color, outline=color)
            canvas.create_text(legend_x + 18, legend_y + 6 + index * 22, text=name, anchor="w", fill=self.TEXT, font=("Segoe UI", 9))

    def _draw_bar_chart(
        self,
        canvas: tk.Canvas,
        labels: list[str],
        values: list[float],
        colors: list[str],
        title: str,
    ) -> None:
        canvas.delete("all")
        width = max(int(canvas.cget("width") or 0), canvas.winfo_width(), canvas.winfo_reqwidth(), 360)
        height = max(int(canvas.cget("height") or 0), canvas.winfo_height(), canvas.winfo_reqheight(), 240)
        canvas.create_text(20, 18, text=title, anchor="w", fill=self.TEXT, font=("Segoe UI", 13, "bold"))
        if not values:
            canvas.create_text(width / 2, height / 2, text="No chart data.", fill=self.MUTED, font=("Segoe UI", 11))
            return

        pad_left, pad_right, pad_top, pad_bottom = 40, 24, 42, 52
        plot_width = max(1, width - pad_left - pad_right)
        plot_height = max(1, height - pad_top - pad_bottom)
        max_value = max(values) if max(values) > 0 else 1
        bar_width = max(8, plot_width / max(1, len(values) * 1.6))
        gap = (plot_width - bar_width * len(values)) / max(1, len(values) + 1)

        canvas.create_line(pad_left, pad_top, pad_left, height - pad_bottom, fill="#CBD5E1", width=2)
        canvas.create_line(pad_left, height - pad_bottom, width - pad_right, height - pad_bottom, fill="#CBD5E1", width=2)

        show_every = max(1, len(labels) // 14)
        for index, (label, value) in enumerate(zip(labels, values)):
            x1 = pad_left + gap + index * (bar_width + gap)
            x2 = x1 + bar_width
            bar_height = (value / max_value) * plot_height
            y1 = height - pad_bottom - bar_height
            color = colors[index % len(colors)]
            canvas.create_rectangle(x1, y1, x2, height - pad_bottom, fill=color, outline=color)
            if index % show_every == 0:
                canvas.create_text((x1 + x2) / 2, y1 - 10, text=str(int(value)), fill=self.TEXT, font=("Segoe UI", 9, "bold"))
                canvas.create_text((x1 + x2) / 2, height - pad_bottom + 20, text=label[:10], fill=self.MUTED, font=("Segoe UI", 8), angle=30)

    def _draw_horizontal_bars(self, canvas: tk.Canvas, rows: list[tuple[str, float]], title: str) -> None:
        canvas.delete("all")
        width = int(canvas.cget("width") or canvas.winfo_reqwidth())
        height = int(canvas.cget("height") or canvas.winfo_reqheight())
        canvas.create_text(20, 18, text=title, anchor="w", fill=self.TEXT, font=("Segoe UI", 13, "bold"))
        if not rows:
            canvas.create_text(width / 2, height / 2, text="No chart data.", fill=self.MUTED, font=("Segoe UI", 11))
            return

        pad_left, pad_right, pad_top, pad_bottom = 120, 30, 42, 30
        plot_width = max(1, width - pad_left - pad_right)
        plot_height = max(1, height - pad_top - pad_bottom)
        max_value = max(value for _, value in rows) if rows else 1
        row_height = plot_height / max(1, len(rows))

        for index, (name, value) in enumerate(rows):
            y_top = pad_top + index * row_height + 6
            y_bottom = y_top + row_height * 0.65
            bar_width = (value / max_value) * plot_width if max_value else 0
            color = self.PLAYER_COLORS[index % len(self.PLAYER_COLORS)]
            canvas.create_text(18, (y_top + y_bottom) / 2, text=name, anchor="w", fill=self.TEXT, font=("Segoe UI", 10, "bold"))
            canvas.create_rectangle(pad_left, y_top, pad_left + bar_width, y_bottom, fill=color, outline=color)
            canvas.create_text(pad_left + bar_width + 8, (y_top + y_bottom) / 2, text=f"{value:.2f}", anchor="w", fill=self.TEXT, font=("Segoe UI", 9))

    def _pct(self, value: float) -> str:
        return f"{value * 100:.1f}%"

    def _signed(self, value: float) -> str:
        if isinstance(value, int):
            return f"{value:+d}"
        return f"{value:+.2f}"
