from __future__ import annotations

import math
import textwrap
import tkinter as tk
from tkinter import simpledialog
from typing import Any

from .cards import cards_to_text


class GameStartupScreen:
    """Startup screen for configuring game options."""
    
    def __init__(self, title: str = "Gambling.ai - Poker Tournament"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("750x750")
        self.root.configure(bg="#0E1116")
        
        self.result = None
        
        # Main frame
        main = tk.Frame(self.root, bg="#0E1116")
        main.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        
        # Title
        title_label = tk.Label(
            main,
            text="GAMBLING.AI",
            bg="#0E1116",
            fg="#F39C12",
            font=("Consolas", 32, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        subtitle = tk.Label(
            main,
            text="Poker Tournament Simulator",
            bg="#0E1116",
            fg="#ABEBC6",
            font=("Consolas", 14)
        )
        subtitle.pack(pady=(0, 40))
        
        # Options frame
        options = tk.Frame(main, bg="#1C2833", relief=tk.SUNKEN, bd=1)
        options.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Table talk
        talk_frame = tk.Frame(options, bg="#1C2833")
        talk_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(talk_frame, text="Enable Agent Table Talk", bg="#1C2833", fg="#ECF0F1", font=("Consolas", 11)).pack(anchor="w")
        self.talk_var = tk.BooleanVar(value=True)
        tk.Checkbutton(talk_frame, variable=self.talk_var, bg="#1C2833", fg="#F39C12", selectcolor="#145A32").pack(anchor="w", pady=(5, 0))
        
        # Display mode
        mode_frame = tk.Frame(options, bg="#1C2833")
        mode_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(mode_frame, text="Display Mode", bg="#1C2833", fg="#ECF0F1", font=("Consolas", 11)).pack(anchor="w")
        self.mode_var = tk.StringVar(value="visual")
        
        tk.Radiobutton(mode_frame, text="Visual Table UI (Click-Through)", variable=self.mode_var, value="visual", 
                      bg="#1C2833", fg="#ABEBC6", selectcolor="#145A32").pack(anchor="w", pady=3)
        
        # Play-along mode
        play_frame = tk.Frame(options, bg="#1C2833")
        play_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(play_frame, text="Play Along Mode", bg="#1C2833", fg="#ECF0F1", font=("Consolas", 11)).pack(anchor="w")
        self.play_var = tk.BooleanVar(value=False)
        tk.Checkbutton(play_frame, variable=self.play_var, bg="#1C2833", fg="#F39C12", selectcolor="#145A32").pack(anchor="w", pady=(5, 0))
        
        # Number of rounds
        rounds_frame = tk.Frame(options, bg="#1C2833")
        rounds_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(rounds_frame, text="Number of Rounds", bg="#1C2833", fg="#ECF0F1", font=("Consolas", 11)).pack(anchor="w")
        self.rounds_var = tk.StringVar(value="10")
        tk.Spinbox(rounds_frame, from_=1, to=100, textvariable=self.rounds_var, width=10,
                  bg="#2C3E50", fg="#ECF0F1", font=("Consolas", 10)).pack(anchor="w", pady=(5, 0))
        
        # Buttons frame
        buttons = tk.Frame(main, bg="#0E1116")
        buttons.pack(fill=tk.X, pady=(20, 0))
        
        start_btn = tk.Button(
            buttons,
            text="▶ START GAME",
            font=("Consolas", 12, "bold"),
            bg="#27AE60",
            fg="white",
            activebackground="#229954",
            padx=20,
            pady=10,
            command=self._start
        )
        start_btn.pack(side=tk.LEFT, padx=10)
        
        quit_btn = tk.Button(
            buttons,
            text="QUIT",
            font=("Consolas", 12, "bold"),
            bg="#922B21",
            fg="white",
            activebackground="#641E16",
            padx=20,
            pady=10,
            command=self.root.quit
        )
        quit_btn.pack(side=tk.RIGHT, padx=10)
    
    def _start(self):
        self.result = {
            "table_talk": self.talk_var.get(),
            "mode": self.mode_var.get(),
            "play_along": self.play_var.get(),
            "rounds": int(self.rounds_var.get()),
        }
        self.root.quit()
    
    def show(self) -> dict[str, Any] | None:
        self.root.mainloop()
        return self.result


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
        # Bind canvas clicks to consume the event and prevent propagation
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        
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
        
        # Right-side buttons
        button_frame = tk.Frame(controls, bg="#1B2631")
        button_frame.pack(side=tk.RIGHT, padx=10, pady=6)
        
        self.fast_forward_button = tk.Button(
            button_frame,
            text="⏯ Fast Forward",
            width=14,
            command=self._toggle_fast_forward,
            bg="#E74C3C",
            fg="white",
            font=("Consolas", 10, "bold"),
            activebackground="#C0392B",
            relief=tk.RAISED,
            bd=2
        )
        self.fast_forward_button.pack(side=tk.RIGHT, padx=6)
        
        self.next_button = tk.Button(
            button_frame,
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
        self.next_button.pack(side=tk.RIGHT, padx=6)
        self.next_button.config(state=tk.DISABLED)
        
        self._step_waiting = False
        self._fast_forward = False
        self._canvas_width = 900
        self._canvas_height = 700
        self._tooltip_id = None
        self._tooltip_window = None
        
        # Dialogue tracking
        self._speech: dict[str, str] = {}
        self._dialogue_history: list[tuple[str, str]] = []  # (speaker, message)
        self._dialogue_counter = 0
        
        # Tool analytics tracking
        self._tool_analytics: dict[str, Any] = {}  # Store current tool outputs for display
        
        # Play-along mode flag
        self.play_along = False

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
    
    def set_tool_analytics(self, analytics: dict[str, Any]) -> None:
        """Store tool analytics for display on table."""
        self._tool_analytics = analytics
    
    def get_tool_analytics(self) -> dict[str, Any]:
        """Retrieve stored tool analytics."""
        return self._tool_analytics

    def _advance_step(self) -> None:
        """Called when next button is clicked."""
        self._step_waiting = False
        self.next_button.config(state=tk.DISABLED)
    
    def _toggle_fast_forward(self) -> None:
        """Toggle fast forward mode."""
        self._fast_forward = not self._fast_forward
        if self._fast_forward:
            self.fast_forward_button.config(bg="#27AE60", text="⏯ Stop FF")  # Green and show Stop when active
            self._step_waiting = False  # Auto-advance current step
            self.next_button.config(state=tk.DISABLED)  # Disable next button during fast forward
        else:
            self.fast_forward_button.config(bg="#E74C3C", text="⏯ Fast Forward")  # Red and show Fast Forward when inactive
            # If we were waiting, don't auto-enable next button - let wait_for_next handle it
            if not self._step_waiting:
                self.next_button.config(state=tk.DISABLED)
    
    def is_fast_forward_enabled(self) -> bool:
        """Check if fast forward mode is enabled."""
        return self._fast_forward
    
    def reset_fast_forward_flag(self) -> None:
        """Reset fast forward flag for next tournament."""
        self._fast_forward = False
        self.fast_forward_button.config(bg="#E74C3C", text="⏯ Fast Forward")

    def wait_for_next(self, label: str) -> None:
        """Wait for next button click or auto-advance if fast forward is enabled."""
        import time
        
        self.step_label.config(text=f"Step: {label}")
        
        # If fast forward is enabled, auto-advance immediately with visual update
        if self._fast_forward:
            try:
                self.root.update()
            except (tk.TclError, RuntimeError):
                pass  # Window was closed or other error
            return
        
        # Normal mode: wait for user to click Next button
        self.next_button.config(state=tk.NORMAL)
        self.fast_forward_button.config(state=tk.NORMAL)
        self._step_waiting = True
        
        start_time = time.time()
        timeout_seconds = 300  # 5 minute timeout
        
        while self._step_waiting:
            try:
                if not self.root.winfo_exists():
                    break
                
                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    break
                
                # Process all events properly
                self.root.update()
            except tk.TclError as e:
                # Window was closed
                break
            except RuntimeError as e:
                # Event processing error - skip and continue
                continue
            except Exception as e:
                # Catch any other errors and continue
                import traceback
                print(traceback.format_exc())
                break
        
        self.next_button.config(state=tk.DISABLED)
        self.fast_forward_button.config(state=tk.DISABLED)
        
        elapsed = time.time() - start_time
    
    def _on_canvas_resize(self, event: tk.Event) -> None:
        """Handle canvas resize to update seat positions."""
        self._canvas_width = event.width
        self._canvas_height = event.height
    
    def _on_canvas_click(self, event: tk.Event) -> None:
        """Handle canvas click events - consume them to prevent propagation."""
        # Simply consume the event without doing anything
        # This prevents clicks on the table from interfering with button controls
        return "break"  # Stop event propagation
    
    def _card_to_rank(self, card: Any) -> int:
        """Convert card object to rank (2-14, where 14 is Ace)."""
        if hasattr(card, "rank"):
            rank_map = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
            return rank_map.get(str(card.rank), 2)
        elif isinstance(card, str) and len(card) >= 1:
            rank_map = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
            return rank_map.get(card[0], 2)
        return 2
    
    def _rank_to_display(self, rank: int) -> str:
        """Convert numeric rank (2-14) to display text (2-10, J, Q, K, A)."""
        rank_display = {2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9", 10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"}
        return rank_display.get(rank, "?")



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
        # Clamp to canvas bounds to avoid clipping
        canvas_w = max(1, int(self._canvas_width))
        canvas_h = max(1, int(self._canvas_height))
        left = max(5, left)
        top = max(5, top)
        right = min(canvas_w - 5, right)
        bottom = min(canvas_h - 5, bottom)

        self.canvas.create_rectangle(left, top, right, bottom, fill=fill, outline="#ECF0F1", width=2)
        for tid in text_ids:
            self.canvas.tag_raise(tid)
    
    def _draw_text_box_compact(self, x: float, y: float, lines: list[str], fill: str, text_fill: str, anchor: str = "center") -> None:
        """Draw a more compact text box for player info."""
        text_ids = []
        line_gap = 14  # Smaller gap
        start_y = y - ((len(lines) - 1) * line_gap) / 2
        for idx, line in enumerate(lines):
            font_size = 9 if idx == 0 else 8  # Smaller font
            font_weight = "bold" if idx == 0 else "normal"
            text_id = self.canvas.create_text(
                x,
                start_y + idx * line_gap,
                text=line,
                font=("Consolas", font_size, font_weight),
                fill=text_fill,
                anchor=anchor,
            )
            text_ids.append(text_id)

        boxes = [self.canvas.bbox(tid) for tid in text_ids if self.canvas.bbox(tid)]
        if not boxes:
            return
        left = min(b[0] for b in boxes) - 8
        top = min(b[1] for b in boxes) - 6
        right = max(b[2] for b in boxes) + 8
        bottom = max(b[3] for b in boxes) + 6
        # Clamp to canvas bounds to avoid clipping
        canvas_w = max(1, int(self._canvas_width))
        canvas_h = max(1, int(self._canvas_height))
        left = max(5, left)
        top = max(5, top)
        right = min(canvas_w - 5, right)
        bottom = min(canvas_h - 5, bottom)

        self.canvas.create_rectangle(left, top, right, bottom, fill=fill, outline="#ECF0F1", width=1)
        for tid in text_ids:
            self.canvas.tag_raise(tid)

    def _draw_speech_bubble(self, x: float, y: float, text: str, speaker: str = "") -> None:
        wrapped = textwrap.fill(text[:100], width=22)
        
        # Adjust y position if we have a speaker header
        speaker_offset = 20 if speaker else 0
        
        text_id = self.canvas.create_text(
            x,
            y + speaker_offset,
            text=wrapped,
            font=("Consolas", 9),
            fill="#1B2631",
            justify="center",
        )
        bbox = self.canvas.bbox(text_id)
        if not bbox:
            return
        left = bbox[0] - 10
        top = bbox[1] - 7
        right = bbox[2] + 10
        bottom = bbox[3] + 7
        # Clamp bubble to canvas bounds to avoid clipping
        canvas_w = max(1, int(self._canvas_width))
        canvas_h = max(1, int(self._canvas_height))
        left = max(5, left)
        top = max(5, top)
        right = min(canvas_w - 5, right)
        bottom = min(canvas_h - 5, bottom)

        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            fill="#FCFCFD",
            outline="#AAB7B8",
            width=2,
        )
        
        # Draw speaker name header if provided
        if speaker:
            header_text = f"💬 {speaker}"
            header_id = self.canvas.create_text(
                x,
                y - 8,
                text=header_text,
                font=("Consolas", 8, "bold"),
                fill="#F39C12",
                justify="center",
            )
            header_bbox = self.canvas.bbox(header_id)
            if header_bbox:
                # Header background
                self.canvas.create_rectangle(
                    header_bbox[0] - 5, header_bbox[1] - 2,
                    header_bbox[2] + 5, header_bbox[3] + 2,
                    fill="#1C2833", outline="#F39C12", width=1
                )
                self.canvas.tag_raise(header_id)
        
        # Adjust speech pointer so it stays within bounds
        px1 = max(left + 8, min(x - 10, right - 12))
        px2 = max(left + 12, min(x + 10, right - 8))
        pointer_y = min(canvas_h - 5, bottom + 10)
        self.canvas.create_polygon(
            px1,
            bottom,
            px2,
            bottom,
            (px1 + px2) / 2,
            pointer_y,
            fill="#FCFCFD",
            outline="#AAB7B8",
            width=2,
        )
        self.canvas.tag_raise(text_id)

    def _draw_avatar_scaled(self, x: float, y: float, style: dict[str, str], is_actor: bool, scale: float = 1.0) -> None:
        """Draw avatar with optional scaling."""
        head_radius = 20 * scale
        body_width = 28 * scale
        body_height = 38 * scale
        
        self.canvas.create_oval(x - head_radius, y - 44 * scale, x + head_radius, y - 4 * scale, 
                               fill=style["skin"], outline="#17202A", width=1)
        self.canvas.create_rectangle(x - body_width, y - 4 * scale, x + body_width, y + body_height, 
                                    fill=style["shirt"], outline="#17202A", width=1)

        hat = style["hat"]
        hat_scale = scale
        if hat == "cap":
            self.canvas.create_arc(x - 24 * hat_scale, y - 60 * hat_scale, x + 24 * hat_scale, y - 24 * hat_scale, 
                                  start=0, extent=180, fill="#2E86C1", outline="#1B4F72", width=1)
            self.canvas.create_rectangle(x + 16 * hat_scale, y - 44 * hat_scale, x + 34 * hat_scale, y - 38 * hat_scale, 
                                        fill="#1B4F72", outline="#1B4F72")
        elif hat == "beanie":
            self.canvas.create_arc(x - 22 * hat_scale, y - 58 * hat_scale, x + 22 * hat_scale, y - 20 * hat_scale, 
                                  start=0, extent=180, fill="#8E44AD", outline="#4A235A", width=1)
            self.canvas.create_oval(x - 4 * hat_scale, y - 64 * hat_scale, x + 4 * hat_scale, y - 56 * hat_scale, 
                                   fill="#D2B4DE", outline="#4A235A")
        elif hat == "visor":
            self.canvas.create_arc(x - 24 * hat_scale, y - 56 * hat_scale, x + 24 * hat_scale, y - 24 * hat_scale, 
                                  start=0, extent=180, fill="#F1C40F", outline="#7D6608", width=1)
            self.canvas.create_rectangle(x + 16 * hat_scale, y - 40 * hat_scale, x + 34 * hat_scale, y - 34 * hat_scale, 
                                        fill="#7D6608", outline="#7D6608")
        elif hat == "fedora":
            self.canvas.create_rectangle(x - 26 * hat_scale, y - 52 * hat_scale, x + 26 * hat_scale, y - 44 * hat_scale, 
                                        fill="#784212", outline="#4E342E", width=1)
            self.canvas.create_rectangle(x - 14 * hat_scale, y - 70 * hat_scale, x + 14 * hat_scale, y - 52 * hat_scale, 
                                        fill="#A04000", outline="#4E342E", width=1)
        else:
            self.canvas.create_polygon(
                x - 24 * hat_scale,
                y - 52 * hat_scale,
                x + 24 * hat_scale,
                y - 52 * hat_scale,
                x + 16 * hat_scale,
                y - 40 * hat_scale,
                x - 16 * hat_scale,
                y - 40 * hat_scale,
                fill="#CB4335",
                outline="#78281F",
                width=1,
            )

        if is_actor:
            self.canvas.create_oval(x - 34 * scale, y - 62 * scale, x + 34 * scale, y + 40 * scale, 
                                   outline="#E74C3C", width=2)

    def _get_seat_positions(self) -> list[tuple[float, float]]:
        """Calculate seat positions evenly spaced around the table."""
        w = self._canvas_width
        h = self._canvas_height
        center_x = w / 2
        center_y = h / 2
        
        # Calculate radius based on window size - move further from center to edge of table
        outer_radius = min(w, h) / 2 - 70  # Reduced to push players to table edge
        
        # 5-seat arrangement: evenly spaced around the table
        # 72 degrees apart (360 / 5 = 72)
        angles = [90, 18, -54, -126, -198]  # Top (0), then 72° intervals clockwise
        
        seats = []
        for angle_deg in angles:
            angle_rad = math.radians(angle_deg)
            x = center_x + outer_radius * math.cos(angle_rad)
            y = center_y - outer_radius * math.sin(angle_rad)  # Negative because Y increases downward
            seats.append((x, y))
        
        return seats
    
    def _get_dialogue_position(self, seat_idx: int, player_x: float, player_y: float) -> tuple[float, float, float, float]:
        """Calculate dialogue box position close to agent."""
        if seat_idx == 0:  # Llama (top center)
            return (player_x, player_y + 60, 180, 60)
        elif seat_idx == 1:  # Mistral (upper right) - below avatar
            return (player_x, player_y + 80, 180, 60)
        elif seat_idx == 2:  # Qwen (lower right) - needs adjustment
            return (player_x, player_y - 100, 180, 60)
        elif seat_idx == 3:  # Mahesh (bottom/left) - perfect position
            return (player_x, player_y - 100, 180, 60)
        else:  # Phi (upper left, seat 4) - below avatar
            return (player_x, player_y + 80, 180, 60)
    
    def _draw_tool_analytics(self) -> None:
        """Draw tool analytics information on the table."""
        if not self._tool_analytics:
            return
        
        analytics = self._tool_analytics
        
        # Tool info displayed in top-left corner
        panel_x = 10
        panel_y = 10
        panel_width = 280
        panel_height = 20
        
        # Background panel
        self.canvas.create_rectangle(
            panel_x, panel_y,
            panel_x + panel_width, panel_y + panel_height,
            fill="#1C2833", outline="#F39C12", width=1
        )
        
        # Title
        self.canvas.create_text(
            panel_x + 5, panel_y + 8,
            text="⚙ TOOL ANALYTICS",
            font=("Consolas", 9, "bold"),
            fill="#F39C12",
            anchor="nw"
        )
        
        # Display individual tool metrics if available
        line_y = panel_y + 25
        line_height = 14
        max_lines = 6
        
        # Tool 1: Equity
        if "equity" in analytics:
            equity_pct = analytics["equity"].get("win_equity", 0) * 100
            self.canvas.create_text(
                panel_x + 5, line_y,
                text=f"1. Equity: {equity_pct:.1f}%",
                font=("Consolas", 8),
                fill="#ABEBC6",
                anchor="nw"
            )
            line_y += line_height
        
        # Tool 2: Pot Odds
        if "pot_odds" in analytics:
            breakeven = analytics["pot_odds"].get("break_even_equity", 0) * 100
            self.canvas.create_text(
                panel_x + 5, line_y,
                text=f"2. Break-even: {breakeven:.1f}%",
                font=("Consolas", 8),
                fill="#F8B88B",
                anchor="nw"
            )
            line_y += line_height
        
        # Tool 3: Bet Size
        if "bet_size" in analytics:
            rec_bet = analytics["bet_size"].get("recommended_bet", 0)
            self.canvas.create_text(
                panel_x + 5, line_y,
                text=f"3. Bet Size: {rec_bet}",
                font=("Consolas", 8),
                fill="#85C1E9",
                anchor="nw"
            )
            line_y += line_height
        
        # Tool 7: Bluff Opportunity
        if "bluff_opportunity" in analytics:
            bluff_score = analytics["bluff_opportunity"].get("opportunity_score", 0) * 100
            self.canvas.create_text(
                panel_x + 5, line_y,
                text=f"Bluff Score: {bluff_score:.0f}%",
                font=("Consolas", 8),
                fill="#D7BDE2",
                anchor="nw"
            )
            line_y += line_height

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
        avatar_draws: list[tuple[float, float, dict[str, str], bool]] = []

        for idx, player in enumerate(players):
            x, y = seats[idx]
            folded = getattr(player, "folded", False)
            name = getattr(player, "name", f"Player {idx + 1}")
            stack = getattr(player, "stack", 0)
            current_bet = getattr(player, "current_bet", 0)
            cards = getattr(player, "hole_cards", [])

            style = self._feature_styles[idx % len(self._feature_styles)]
            
            visible_cards = reveal_all_cards or (viewer_name is not None and viewer_name == name)
            if visible_cards and cards:
                # Display cards with suit symbols and proper rank formatting
                card_symbols = []
                for card in cards:
                    # Card may be a Card object, a tuple, an int, or a string.
                    rank_val = None
                    suit_val = ''
                    if hasattr(card, 'rank'):
                        rank_val = getattr(card, 'rank')
                        suit_val = getattr(card, 'suit', '')
                    elif isinstance(card, tuple) and len(card) >= 2:
                        rank_val, suit_val = card[0], card[1]
                    elif isinstance(card, int):
                        rank_val = card
                    elif isinstance(card, str):
                        # e.g., 'AS' or '10H' or 'A'
                        if len(card) >= 2 and card[0].isdigit():
                            # '10H' case
                            rank_token = card[:-1]
                            suit_val = card[-1]
                            try:
                                rank_val = int(rank_token)
                            except Exception:
                                rank_val = None
                        else:
                            rank_token = card[0]
                            suit_val = card[1] if len(card) > 1 else ''
                            rank_val = {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}.get(rank_token, None)

                    # Convert numeric rank to display char
                    display_rank = '?'
                    if isinstance(rank_val, int):
                        display_rank = self._rank_to_display(rank_val)
                    elif isinstance(rank_val, str):
                        # maybe already 'A','K', etc.
                        display_rank = rank_val

                    suit_symbol = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}.get(str(suit_val), '')
                    card_symbols.append(f"{display_rank}{suit_symbol}".strip())
                cards_text = " ".join(card_symbols)
            else:
                cards_text = "?? ??"
            
            # Enhanced panel styling with folded state
            if folded:
                panel_fill = "#34495E"
                text_fill = "#95A5A6"
            else:
                panel_fill = "#1C2833"
                text_fill = "#FFFFFF"
            
            panel_lines = [name, f"${stack}", f"Bet: {current_bet}", cards_text]
            
            self._draw_text_box_compact(
                x + 25,
                y,
                panel_lines,
                fill=panel_fill,
                text_fill=text_fill,
            )

            if idx == dealer_index:
                # Dealer button (smaller)
                self.canvas.create_oval(x + 50, y - 32, x + 68, y - 14, fill="#F1C40F", outline="black", width=1)
                self.canvas.create_text(x + 59, y - 23, text="D", font=("Consolas", 9, "bold"), fill="black")

            if name in self._speech and self._speech[name]:
                bubble_text = self._speech[name][:80]
                bubble_x, bubble_y, _, _ = self._get_dialogue_position(idx, x, y)
                self._draw_speech_bubble(bubble_x, bubble_y, bubble_text, speaker=name)

            avatar_draws.append((x - 40, y, style, name == current_actor))

        for avatar_x, avatar_y, style, is_actor in avatar_draws:
            self._draw_avatar_scaled(avatar_x, avatar_y, style, is_actor=is_actor, scale=0.65)

        # Physical dealer with enhanced styling (bottom center, smaller)
        dealer_x = center_x
        dealer_y = self._canvas_height - 80
        dealer_scale = 0.55
        self.canvas.create_oval(dealer_x - 28 * dealer_scale, dealer_y - 78 * dealer_scale, 
                               dealer_x + 28 * dealer_scale, dealer_y - 20 * dealer_scale, 
                               fill="#F5CBA7", outline="#17202A", width=1)
        self.canvas.create_rectangle(dealer_x - 36 * dealer_scale, dealer_y - 20 * dealer_scale, 
                                    dealer_x + 36 * dealer_scale, dealer_y + 36 * dealer_scale, 
                                    fill="#17202A", outline="#0E1116", width=1)
        self.canvas.create_rectangle(dealer_x - 40 * dealer_scale, dealer_y - 86 * dealer_scale, 
                                    dealer_x + 40 * dealer_scale, dealer_y - 74 * dealer_scale, 
                                    fill="#283747", outline="#1B2631", width=1)
        self.canvas.create_rectangle(dealer_x - 24 * dealer_scale, dealer_y - 112 * dealer_scale, 
                                    dealer_x + 24 * dealer_scale, dealer_y - 86 * dealer_scale, 
                                    fill="#34495E", outline="#1B2631", width=1)
        self.canvas.create_rectangle(dealer_x - 24 * dealer_scale, dealer_y - 94 * dealer_scale, 
                                    dealer_x + 24 * dealer_scale, dealer_y - 88 * dealer_scale, 
                                    fill="#F1C40F", outline="#F1C40F")
        self.canvas.create_text(dealer_x, dealer_y + 30, text=f"🎰 {dealer_name}", 
                               font=("Consolas", 9, "bold"), fill="#F7DC6F", anchor="center")
        
        if dealer_message:
            self._draw_speech_bubble(dealer_x, dealer_y - 120, dealer_message)
        
        # Draw tool analytics if available
        self._draw_tool_analytics()

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
