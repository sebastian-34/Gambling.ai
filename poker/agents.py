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
            if "raises" in low:
                stats["raises"] += 1
            if "calls" in low:
                stats["calls"] += 1
            if "fold" in low:
                stats["folds"] += 1
            if ":" in event:
                stats["chat"] += 1

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
        return (
            f"Personal context: bankroll_trend={trend_desc}; dialogue_signal={dialogue_desc}; "
            f"opponent_reads={opponents}; recent_results={recency}."
        )

    def _build_prompt(self, ctx: DecisionContext) -> str:
        chat_context = " | ".join(ctx.recent_chat[-5:]) if ctx.recent_chat else "none"
        personal_context = self._build_personal_context()
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
            "Rules: if to_call is 0 then choose check or raise. "
            "If to_call > 0 then choose fold/call/raise. "
            "raise_amount is the extra amount above current bet, not total bet."
        )

    def _build_talk_prompt(self, ctx: DecisionContext) -> str:
        chat_context = " | ".join(ctx.recent_chat[-6:]) if ctx.recent_chat else "none"
        personal_context = self._build_personal_context()
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
        seed = int(hashlib.sha256(self.profile.name.encode("utf-8")).hexdigest()[:8], 16)
        model_rng = random.Random(seed + ctx.pot + ctx.to_call + len(ctx.recent_chat) * 7)

        # Agents can stay silent based on pressure and tendency.
        talk_bias = 0.45 + model_rng.random() * 0.25
        if ctx.to_call > 0:
            talk_bias -= 0.08
        if ctx.hand_strength > 0.75:
            talk_bias += 0.07
        if rng.random() > max(0.2, min(0.9, talk_bias)):
            return ""

        last_line = ""
        for line in reversed(ctx.recent_chat):
            if ":" in line:
                speaker, content = line.split(":", 1)
                if speaker.strip() != ctx.player_name:
                    last_line = content.strip()
                    break

        if ctx.hand_strength > 0.8:
            stance = "confident"
        elif ctx.hand_strength < 0.35:
            stance = "deflecting"
        else:
            stance = "balanced"

        if last_line:
            response_starts = [
                "Interesting read.",
                "Maybe.",
                "Could be.",
                "I hear you.",
            ]
            opener = response_starts[model_rng.randint(0, len(response_starts) - 1)]
        else:
            opener = ""

        if stance == "confident":
            core = "This texture favors pressure, not hesitation."
        elif stance == "deflecting":
            core = "I'm just navigating ranges and timing here."
        else:
            if ctx.to_call > 0:
                core = "Pot odds and tempo matter more than noise."
            else:
                core = "Let's see who tells the cleaner story by river."

        message = f"{opener} {core}".strip()
        message = " ".join(message.split())

        words = message.split()
        if len(words) > 16:
            message = " ".join(words[:16])
        return message


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
