from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog
from typing import Any

from .cards import cards_to_text


class PokerTableUI:
    """Simple Tkinter table renderer for five-seat Hold'em games."""

    def __init__(self, title: str = "Poker Tournament") -> None:
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("1180x820")
        self.canvas = tk.Canvas(self.root, width=1180, height=760, bg="#145A32", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        controls = tk.Frame(self.root, bg="#1B2631")
        controls.pack(fill=tk.X)
        self.step_label = tk.Label(controls, text="", fg="white", bg="#1B2631", anchor="w")
        self.step_label.pack(side=tk.LEFT, padx=10, pady=8)
        self.next_button = tk.Button(controls, text="Next", width=14, command=self._advance_step)
        self.next_button.pack(side=tk.RIGHT, padx=12, pady=6)
        self.next_button.config(state=tk.DISABLED)
        self._step_var = tk.BooleanVar(value=False)
        self._speech: dict[str, str] = {}

        self._feature_styles = [
            {"skin": "#F5CBA7", "shirt": "#1F618D", "hat": "cap"},
            {"skin": "#D7BDE2", "shirt": "#117864", "hat": "beanie"},
            {"skin": "#FAD7A0", "shirt": "#7D6608", "hat": "visor"},
            {"skin": "#F9E79F", "shirt": "#922B21", "hat": "fedora"},
            {"skin": "#F5B7B1", "shirt": "#4A235A", "hat": "bandana"},
        ]

    def clear_speech(self) -> None:
        self._speech.clear()

    def set_speech(self, name: str, message: str) -> None:
        self._speech[name] = message

    def _advance_step(self) -> None:
        self._step_var.set(True)

    def wait_for_next(self, label: str) -> None:
        self.step_label.config(text=f"Step: {label}")
        self.next_button.config(state=tk.NORMAL)
        self._step_var.set(False)
        self.root.wait_variable(self._step_var)
        self.next_button.config(state=tk.DISABLED)

    def _draw_text_box(self, x: float, y: float, lines: list[str], fill: str, text_fill: str, anchor: str = "center") -> None:
        text_ids = []
        line_gap = 18
        start_y = y - ((len(lines) - 1) * line_gap) / 2
        for idx, line in enumerate(lines):
            text_id = self.canvas.create_text(
                x,
                start_y + idx * line_gap,
                text=line,
                font=("Consolas", 11, "bold" if idx == 0 else "normal"),
                fill=text_fill,
                anchor=anchor,
            )
            text_ids.append(text_id)

        boxes = [self.canvas.bbox(tid) for tid in text_ids if self.canvas.bbox(tid)]
        if not boxes:
            return
        left = min(b[0] for b in boxes) - 10
        top = min(b[1] for b in boxes) - 8
        right = max(b[2] for b in boxes) + 10
        bottom = max(b[3] for b in boxes) + 8
        self.canvas.create_rectangle(left, top, right, bottom, fill=fill, outline="#ECF0F1", width=2)
        for tid in text_ids:
            self.canvas.tag_raise(tid)

    def _draw_avatar(self, x: float, y: float, style: dict[str, str], is_actor: bool) -> None:
        self.canvas.create_oval(x - 20, y - 44, x + 20, y - 4, fill=style["skin"], outline="#17202A", width=2)
        self.canvas.create_rectangle(x - 28, y - 4, x + 28, y + 34, fill=style["shirt"], outline="#17202A", width=2)

        hat = style["hat"]
        if hat == "cap":
            self.canvas.create_arc(x - 24, y - 60, x + 24, y - 24, start=0, extent=180, fill="#2E86C1", outline="#1B4F72", width=2)
            self.canvas.create_rectangle(x + 16, y - 44, x + 34, y - 38, fill="#1B4F72", outline="#1B4F72")
        elif hat == "beanie":
            self.canvas.create_arc(x - 22, y - 58, x + 22, y - 20, start=0, extent=180, fill="#8E44AD", outline="#4A235A", width=2)
            self.canvas.create_oval(x - 4, y - 64, x + 4, y - 56, fill="#D2B4DE", outline="#4A235A")
        elif hat == "visor":
            self.canvas.create_arc(x - 24, y - 56, x + 24, y - 24, start=0, extent=180, fill="#F1C40F", outline="#7D6608", width=2)
            self.canvas.create_rectangle(x + 16, y - 40, x + 34, y - 34, fill="#7D6608", outline="#7D6608")
        elif hat == "fedora":
            self.canvas.create_rectangle(x - 26, y - 52, x + 26, y - 44, fill="#784212", outline="#4E342E", width=2)
            self.canvas.create_rectangle(x - 14, y - 70, x + 14, y - 52, fill="#A04000", outline="#4E342E", width=2)
        else:
            self.canvas.create_polygon(
                x - 24,
                y - 52,
                x + 24,
                y - 52,
                x + 16,
                y - 40,
                x - 16,
                y - 40,
                fill="#CB4335",
                outline="#78281F",
                width=2,
            )

        if is_actor:
            self.canvas.create_oval(x - 34, y - 62, x + 34, y + 40, outline="#E74C3C", width=3)

    def render(
        self,
        players: list[Any],
        community_cards: list[Any],
        pot: int,
        dealer_index: int,
        street: str,
        current_actor: str | None = None,
        viewer_name: str | None = None,
        reveal_all_cards: bool = True,
        dealer_name: str = "Dealer",
        dealer_message: str = "",
    ) -> None:
        self.canvas.delete("all")

        # Table felt and center panel.
        self.canvas.create_oval(120, 120, 980, 640, fill="#1E8449", outline="#0B3D2E", width=6)
        self.canvas.create_text(
            550,
            300,
            text=f"POT: {pot}",
            font=("Consolas", 24, "bold"),
            fill="white",
        )
        self.canvas.create_text(
            550,
            340,
            text=f"Street: {street.title()}",
            font=("Consolas", 15, "bold"),
            fill="#F7DC6F",
        )
        self.canvas.create_text(
            550,
            380,
            text=f"Board: {cards_to_text(community_cards) if community_cards else '--'}",
            font=("Consolas", 16),
            fill="white",
        )

        seats = [(550, 150), (900, 280), (760, 560), (340, 560), (200, 280)]

        for idx, player in enumerate(players):
            x, y = seats[idx]
            folded = getattr(player, "folded", False)
            name = getattr(player, "name", f"Player {idx + 1}")
            stack = getattr(player, "stack", 0)
            current_bet = getattr(player, "current_bet", 0)
            cards = getattr(player, "hole_cards", [])

            style = self._feature_styles[idx % len(self._feature_styles)]
            self._draw_avatar(x - 70, y + 8, style, is_actor=(name == current_actor))

            visible_cards = reveal_all_cards or (viewer_name is not None and viewer_name == name)
            cards_text = cards_to_text(cards) if visible_cards and cards else "?? ??"
            panel_fill = "#5D6D7E" if folded else "#1C2833"
            self._draw_text_box(
                x + 24,
                y,
                [name, f"Stack: {stack}", f"Bet: {current_bet}", cards_text],
                fill=panel_fill,
                text_fill="white",
            )

            if idx == dealer_index:
                self.canvas.create_oval(x + 98, y - 54, x + 122, y - 30, fill="#F1C40F", outline="black")
                self.canvas.create_text(x + 110, y - 42, text="D", font=("Consolas", 10, "bold"), fill="black")

            if name in self._speech and self._speech[name]:
                bubble_text = self._speech[name][:80]
                text_id = self.canvas.create_text(
                    x + 20,
                    y - 98,
                    text=bubble_text,
                    font=("Consolas", 10),
                    fill="#1B2631",
                )
                bbox = self.canvas.bbox(text_id)
                if bbox:
                    self.canvas.create_rectangle(
                        bbox[0] - 10,
                        bbox[1] - 6,
                        bbox[2] + 10,
                        bbox[3] + 6,
                        fill="#FBFCFC",
                        outline="#BDC3C7",
                        width=1,
                    )
                    self.canvas.tag_raise(text_id)

        # Physical dealer with a cool hat.
        dealer_x = 550
        dealer_y = 700
        self.canvas.create_oval(dealer_x - 28, dealer_y - 78, dealer_x + 28, dealer_y - 20, fill="#F5CBA7", outline="#17202A", width=2)
        self.canvas.create_rectangle(dealer_x - 36, dealer_y - 20, dealer_x + 36, dealer_y + 36, fill="#17202A", outline="#0E1116", width=2)
        self.canvas.create_rectangle(dealer_x - 40, dealer_y - 86, dealer_x + 40, dealer_y - 74, fill="#283747", outline="#1B2631", width=2)
        self.canvas.create_rectangle(dealer_x - 24, dealer_y - 112, dealer_x + 24, dealer_y - 86, fill="#34495E", outline="#1B2631", width=2)
        self.canvas.create_rectangle(dealer_x - 24, dealer_y - 94, dealer_x + 24, dealer_y - 88, fill="#F1C40F", outline="#F1C40F")
        self._draw_text_box(dealer_x + 170, dealer_y - 40, [dealer_name], fill="#1B2631", text_fill="#F7DC6F")
        if dealer_message:
            text_id = self.canvas.create_text(
                dealer_x + 170,
                dealer_y - 88,
                text=dealer_message[:100],
                font=("Consolas", 10),
                fill="#1B2631",
            )
            bbox = self.canvas.bbox(text_id)
            if bbox:
                self.canvas.create_rectangle(
                    bbox[0] - 10,
                    bbox[1] - 6,
                    bbox[2] + 10,
                    bbox[3] + 6,
                    fill="#FBFCFC",
                    outline="#BDC3C7",
                    width=1,
                )
                self.canvas.tag_raise(text_id)

        self.root.update_idletasks()
        self.root.update()

    def ask_optional_chat(self, player_name: str) -> str:
        message = simpledialog.askstring(
            "Table Talk",
            f"{player_name}, optional chat message before your action (leave blank to skip):",
            parent=self.root,
        )
        return (message or "").strip()

    def ask_action(self, player_name: str, to_call: int, min_raise: int, stack: int) -> tuple[str, int]:
        while True:
            default_action = "check" if to_call == 0 else "call"
            action = simpledialog.askstring(
                "Your Action",
                (
                    f"{player_name} action? fold/call/check/raise\n"
                    f"to_call={to_call}, min_raise={min_raise}, stack={stack}\n"
                    f"Press Enter for {default_action}."
                ),
                parent=self.root,
            )
            action = (action or default_action).strip().lower()

            if action not in {"fold", "call", "check", "raise"}:
                continue

            if action == "raise":
                amount_text = simpledialog.askstring(
                    "Raise Amount",
                    f"Enter raise amount (minimum {min_raise}):",
                    parent=self.root,
                )
                try:
                    raise_amount = int((amount_text or "0").strip())
                except ValueError:
                    raise_amount = 0
                return "raise", max(min_raise, raise_amount)

            return action, 0
