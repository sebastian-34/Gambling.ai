from __future__ import annotations

from dataclasses import dataclass, field
import random
import sys
from typing import Any

from .agents import DealerAgent, Decision, DecisionContext, PokerAgent
from .cards import Card, cards_to_text, deal_hand, deal_one, evaluate_best_hand, shuffled_deck

try:
    from .ui import PokerTableUI
except Exception:
    PokerTableUI = None  # type: ignore[assignment]


@dataclass
class PlayerState:
    name: str
    agent: PokerAgent
    stack: int
    hole_cards: list[Card] = field(default_factory=list)
    folded: bool = False
    current_bet: int = 0


class PokerGame:
    MAX_RAISES_PER_STREET = 4
    MAX_CHAT_HISTORY = 20

    def __init__(
        self,
        agents: list[PokerAgent],
        starting_stack: int = 1000,
        small_blind: int = 5,
        big_blind: int = 10,
        seed: int | None = None,
        verbose: bool = True,
        enable_table_talk: bool = True,
        output_mode: str = "live",
        table_ui: Any | None = None,
        play_along: bool = False,
        human_player_name: str = "You",
        dealer_agent: DealerAgent | None = None,
        step_through: bool = False,
    ) -> None:
        if len(agents) != 5:
            raise ValueError("This simulation expects exactly 5 agents.")
        if small_blind <= 0 or big_blind <= 0:
            raise ValueError("Blinds must be positive integers.")
        if small_blind >= big_blind:
            raise ValueError("small_blind must be lower than big_blind.")

        self.rng = random.Random(seed)
        self.verbose = verbose
        self.enable_table_talk = enable_table_talk
        self.output_mode = output_mode
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.players: list[PlayerState] = [
            PlayerState(name=agent.name, agent=agent, stack=starting_stack) for agent in agents
        ]
        self.round_number = 0
        self.dealer_idx = 0
        self._replay_log: list[str] = []
        self.table_ui = table_ui
        self.play_along = play_along
        self.human_player_name = human_player_name
        self._current_street = "preflop"
        self._community_cards: list[Card] = []
        self._pot = 0
        self.dealer_agent = dealer_agent
        self.step_through = step_through
        self._dealer_line = "Ready to deal."

        if self.output_mode not in {"live", "replay"}:
            raise ValueError("output_mode must be 'live' or 'replay'.")

    def _log(self, message: str) -> None:
        if self.output_mode == "replay":
            self._replay_log.append(message)
            return
        if self.verbose:
            print(message)

    def _render_table(self, current_actor: str | None = None) -> None:
        if not self.table_ui:
            return
        self.table_ui.render(
            players=self.players,
            community_cards=self._community_cards,
            pot=self._pot,
            dealer_index=self.dealer_idx,
            street=self._current_street,
            current_actor=current_actor,
            viewer_name=self.human_player_name if self.play_along else None,
            reveal_all_cards=not self.play_along,
            dealer_name=self.dealer_agent.name if self.dealer_agent else "Dealer",
            dealer_message=self._dealer_line,
        )

    def _step_wait(self, label: str) -> None:
        if self.table_ui and self.step_through:
            self.table_ui.wait_for_next(label)

    def _dealer_say(self, message: str) -> None:
        if not message:
            return
        self._dealer_line = message
        self._log(f"Dealer: {message}")
        self._render_table()

    def _prompt_human_chat(self) -> str:
        if self.table_ui:
            return self.table_ui.ask_optional_chat(self.human_player_name)
        if not sys.stdin.isatty():
            return ""
        return input("Optional table-talk message (blank to skip): ").strip()

    def _prompt_human_decision(self, ctx: DecisionContext) -> Decision:
        if self.table_ui:
            action, raise_amount = self.table_ui.ask_action(
                player_name=self.human_player_name,
                to_call=ctx.to_call,
                min_raise=ctx.min_raise,
                stack=ctx.stack,
            )
            return Decision(action=action, raise_amount=raise_amount)

        if not sys.stdin.isatty():
            # Non-interactive fallback keeps automation from blocking.
            return Decision(action="check" if ctx.to_call == 0 else "call", raise_amount=0)

        default_action = "check" if ctx.to_call == 0 else "call"
        while True:
            raw = input(
                (
                    f"Your action [fold/call/check/raise] "
                    f"(to_call={ctx.to_call}, min_raise={ctx.min_raise}, stack={ctx.stack}, "
                    f"Enter={default_action}): "
                )
            ).strip().lower()
            action = raw or default_action
            if action not in {"fold", "call", "check", "raise"}:
                print("Invalid action.")
                continue
            if action == "raise":
                amount_raw = input(f"Raise amount (minimum {ctx.min_raise}): ").strip()
                try:
                    raise_amount = int(amount_raw)
                except ValueError:
                    raise_amount = 0
                return Decision(action="raise", raise_amount=max(ctx.min_raise, raise_amount))
            return Decision(action=action, raise_amount=0)

    def get_replay_text(self) -> str:
        return "\n".join(self._replay_log)

    def _print_progress_bar(self, completed: int, total: int) -> None:
        if total <= 0:
            return
        bar_width = 28
        ratio = completed / total
        filled = int(bar_width * ratio)
        bar = "#" * filled + "-" * (bar_width - filled)
        percent = int(ratio * 100)
        line = f"Simulating tournament: [{bar}] {completed}/{total} hands ({percent:>3}%)"
        if sys.stdout.isatty():
            sys.stdout.write(f"\r{line}")
            sys.stdout.flush()
        else:
            print(line)

    def _estimate_strength(self, hole_cards: list[Card], community_cards: list[Card]) -> float:
        cards = hole_cards + community_cards
        if len(cards) >= 5:
            rank = evaluate_best_hand(cards)
            category = rank[0]
            kickers = rank[1]
            kicker_score = sum(v * (0.01 ** i) for i, v in enumerate(kickers, start=1))
            return min(0.99, category / 8 + kicker_score)

        # Preflop heuristic based on pair/suited/high cards.
        a, b = hole_cards
        high = max(a.rank, b.rank)
        low = min(a.rank, b.rank)
        is_pair = a.rank == b.rank
        is_suited = a.suit == b.suit
        gap = abs(a.rank - b.rank)

        strength = 0.2 + high / 20 + low / 30
        if is_pair:
            strength += 0.2
        if is_suited:
            strength += 0.06
        if gap <= 1:
            strength += 0.04
        elif gap >= 5:
            strength -= 0.05
        return max(0.05, min(0.95, strength))

    def _post_blind(self, player: PlayerState, amount: int) -> int:
        if player.folded or player.stack <= 0:
            return 0
        if player.stack < amount:
            # Simplified model: if player cannot post blind, they sit out this hand.
            player.folded = True
            return 0
        player.stack -= amount
        player.current_bet += amount
        return amount

    def _betting_round(
        self,
        ordered_players: list[PlayerState],
        pot: int,
        street: str,
        community_cards: list[Card],
        hand_chat: list[str],
    ) -> int:
        for player in ordered_players:
            if not player.folded:
                player.current_bet = 0

        if street == "preflop":
            sb = ordered_players[1]
            bb = ordered_players[2]
            pot += self._post_blind(sb, self.small_blind)
            pot += self._post_blind(bb, self.big_blind)
            current_bet = max(sb.current_bet, bb.current_bet)
            action_queue = ordered_players[3:] + ordered_players[:3]
            min_raise = self.big_blind
            self._log(f"Blinds posted: {sb.name}={self.small_blind}, {bb.name}={self.big_blind}")
        else:
            current_bet = 0
            action_queue = [p for p in ordered_players if not p.folded]
            min_raise = self.big_blind

        raises_made = 0

        while action_queue:
            remaining = [p for p in ordered_players if not p.folded]
            if len(remaining) <= 1:
                break

            player = action_queue.pop(0)
            if player.folded:
                continue

            self._render_table(current_actor=player.name)
            self._step_wait(f"{street.title()}: {player.name} to act")

            to_call = max(0, current_bet - player.current_bet)
            strength = self._estimate_strength(player.hole_cards, community_cards)
            ctx = DecisionContext(
                hand_strength=strength,
                to_call=to_call,
                current_bet=current_bet,
                pot=pot,
                min_raise=min_raise,
                stack=player.stack,
                street=street,
                community_count=len(community_cards),
                player_name=player.name,
                recent_chat=hand_chat[-8:],
            )
            if self.play_along and player.name == self.human_player_name:
                if self.enable_table_talk:
                    user_chat = self._prompt_human_chat()
                    if user_chat:
                        line = f"{player.name}: {user_chat}"
                        self._log(f"  {line}")
                        self._append_chat(hand_chat, line)
                decision = self._prompt_human_decision(ctx)
            else:
                decision = player.agent.decide(ctx, self.rng)

            if self.dealer_agent:
                decision, dealer_note = self.dealer_agent.validate_decision(
                    decision=decision,
                    ctx=ctx,
                    raises_made=raises_made,
                    max_raises=self.MAX_RAISES_PER_STREET,
                )
                if dealer_note:
                    self._dealer_say(dealer_note)

            if decision.action == "fold":
                player.folded = True
                self._log(f"{player.name:<12} folds")
                self._append_chat(hand_chat, f"{player.name} folds.")
                self._render_table()
                continue

            if decision.action == "raise" and raises_made >= self.MAX_RAISES_PER_STREET:
                decision.action = "call" if to_call > 0 else "check"

            if decision.action in {"call", "check"}:
                if to_call > 0:
                    if player.stack < to_call:
                        player.folded = True
                        self._log(f"{player.name:<12} folds (insufficient chips to call)")
                        continue
                    player.stack -= to_call
                    player.current_bet += to_call
                    pot += to_call
                    self._log(f"{player.name:<12} calls {to_call}")
                    self._append_chat(hand_chat, f"{player.name} calls {to_call}.")
                else:
                    self._log(f"{player.name:<12} checks")
                    self._append_chat(hand_chat, f"{player.name} checks.")
                self._render_table()
                continue

            if decision.action == "raise":
                raise_amount = max(min_raise, decision.raise_amount)
                target_bet = current_bet + raise_amount
                to_put = target_bet - player.current_bet

                if player.stack < to_put:
                    if to_call > 0 and player.stack >= to_call:
                        player.stack -= to_call
                        player.current_bet += to_call
                        pot += to_call
                        self._log(f"{player.name:<12} calls {to_call}")
                        self._append_chat(hand_chat, f"{player.name} calls {to_call}.")
                    elif to_call == 0:
                        self._log(f"{player.name:<12} checks")
                        self._append_chat(hand_chat, f"{player.name} checks.")
                    else:
                        player.folded = True
                        self._log(f"{player.name:<12} folds (insufficient chips)")
                        self._append_chat(hand_chat, f"{player.name} folds under pressure.")
                    self._render_table()
                    continue

                player.stack -= to_put
                player.current_bet += to_put
                pot += to_put
                current_bet = player.current_bet
                raises_made += 1
                self._log(f"{player.name:<12} raises to {current_bet}")
                self._append_chat(hand_chat, f"{player.name} raises to {current_bet}.")
                self._render_table()

                action_queue = [p for p in ordered_players if not p.folded and p is not player]
                continue

            player.folded = True
            self._log(f"{player.name:<12} folds (invalid action)")
            self._append_chat(hand_chat, f"{player.name} folds after a bad read.")
            self._render_table()

        return pot

    def _append_chat(self, hand_chat: list[str], entry: str) -> None:
        hand_chat.append(entry)
        if len(hand_chat) > self.MAX_CHAT_HISTORY:
            del hand_chat[:-self.MAX_CHAT_HISTORY]
        if self.table_ui and ":" in entry:
            speaker, message = entry.split(":", 1)
            self.table_ui.set_speech(speaker.strip(), message.strip())
            self._render_table()
        self._broadcast_event(entry)

    def _broadcast_event(self, event: str) -> None:
        for player in self.players:
            player.agent.observe_event(event)

    def _finalize_hand_memory(
        self,
        ordered_players: list[PlayerState],
        hand_start_stacks: dict[str, int],
        winner_names: set[str],
    ) -> None:
        for player in ordered_players:
            start_stack = hand_start_stacks.get(player.name, player.stack)
            delta = player.stack - start_stack
            player.agent.end_hand(chip_delta=delta, won=player.name in winner_names)

    def _table_talk_phase(
        self,
        ordered_players: list[PlayerState],
        street: str,
        community_cards: list[Card],
        pot: int,
        hand_chat: list[str],
    ) -> None:
        if not self.enable_table_talk:
            return

        active = [p for p in ordered_players if not p.folded]
        if not active:
            return

        self._log(f"Table talk ({street}):")
        for player in active:
            ctx = DecisionContext(
                hand_strength=self._estimate_strength(player.hole_cards, community_cards),
                to_call=0,
                current_bet=0,
                pot=pot,
                min_raise=self.big_blind,
                stack=player.stack,
                street=street,
                community_count=len(community_cards),
                player_name=player.name,
                recent_chat=hand_chat[-8:],
            )
            message = player.agent.speak(ctx, self.rng).strip()
            if not message:
                continue
            line = f"{player.name}: {message}"
            self._log(f"  {line}")
            self._append_chat(hand_chat, line)

    def _showdown(
        self, ordered_players: list[PlayerState], community_cards: list[Card], pot: int
    ) -> set[str]:
        contenders = [p for p in ordered_players if not p.folded]
        if len(contenders) == 1:
            winner = contenders[0]
            winner.stack += pot
            self._log(f"Winner by fold: {winner.name} wins {pot}")
            self._broadcast_event(f"Showdown winner: {winner.name}")
            return {winner.name}

        scored: list[tuple[PlayerState, tuple[int, tuple[int, ...]]]] = []
        for p in contenders:
            score = evaluate_best_hand(p.hole_cards + community_cards)
            scored.append((p, score))

        best_score = max(score for _, score in scored)
        winners = [p for p, score in scored if score == best_score]

        share = pot // len(winners)
        remainder = pot % len(winners)
        for idx, winner in enumerate(winners):
            winner.stack += share + (1 if idx < remainder else 0)

        self._log(f"Board: {cards_to_text(community_cards)}")
        for p, score in scored:
            self._log(f"{p.name:<12} hole: {cards_to_text(p.hole_cards):<8} best={score}")

        self._render_table()

        if len(winners) == 1:
            self._log(f"Showdown winner: {winners[0].name} wins {pot}")
            self._broadcast_event(f"Showdown winner: {winners[0].name}")
        else:
            names = ", ".join(w.name for w in winners)
            self._log(f"Split pot ({pot}) among: {names}")
            self._broadcast_event(f"Split pot winners: {names}")

        if self.dealer_agent:
            line = self.dealer_agent.comment_showdown(
                winner_names={w.name for w in winners},
                pot=pot,
                board_text=cards_to_text(community_cards),
            )
            self._dealer_say(line)

        return {w.name for w in winners}

    def play_round(self) -> None:
        self.round_number += 1
        self._log(f"\n--- Hand {self.round_number} ---")
        self._current_street = "preflop"
        self._community_cards = []
        self._pot = 0
        if self.table_ui:
            self.table_ui.clear_speech()
        self._dealer_line = "Shuffling up and dealing."

        ordered_players: list[PlayerState] = []
        total = len(self.players)
        for offset in range(total):
            idx = (self.dealer_idx + offset) % total
            p = self.players[idx]
            p.folded = p.stack <= 0
            p.current_bet = 0
            p.hole_cards = []
            ordered_players.append(p)

        hand_start_stacks = {p.name: p.stack for p in ordered_players}
        for p in ordered_players:
            opponents = [o.name for o in ordered_players if o.name != p.name]
            p.agent.start_hand(self.round_number, p.stack, opponents)

        alive = [p for p in ordered_players if p.stack > 0]
        if len(alive) <= 1:
            return

        deck = shuffled_deck(self.rng)
        for p in ordered_players:
            if not p.folded:
                p.hole_cards = deal_hand(deck, hand_size=2)

        pot = 0
        community_cards: list[Card] = []
        hand_chat: list[str] = []
        self._community_cards = community_cards
        self._pot = pot
        self._render_table()
        self._step_wait("Preflop setup")

        self._table_talk_phase(ordered_players, "preflop", community_cards, pot, hand_chat)
        pot = self._betting_round(ordered_players, pot, "preflop", community_cards, hand_chat)
        self._pot = pot
        self._render_table()
        self._step_wait("Preflop complete")
        if len([p for p in ordered_players if not p.folded]) <= 1:
            winner_names = self._showdown(ordered_players, community_cards, pot)
            self._finalize_hand_memory(ordered_players, hand_start_stacks, winner_names)
            self.dealer_idx = (self.dealer_idx + 1) % len(self.players)
            return

        # Burn one, reveal flop.
        _ = deal_one(deck)
        community_cards.extend(deal_hand(deck, hand_size=3))
        self._current_street = "flop"
        self._community_cards = community_cards
        self._log(f"Flop: {cards_to_text(community_cards)}")
        if self.dealer_agent:
            self._dealer_say(
                self.dealer_agent.comment_street(
                    street="flop",
                    pot=pot,
                    board_text=cards_to_text(community_cards),
                    active_players=len([p for p in ordered_players if not p.folded]),
                )
            )
        self._render_table()
        self._step_wait("Flop revealed")
        self._table_talk_phase(ordered_players, "flop", community_cards, pot, hand_chat)
        pot = self._betting_round(ordered_players, pot, "flop", community_cards, hand_chat)
        self._pot = pot
        self._render_table()
        self._step_wait("Flop action complete")
        if len([p for p in ordered_players if not p.folded]) <= 1:
            winner_names = self._showdown(ordered_players, community_cards, pot)
            self._finalize_hand_memory(ordered_players, hand_start_stacks, winner_names)
            self.dealer_idx = (self.dealer_idx + 1) % len(self.players)
            return

        # Burn one, reveal turn.
        _ = deal_one(deck)
        community_cards.append(deal_one(deck))
        self._current_street = "turn"
        self._community_cards = community_cards
        self._log(f"Turn: {cards_to_text(community_cards)}")
        if self.dealer_agent:
            self._dealer_say(
                self.dealer_agent.comment_street(
                    street="turn",
                    pot=pot,
                    board_text=cards_to_text(community_cards),
                    active_players=len([p for p in ordered_players if not p.folded]),
                )
            )
        self._render_table()
        self._step_wait("Turn revealed")
        self._table_talk_phase(ordered_players, "turn", community_cards, pot, hand_chat)
        pot = self._betting_round(ordered_players, pot, "turn", community_cards, hand_chat)
        self._pot = pot
        self._render_table()
        self._step_wait("Turn action complete")
        if len([p for p in ordered_players if not p.folded]) <= 1:
            winner_names = self._showdown(ordered_players, community_cards, pot)
            self._finalize_hand_memory(ordered_players, hand_start_stacks, winner_names)
            self.dealer_idx = (self.dealer_idx + 1) % len(self.players)
            return

        # Burn one, reveal river.
        _ = deal_one(deck)
        community_cards.append(deal_one(deck))
        self._current_street = "river"
        self._community_cards = community_cards
        self._log(f"River: {cards_to_text(community_cards)}")
        if self.dealer_agent:
            self._dealer_say(
                self.dealer_agent.comment_street(
                    street="river",
                    pot=pot,
                    board_text=cards_to_text(community_cards),
                    active_players=len([p for p in ordered_players if not p.folded]),
                )
            )
        self._render_table()
        self._step_wait("River revealed")
        self._table_talk_phase(ordered_players, "river", community_cards, pot, hand_chat)
        pot = self._betting_round(ordered_players, pot, "river", community_cards, hand_chat)
        self._pot = pot
        self._render_table()
        self._step_wait("River action complete")

        winner_names = self._showdown(ordered_players, community_cards, pot)
        self._finalize_hand_memory(ordered_players, hand_start_stacks, winner_names)

        self.dealer_idx = (self.dealer_idx + 1) % len(self.players)
        stacks = ", ".join(f"{p.name}:{p.stack}" for p in self.players)
        self._log(f"Stacks: {stacks}")
        self._render_table()
        self._step_wait("Hand complete")

    def play_tournament(self, rounds: int = 25) -> list[tuple[str, int]]:
        completed = 0
        for _ in range(rounds):
            alive = [p for p in self.players if p.stack > 0]
            if len(alive) <= 1:
                break
            self.play_round()
            completed += 1
            if self.output_mode == "replay":
                self._print_progress_bar(completed, rounds)

        if self.output_mode == "replay" and completed > 0:
            print()

        return sorted(((p.name, p.stack) for p in self.players), key=lambda x: x[1], reverse=True)
