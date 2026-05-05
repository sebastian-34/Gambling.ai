from __future__ import annotations

import textwrap
import tkinter as tk
from tkinter import simpledialog
from typing import Any

from .cards import cards_to_text


class PokerTableUI:
    """Simple Tkinter table renderer for five-seat Hold'em games."""

    def __init__(self, title: str = "Poker Tournament") -> None:
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("1600x900")
        self.root.minsize(1400, 800)
        
        # Main container with table on left and dialogue log on right
        main_frame = tk.Frame(self.root, bg="#0E1116")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=3)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Left side: table canvas
        left_frame = tk.Frame(main_frame, bg="#0E1116")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.canvas = tk.Canvas(left_frame, bg="#145A32", highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        
        # Right side: dialogue log
        right_frame = tk.Frame(main_frame, bg="#0E1116")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Dialogue log title
        log_title = tk.Label(right_frame, text="📢 TABLE TALK", fg="#F39C12", bg="#0E1116", font=("Consolas", 11, "bold"))
        log_title.grid(row=0, column=0, columnspan=2, pady=5, sticky="ew")
        
        # Dialogue log scrollable text area
        scrollbar = tk.Scrollbar(right_frame)
        scrollbar.grid(row=1, column=1, sticky="ns")
        
        self.dialogue_text = tk.Text(
            right_frame,
            width=35,
            bg="#1C2833",
            fg="#ECF0F1",
            font=("Consolas", 8),
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bd=1,
            relief=tk.SUNKEN
        )
        self.dialogue_text.grid(row=1, column=0, sticky="nsew")
        scrollbar.config(command=self.dialogue_text.yview)
        
        # Configure text tags for styling
        self.dialogue_text.tag_config("timestamp", foreground="#7F8C8D", font=("Consolas", 8))
        self.dialogue_text.tag_config("speaker", foreground="#F39C12", font=("Consolas", 9, "bold"))
        self.dialogue_text.tag_config("message", foreground="#ECF0F1", font=("Consolas", 9))
        
        # Control bar
        controls = tk.Frame(self.root, bg="#1B2631")
        controls.pack(fill=tk.X, padx=10, pady=5)
        self.step_label = tk.Label(controls, text="", fg="#F7DC6F", bg="#1B2631", anchor="w", font=("Consolas", 10, "bold"))
        self.step_label.pack(side=tk.LEFT, padx=10, pady=8)
        self.next_button = tk.Button(
            controls,
            text="▶ Next",
            width=14,
            command=self._advance_step,
            bg="#27AE60",
            fg="white",
            font=("Consolas", 10, "bold"),
            activebackground="#229954",
            relief=tk.RAISED,
            bd=2
        )
        self.next_button.pack(side=tk.RIGHT, padx=12, pady=6)
        self.next_button.config(state=tk.DISABLED)
        self._step_waiting = False
        self._canvas_width = 900
        self._canvas_height = 700
        
        # Dialogue tracking
        self._speech: dict[str, str] = {}
        self._dialogue_history: list[tuple[str, str]] = []  # (speaker, message)
        self._dialogue_counter = 0

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
        # Add to dialogue history if not empty
        if message.strip():
            self._dialogue_counter += 1
            self._dialogue_history.append((name, message))
            self._update_dialogue_log(name, message)
    
    def _update_dialogue_log(self, speaker: str, message: str) -> None:
        """Update the dialogue log display."""
        self.dialogue_text.config(state=tk.NORMAL)
        
        # Add timestamp and message
        timestamp = f"[{self._dialogue_counter:02d}] "
        
        self.dialogue_text.insert(tk.END, timestamp, "timestamp")
        self.dialogue_text.insert(tk.END, f"{speaker}: ", "speaker")
        self.dialogue_text.insert(tk.END, f"{message}\n", "message")
        
        # Auto-scroll to bottom
        self.dialogue_text.see(tk.END)
        self.dialogue_text.config(state=tk.DISABLED)
    
    def clear_dialogue_log(self) -> None:
        """Clear the dialogue history for a new hand."""
        self._dialogue_history.clear()
        self._dialogue_counter = 0
        self.dialogue_text.config(state=tk.NORMAL)
        self.dialogue_text.delete("1.0", tk.END)
        self.dialogue_text.config(state=tk.DISABLED)

    def _advance_step(self) -> None:
        """Called when next button is clicked."""
        self._step_waiting = False
        self.next_button.config(state=tk.DISABLED)

    def wait_for_next(self, label: str) -> None:
        """Wait for next button click - process Tkinter events until clicked."""
        import time
        
        self.step_label.config(text=f"Step: {label}")
        self.next_button.config(state=tk.NORMAL)
        self._step_waiting = True
        print(f"[DEBUG] wait_for_next started for: {label}")
        
        start_time = time.time()
        timeout_seconds = 300  # 5 minute timeout
        
        while self._step_waiting:
            try:
                if not self.root.winfo_exists():
                    print("[DEBUG] Root window no longer exists")
                    break
                
                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    print(f"[DEBUG] wait_for_next timeout after {timeout_seconds}s for: {label}")
                    break
                
                self.root.update()
            except tk.TclError as e:
                # Window was closed
                print(f"[DEBUG] TclError in wait_for_next: {e}")
                break
            except Exception as e:
                # Catch any other errors and continue
                print(f"[DEBUG] Exception in wait_for_next: {type(e).__name__}: {e}")
                import traceback
                print(traceback.format_exc())
                break
        
        elapsed = time.time() - start_time
        print(f"[DEBUG] wait_for_next finished for: {label}, elapsed: {elapsed:.2f}s")
    
    def _on_canvas_resize(self, event: tk.Event) -> None:
        """Handle canvas resize to update seat positions."""
        self._canvas_width = event.width
        self._canvas_height = event.height



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

    def _draw_speech_bubble(self, x: float, y: float, text: str) -> None:
        wrapped = textwrap.fill(text[:120], width=28)
        text_id = self.canvas.create_text(
            x,
            y,
            text=wrapped,
            font=("Consolas", 10),
            fill="#1B2631",
            justify="center",
        )
        bbox = self.canvas.bbox(text_id)
        if not bbox:
            return
        left = bbox[0] - 12
        top = bbox[1] - 8
        right = bbox[2] + 12
        bottom = bbox[3] + 8
        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            fill="#FCFCFD",
            outline="#AAB7B8",
            width=2,
        )
        self.canvas.create_polygon(
            x - 10,
            bottom,
            x + 10,
            bottom,
            x,
            bottom + 10,
            fill="#FCFCFD",
            outline="#AAB7B8",
            width=2,
        )
        self.canvas.tag_raise(text_id)

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

    def _get_seat_positions(self) -> list[tuple[float, float]]:
        """Calculate seat positions based on canvas size - all outside the table."""
        w = self._canvas_width
        h = self._canvas_height
        center_x = w / 2
        center_y = h / 2
        
        # Position players well outside the table
        # Table margin is 40px, so position seats at safe distance
        
        return [
            (center_x, 20),                              # Top center (seat 0) - well above
            (w - 80, center_y - 120),                    # Right upper (seat 1) - well right
            (w - 80, center_y + 120),                    # Right lower (seat 2) - well right
            (center_x, h - 20),                          # Bottom center (seat 3) - well below
            (40, center_y),                              # Left (seat 4) - well left
        ]
    
    def _get_dialogue_position(self, seat_idx: int, player_x: float, player_y: float) -> tuple[float, float, float, float]:
        """Calculate dialogue box position based on seat position."""
        if seat_idx == 0:  # Top center
            return (player_x, player_y + 80, 200, 80)
        elif seat_idx == 1:  # Right upper
            return (player_x - 250, player_y - 60, 200, 100)
        elif seat_idx == 2:  # Right lower
            return (player_x - 250, player_y - 60, 200, 100)
        elif seat_idx == 3:  # Bottom center
            return (player_x, player_y - 120, 200, 80)
        else:  # Left (seat 4)
            return (player_x + 150, player_y - 60, 200, 100)

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
        try:
            self._render_impl(players, community_cards, pot, dealer_index, street, current_actor, viewer_name, reveal_all_cards, dealer_name, dealer_message)
        except Exception as e:
            print(f"Error rendering: {e}")
            try:
                self.root.update_idletasks()
            except Exception:
                pass
    
    def _render_impl(
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

        # Enhanced table felt with gradient effect (using overlapping ovals)
        margin = 40
        self.canvas.create_oval(margin, margin, self._canvas_width - margin, self._canvas_height - margin, fill="#1E8449", outline="#0B3D2E", width=8)
        self.canvas.create_oval(margin + 10, margin + 10, self._canvas_width - margin - 10, self._canvas_height - margin - 10, fill="#2A9D5D", outline="", width=0)
        
        # Center display with enhanced styling
        center_x = self._canvas_width / 2
        center_y = self._canvas_height / 2
        
        self.canvas.create_text(
            center_x,
            center_y - 80,
            text=f"♠ POT: {pot} ♠",
            font=("Consolas", 28, "bold"),
            fill="#F7DC6F",
        )
        self.canvas.create_text(
            center_x,
            center_y - 30,
            text=f"Street: {street.title()}",
            font=("Consolas", 16, "bold"),
            fill="#ABEBC6",
        )
        self.canvas.create_text(
            center_x,
            center_y + 20,
            text=f"Board: {cards_to_text(community_cards) if community_cards else '-- -- --'}",
            font=("Consolas", 14),
            fill="#FFFFFF",
        )

        seats = self._get_seat_positions()

        for idx, player in enumerate(players):
            x, y = seats[idx]
            folded = getattr(player, "folded", False)
            name = getattr(player, "name", f"Player {idx + 1}")
            stack = getattr(player, "stack", 0)
            current_bet = getattr(player, "current_bet", 0)
            cards = getattr(player, "hole_cards", [])

            style = self._feature_styles[idx % len(self._feature_styles)]
            # Avatar position: to the left of the player panel
            avatar_x = x - 55
            avatar_y = y
            self._draw_avatar(avatar_x, avatar_y, style, is_actor=(name == current_actor))

            visible_cards = reveal_all_cards or (viewer_name is not None and viewer_name == name)
            cards_text = cards_to_text(cards) if visible_cards and cards else "?? ??"
            
            # Enhanced panel styling with folded state
            if folded:
                panel_fill = "#34495E"
                text_fill = "#95A5A6"
            else:
                panel_fill = "#1C2833"
                text_fill = "#FFFFFF"
            
            # Player info panel position
            self._draw_text_box(
                x + 30,
                y,
                [name, f"💰 {stack}", f"Bet: {current_bet}", cards_text],
                fill=panel_fill,
                text_fill=text_fill,
            )

            if idx == dealer_index:
                # Dealer button
                self.canvas.create_oval(x + 60, y - 40, x + 85, y - 15, fill="#F1C40F", outline="black", width=2)
                self.canvas.create_text(x + 72, y - 27, text="D", font=("Consolas", 11, "bold"), fill="black")

            if name in self._speech and self._speech[name]:
                bubble_text = self._speech[name][:80]
                self._draw_speech_bubble(x + 20, y - 98, bubble_text)

        # Physical dealer with enhanced styling (bottom center)
        dealer_x = center_x
        dealer_y = self._canvas_height - 70
        self.canvas.create_oval(dealer_x - 28, dealer_y - 78, dealer_x + 28, dealer_y - 20, fill="#F5CBA7", outline="#17202A", width=2)
        self.canvas.create_rectangle(dealer_x - 36, dealer_y - 20, dealer_x + 36, dealer_y + 36, fill="#17202A", outline="#0E1116", width=2)
        self.canvas.create_rectangle(dealer_x - 40, dealer_y - 86, dealer_x + 40, dealer_y - 74, fill="#283747", outline="#1B2631", width=2)
        self.canvas.create_rectangle(dealer_x - 24, dealer_y - 112, dealer_x + 24, dealer_y - 86, fill="#34495E", outline="#1B2631", width=2)
        self.canvas.create_rectangle(dealer_x - 24, dealer_y - 94, dealer_x + 24, dealer_y - 88, fill="#F1C40F", outline="#F1C40F")
        self._draw_text_box(dealer_x, dealer_y + 50, [f"🎰 {dealer_name}"], fill="#1B2631", text_fill="#F7DC6F")
        
        if dealer_message:
            self._draw_speech_bubble(dealer_x + 170, dealer_y - 88, dealer_message)

        try:
            self.root.update_idletasks()
        except tk.TclError:
            pass  # Window was closed

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
