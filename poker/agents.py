from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections import defaultdict
import hashlib
import json
import os
import random
from typing import Any

from .tools import (
    estimate_equity,
    calculate_pot_odds,
    OpponentProfiler,
    RangeTracker,
    recommend_bet_size,
    plan_bluff,
    HandMemory,
    plan_table_talk,
    LeakDetector,
)
from .dialogue import PokerDialogueGenerator, DialogueContext

try:
    from agent_framework import Agent as AFAgent
    from agent_framework.ollama import OllamaChatClient
except ImportError:
    AFAgent = None
    OllamaChatClient = None


@dataclass
class Decision:
    action: str  # fold, call, check, raise
    raise_amount: int = 0


@dataclass
class DecisionContext:
    hand_strength: float
    to_call: int
    current_bet: int
    pot: int
    min_raise: int
    stack: int
    street: str
    community_count: int
    player_name: str
    recent_chat: list[str]


@dataclass
class LLMProfile:
    name: str
    provider: str
    model: str
    host: str = ""
    timeout_seconds: float = 4.0
    temperature: float = 0.3


class PokerAgent(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def decide(self, ctx: DecisionContext, rng: random.Random) -> Decision:
        raise NotImplementedError

    def speak(self, ctx: DecisionContext, rng: random.Random) -> str:
        return ""

    def start_hand(self, hand_number: int, stack: int, opponents: list[str]) -> None:
        return None

    def observe_event(self, event: str) -> None:
        return None

    def end_hand(self, chip_delta: int, won: bool) -> None:
        return None


class LLMPokerAgent(PokerAgent):
    def __init__(self, profile: LLMProfile) -> None:
        super().__init__(profile.name)
        self.profile = profile
        self._decision_agent: Any | None = None
        self._talk_agent: Any | None = None
        self.hand_number = 0
        self._stack_at_hand_start = 0
        self._recent_observations: list[str] = []
        self._hand_journal: list[str] = []
        self._known_players: list[str] = [self.name]
        self._dialogue_impact = 0.0
        self._chip_trend = 0.0
        self._last_spoken_event_index: int | None = None
        self._opponent_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"raises": 0, "calls": 0, "folds": 0, "chat": 0}
        )
        
        # Tool instances
        self._opponent_profiler = OpponentProfiler()
        self._range_tracker = RangeTracker()
        self._hand_memory = HandMemory(max_memory=100)
        self._leak_detector = LeakDetector()

    def start_hand(self, hand_number: int, stack: int, opponents: list[str]) -> None:
        self.hand_number = hand_number
        self._stack_at_hand_start = stack
        self._last_spoken_event_index = None
        self._known_players = [self.name, *opponents]
        for opponent in opponents:
            _ = self._opponent_stats[opponent]

    def _detect_actor(self, event: str) -> str:
        for candidate in sorted(self._known_players, key=len, reverse=True):
            if event.startswith(candidate):
                return candidate
        return ""

    def observe_event(self, event: str) -> None:
        self._recent_observations.append(event)
        if len(self._recent_observations) > 40:
            del self._recent_observations[:-40]

        actor = self._detect_actor(event)
        if actor and actor != self.name and actor in self._opponent_stats:
            stats = self._opponent_stats[actor]
            low = event.lower()
            
            # Track in opponent profiler (Tool 4)
            if "raises" in low:
                stats["raises"] += 1
                self._opponent_profiler.record_action(actor, "raise", is_pressure=False)
            if "calls" in low:
                stats["calls"] += 1
                self._opponent_profiler.record_action(actor, "call", is_pressure=False)
            if "fold" in low:
                stats["folds"] += 1
                is_pressure = "pressure" in low or "facing" in low
                self._opponent_profiler.record_action(actor, "fold", is_pressure=is_pressure)
            if ":" in event:
                stats["chat"] += 1
            
            # Update range tracker (Tool 5)
            street = "unknown"
            if "flop" in low:
                street = "flop"
            elif "turn" in low:
                street = "turn"
            elif "river" in low:
                street = "river"
            if street != "unknown":
                action_type = "raise" if "raises" in low else "call" if "calls" in low else "fold"
                self._range_tracker.update_range_after_action(actor, street, action_type, [])

        # Crude causal signal: if others fold shortly after our talk, dialogue efficacy increases.
        if self._last_spoken_event_index is not None:
            if len(self._recent_observations) - self._last_spoken_event_index <= 6:
                low = event.lower()
                if "fold" in low and actor and actor != self.name:
                    self._dialogue_impact = 0.85 * self._dialogue_impact + 0.15 * 1.0
                    self._last_spoken_event_index = None
                elif ("calls" in low or "raises" in low) and actor and actor != self.name:
                    self._dialogue_impact = 0.9 * self._dialogue_impact - 0.1 * 0.4
                    self._last_spoken_event_index = None

    def end_hand(self, chip_delta: int, won: bool) -> None:
        self._chip_trend = 0.85 * self._chip_trend + 0.15 * chip_delta
        outcome = "won" if won else "lost"
        note = (
            f"Hand {self.hand_number}: {outcome} {chip_delta:+} chips; "
            f"dialogue_impact={self._dialogue_impact:+.2f}; trend={self._chip_trend:+.2f}"
        )
        self._hand_journal.append(note)
        if len(self._hand_journal) > 18:
            del self._hand_journal[:-18]
        
        # Tool 10: Record hand in memory for future reference
        self._hand_memory.record_hand(
            hand_number=self.hand_number,
            street="river",  # Simplified: assume hand went to river
            action="fold" if not won else "call",
            board_type="dry" if chip_delta < 0 else "wet",
            result=outcome,
            equity=0.5,  # Placeholder
        )
        
        # Tool 12: Record for leak detection
        action_type = "fold" if chip_delta < -5 else "raise" if chip_delta > 10 else "call"
        self._leak_detector.record_hand_action(
            street="river",
            action=action_type,
            hand_strength=0.5,
            is_fold=chip_delta < 0,
        )

    def decide(self, ctx: DecisionContext, rng: random.Random) -> Decision:
        prompt = self._build_prompt(ctx)
        response_text = self._call_llm(prompt)
        if response_text is not None:
            parsed = self._parse_decision(response_text, ctx)
            if parsed is not None:
                return parsed

        # Fallback keeps game running even if a model is unreachable.
        return self._fallback_decision(ctx, rng)

    def speak(self, ctx: DecisionContext, rng: random.Random) -> str:
        prompt = self._build_talk_prompt(ctx)
        response_text = self._call_llm_chat(prompt)
        if response_text:
            message = self._parse_chat_message(response_text)
            if message:
                self._last_spoken_event_index = len(self._recent_observations)
                return message
        fallback = self._fallback_chat(ctx, rng)
        if fallback:
            self._last_spoken_event_index = len(self._recent_observations)
        return fallback

    def _build_personal_context(self) -> str:
        top_opponents = []
        for name, stats in self._opponent_stats.items():
            activity = stats["raises"] + stats["calls"] + stats["folds"]
            if activity == 0:
                continue
            tendency = "balanced"
            if stats["raises"] > stats["calls"] + stats["folds"]:
                tendency = "pressure-heavy"
            elif stats["folds"] > stats["raises"]:
                tendency = "cautious under pressure"
            top_opponents.append(f"{name}={tendency}")

        trend_desc = "up" if self._chip_trend > 5 else "down" if self._chip_trend < -5 else "flat"
        dialogue_desc = (
            "effective"
            if self._dialogue_impact > 0.2
            else "ineffective"
            if self._dialogue_impact < -0.2
            else "uncertain"
        )

        recency = " | ".join(self._hand_journal[-3:]) if self._hand_journal else "none"
        opponents = ", ".join(top_opponents[:3]) if top_opponents else "none"
        
        # Tool 12: Leak detection alerts
        leaks = self._leak_detector.detect_leaks()
        leak_alerts = ""
        if leaks:
            leak_summary = "; ".join([f"{leak.leak_type}({leak.severity})" for leak in leaks[:2]])
            leak_alerts = f"Active Leaks: {leak_summary}. "
        
        # Tool 10: Memory insights
        memory_insights = ""
        similar_hands = self._hand_memory.find_similar_hands(street="river", board_type="unknown", equity=0.5, top_n=1)
        if similar_hands:
            hand = similar_hands[0]
            memory_insights = f"Similar recent hand: {hand.my_action} → {hand.result}. "
        
        return (
            f"Personal context: bankroll_trend={trend_desc}; dialogue_signal={dialogue_desc}; "
            f"opponent_reads={opponents}; recent_results={recency}. "
            f"{leak_alerts}{memory_insights}"
        )

    def _build_prompt(self, ctx: DecisionContext) -> str:
        chat_context = " | ".join(ctx.recent_chat[-5:]) if ctx.recent_chat else "none"
        personal_context = self._build_personal_context()
        
        # Tool 1 & 2: Equity and Pot-Odds Analysis
        equity_result = estimate_equity([14, 13], [], num_opponents=4, rng=random.Random())
        pot_odds = calculate_pot_odds(ctx.to_call, ctx.pot, equity_result.win_equity)
        equity_context = (
            f"Equity Analysis: hand_equity={equity_result.win_equity:.1%}; "
            f"break_even={pot_odds.break_even_equity:.1%}; "
            f"pot_odds_recommendation={pot_odds.ev_recommendation}. "
        )
        
        # Tool 4: Opponent Profile
        opp_profiles_summary = ""
        for opponent in self._known_players:
            if opponent == self.name:
                continue
            profile = self._opponent_profiler.get_profile(opponent)
            opp_profiles_summary += f"{opponent}={profile.profile_type},{profile.aggression_type}; "
        
        # Tool 6: Bet Size Recommendation
        objective = "value" if ctx.hand_strength > 0.65 else "bluff" if ctx.hand_strength < 0.35 else "protection"
        bet_rec = recommend_bet_size(
            ctx.pot, ctx.stack, ctx.min_raise, objective,
            board_texture="wet" if ctx.community_count >= 3 else "dry",
            equity=ctx.hand_strength
        )
        sizing_context = f"Sizing_recommendation={bet_rec.recommended_size}chips ({bet_rec.recommendation_reason}). "
        
        # Tool 7: Bluff Planning
        bluff_plan = plan_bluff(
            equity=ctx.hand_strength,
            pot=ctx.pot,
            bet_size=bet_rec.recommended_size,
            opponent_fold_to_pressure=0.5,
            has_blockers=ctx.hand_strength < 0.4,
        )
        bluff_context = f"Bluff_plan={bluff_plan.plan_summary} (fold_equity={bluff_plan.fold_equity:.1%}). "
        
        return (
            "You are deciding a single Texas Hold'em action for one betting turn. "
            "Respond with JSON only in this exact schema: "
            '{"action":"fold|call|check|raise","raise_amount":number}. '\
            "Do not add explanation. "
            f"You are {ctx.player_name}. "
            f"Street={ctx.street}; hand_strength={ctx.hand_strength:.3f}; "
            f"to_call={ctx.to_call}; current_bet={ctx.current_bet}; pot={ctx.pot}; "
            f"min_raise={ctx.min_raise}; stack={ctx.stack}; community_count={ctx.community_count}. "
            f"Recent table talk={chat_context}. "
            f"{personal_context} "
            f"Tool Analysis: {equity_context}{sizing_context}{bluff_context}"
            f"Opponent Reads: {opp_profiles_summary or 'none yet'}. "
            "Rules: if to_call is 0 then choose check or raise. "
            "If to_call > 0 then choose fold/call/raise. "
            "raise_amount is the extra amount above current bet, not total bet."
        )

    def _build_talk_prompt(self, ctx: DecisionContext) -> str:
        chat_context = " | ".join(ctx.recent_chat[-6:]) if ctx.recent_chat else "none"
        personal_context = self._build_personal_context()
        
        # Tool 11: Table-Talk Strategy
        talk_strategy = plan_table_talk(
            recent_chat=ctx.recent_chat,
            hand_strength=ctx.hand_strength,
            to_call=ctx.to_call,
            stack=ctx.stack,
            opponent_profiles={
                name: self._opponent_profiler.get_profile(name)
                for name in self._known_players if name != self.name
            },
            player_name=self.name,
        )
        
        talk_guidance = (
            f"Talk_Strategy: should_speak={talk_strategy.should_speak}; "
            f"tone={talk_strategy.tone}; purpose={talk_strategy.strategic_purpose}; "
            f"suggestion='{talk_strategy.suggested_message}'. "
        )
        
        return (
            "You are roleplaying table talk in a Texas Hold'em hand. "
            "Reply with JSON only using this schema: "
            '{"speak":true|false,"message":"text"}. '
            "If you choose not to talk, set speak=false and message to an empty string. "
            "Keep message under 16 words. No profanity, slurs, threats, or explicit content. "
            f"You are {ctx.player_name}. Street={ctx.street}; pot={ctx.pot}; "
            f"to_call={ctx.to_call}; hand_strength={ctx.hand_strength:.3f}; stack={ctx.stack}. "
            f"Recent table talk={chat_context}. "
            f"{personal_context} "
            f"{talk_guidance} "
            "If talking, interpret opponents' latest lines and respond strategically using confidence, "
            "misdirection, pressure, or calm control."
        )

    def _call_llm(self, prompt: str) -> str | None:
        self._ensure_framework_agents()
        return self._run_agent_prompt(self._decision_agent, prompt)

    def _call_llm_chat(self, prompt: str) -> str | None:
        self._ensure_framework_agents()
        return self._run_agent_prompt(self._talk_agent, prompt)

    def _ensure_framework_agents(self) -> None:
        if self._decision_agent is None:
            self._decision_agent = self._create_framework_agent(kind="decision")
        if self._talk_agent is None:
            self._talk_agent = self._create_framework_agent(kind="talk")

    def _create_framework_agent(self, kind: str) -> Any | None:
        if AFAgent is None:
            return None

        try:
            if self.profile.provider == "agent-framework-ollama":
                if OllamaChatClient is None:
                    return None
                host = self.profile.host or None
                client = OllamaChatClient(model=self.profile.model, host=host)
            else:
                return None

            instructions = (
                "You are a poker action policy model that replies with strict JSON only."
                if kind == "decision"
                else "You are a poker table-talk model that replies with strict JSON only."
            )
            return AFAgent(client=client, instructions=instructions, name=f"{self.name}-{kind}")
        except Exception:
            return None

    def _run_agent_prompt(self, agent: Any | None, prompt: str) -> str | None:
        if agent is None:
            return None

        async def _invoke() -> str | None:
            result = await asyncio.wait_for(
                agent.run(prompt),
                timeout=self.profile.timeout_seconds,
            )
            text = getattr(result, "text", None)
            if isinstance(text, str):
                return text
            content = getattr(result, "content", None)
            if isinstance(content, str):
                return content
            return None

        try:
            return asyncio.run(_invoke())
        except RuntimeError:
            return None
        except Exception:
            return None

    def _parse_decision(self, text: str, ctx: DecisionContext) -> Decision | None:
        try:
            parsed: Any = json.loads(text)
        except ValueError:
            return None

        action = str(parsed.get("action", "")).strip().lower()
        if action not in {"fold", "call", "check", "raise"}:
            return None

        if ctx.to_call == 0 and action == "call":
            action = "check"
        if ctx.to_call > 0 and action == "check":
            action = "call"

        try:
            raise_amount = int(parsed.get("raise_amount", 0))
        except (TypeError, ValueError):
            raise_amount = 0

        if action == "raise":
            raise_amount = max(ctx.min_raise, raise_amount)
        else:
            raise_amount = 0

        return Decision(action=action, raise_amount=raise_amount)

    def _parse_chat_message(self, text: str) -> str | None:
        try:
            parsed: Any = json.loads(text)
        except ValueError:
            return None

        speak = parsed.get("speak", True)
        if isinstance(speak, bool) and not speak:
            return ""

        message = str(parsed.get("message", "")).strip()
        if not message:
            return ""

        # Keep logs compact and avoid multi-line output.
        message = " ".join(message.split())
        return message[:120]

    def _fallback_decision(self, ctx: DecisionContext, rng: random.Random) -> Decision:
        # Stable bias per model name makes each fallback policy distinct.
        seed = int(hashlib.sha256(self.profile.name.encode("utf-8")).hexdigest()[:8], 16)
        model_rng = random.Random(seed + int(ctx.hand_strength * 1000) + ctx.to_call + ctx.pot)

        aggressiveness = 0.25 + model_rng.random() * 0.45
        bluff_rate = 0.05 + model_rng.random() * 0.2

        if ctx.to_call == 0:
            if ctx.stack > ctx.min_raise and (
                ctx.hand_strength > (0.65 - aggressiveness * 0.25) or rng.random() < bluff_rate
            ):
                size = max(ctx.min_raise, int(ctx.min_raise + 30 * aggressiveness))
                return Decision("raise", size)
            return Decision("check")

        pressure = ctx.to_call / max(1, ctx.stack)
        fold_threshold = 0.28 - aggressiveness * 0.12 + pressure * 0.3
        raise_threshold = 0.72 - aggressiveness * 0.2

        if ctx.hand_strength < fold_threshold:
            return Decision("fold")

        if ctx.stack > ctx.to_call + ctx.min_raise and (
            ctx.hand_strength > raise_threshold or rng.random() < bluff_rate * 0.6
        ):
            size = max(ctx.min_raise, int(ctx.min_raise + 25 + 20 * aggressiveness))
            return Decision("raise", size)

        return Decision("call")

    def _fallback_chat(self, ctx: DecisionContext, rng: random.Random) -> str:
        """Generate diverse, realistic poker table talk using the enhanced dialogue system."""
        
        # Sometimes stay silent based on pressure and personality
        talk_bias = 0.45 + rng.random() * 0.25
        if ctx.to_call > 0:
            talk_bias -= 0.08
        if ctx.hand_strength > 0.75:
            talk_bias += 0.07
        
        if rng.random() > max(0.2, min(0.9, talk_bias)):
            return ""
        
        # Map game state to dialogue context
        position_map = {
            0: "button",
            1: "sb",
            2: "bb",
            3: "utg",
            4: "co",
        }
        
        # Estimate bet size ratio for dialogue context
        bet_size_ratio = (ctx.current_bet / ctx.pot) if ctx.pot > 0 else 0.5
        
        # Default position to cutoff if seat_index not available
        position = "co"
        
        dialogue_ctx = DialogueContext(
            hand_strength=ctx.hand_strength,
            to_call=ctx.to_call,
            pot=ctx.pot,
            stack=ctx.stack,
            street=ctx.street,
            position=position,
            opponent_count=max(1, 5 - ctx.community_count),  # Rough estimate
            is_aggressor=False,  # Don't have this info in DecisionContext
            just_raised=ctx.current_bet > 0,
            bet_size_ratio=bet_size_ratio,
        )
        
        # Generate dialogue using the new system
        dialogue = PokerDialogueGenerator.generate_dialogue(dialogue_ctx, seed=rng.randint(0, 10000))
        
        return dialogue


class DealerAgent:
    """Non-playing dealer that validates legality and provides commentary."""

    def __init__(self, name: str = "Dealer", model: str = "qwen2.5:7b", host: str = "http://127.0.0.1:11434") -> None:
        self.name = name
        self.model = model
        self.host = host
        self._agent: Any | None = None

    def validate_decision(
        self,
        decision: Decision,
        ctx: DecisionContext,
        raises_made: int,
        max_raises: int,
    ) -> tuple[Decision, str | None]:
        action = decision.action
        raise_amount = decision.raise_amount

        if action not in {"fold", "call", "check", "raise"}:
            return Decision(action="fold", raise_amount=0), self._line("Invalid action declared. Hand ruled as fold.")

        if ctx.to_call == 0 and action == "call":
            return Decision(action="check", raise_amount=0), self._line("Call is not legal with nothing to call. Converted to check.")

        if ctx.to_call > 0 and action == "check":
            return Decision(action="call", raise_amount=0), self._line("Check is not legal facing a bet. Converted to call.")

        if action == "raise" and raises_made >= max_raises:
            fallback = "call" if ctx.to_call > 0 else "check"
            return Decision(action=fallback, raise_amount=0), self._line("Raise cap reached. Action reduced.")

        if action == "raise" and raise_amount < ctx.min_raise:
            return Decision(action="raise", raise_amount=ctx.min_raise), self._line(
                f"Minimum raise enforced at {ctx.min_raise}."
            )

        if action != "raise":
            raise_amount = 0

        return Decision(action=action, raise_amount=raise_amount), None

    def comment_street(self, street: str, pot: int, board_text: str, active_players: int) -> str:
        prompt = (
            "You are a professional poker dealer and commentator. "
            "Respond with one short line under 20 words. "
            f"Street={street}; pot={pot}; board={board_text or 'none'}; active_players={active_players}."
        )
        generated = self._call_model(prompt)
        if generated:
            return generated

        fallback = {
            "flop": "Flop is out. Board texture now starts telling the story.",
            "turn": "Turn card dealt. Pressure rises as ranges narrow.",
            "river": "River is out. Final decisions before showdown.",
        }
        return fallback.get(street.lower(), "Action remains live. Dealer watching every move.")

    def comment_showdown(self, winner_names: set[str], pot: int, board_text: str) -> str:
        names = ", ".join(sorted(winner_names))
        prompt = (
            "You are a professional poker dealer. "
            "Respond with one concise closing line under 20 words. "
            f"Winners={names}; pot={pot}; board={board_text}."
        )
        generated = self._call_model(prompt)
        if generated:
            return generated
        if len(winner_names) == 1:
            return f"Pot of {pot} pushed to {names}."
        return f"Split pot awarded to {names}."

    def _ensure_agent(self) -> None:
        if self._agent is not None:
            return
        if AFAgent is None or OllamaChatClient is None:
            return
        try:
            client = OllamaChatClient(model=self.model, host=self.host)
            self._agent = AFAgent(
                client=client,
                instructions="You are a poker dealer. Keep responses short, neutral, and clean.",
                name=self.name,
            )
        except Exception:
            self._agent = None

    def _call_model(self, prompt: str) -> str | None:
        self._ensure_agent()
        if self._agent is None:
            return None

        async def _invoke() -> str | None:
            result = await asyncio.wait_for(self._agent.run(prompt), timeout=3.0)
            text = getattr(result, "text", None)
            if isinstance(text, str):
                compact = " ".join(text.split())
                return compact[:120]
            return None

        try:
            return asyncio.run(_invoke())
        except Exception:
            return None

    def _line(self, text: str) -> str:
        return text[:120]


def build_default_agents() -> list[PokerAgent]:
    """Build five poker agents backed by five different LLM profiles.

    Default setup:
    - Five local Ollama models through Microsoft Agent Framework.

    Unavailable local endpoints or models automatically trigger fallback policy.
    """
    profiles = [
        LLMProfile(
            name="Llama Agent",
            provider="agent-framework-ollama",
            model="llama3.1:8b",
            host="http://127.0.0.1:11434",
        ),
        LLMProfile(
            name="Mistral Agent",
            provider="agent-framework-ollama",
            model="mistral:7b",
            host="http://127.0.0.1:11434",
        ),
        LLMProfile(
            name="Qwen Agent",
            provider="agent-framework-ollama",
            model="qwen2.5:7b",
            host="http://127.0.0.1:11434",
        ),
        LLMProfile(
            name="Gemma Agent",
            provider="agent-framework-ollama",
            model="gemma2:9b",
            host="http://127.0.0.1:11434",
        ),
        LLMProfile(
            name="Phi Agent",
            provider="agent-framework-ollama",
            model="phi3:mini",
            host="http://127.0.0.1:11434",
        ),
    ]

    return [LLMPokerAgent(profile) for profile in profiles]


def build_default_dealer_agent() -> DealerAgent:
    return DealerAgent(name="Dealer", model="qwen2.5:7b", host="http://127.0.0.1:11434")
