"""Poker decision support tools for LLM agents."""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Any
import random
from itertools import combinations

# ============================================================================
# Tool 1: Odds and Equity Estimator
# ============================================================================

@dataclass
class EquityResult:
    win_prob: float
    tie_prob: float
    loss_prob: float
    win_equity: float  # % of pot I win on average


def estimate_equity(
    hole_cards: list[int],
    board_cards: list[int],
    num_opponents: int,
    num_simulations: int = 1000,
    rng: random.Random | None = None,
) -> EquityResult:
    """Estimate hand equity using Monte Carlo simulation.
    
    Args:
        hole_cards: Ranks of player's two hole cards (2-14, where 14=Ace)
        board_cards: Ranks of community cards on board (0-5 cards)
        num_opponents: Number of active opponents
        num_simulations: Monte Carlo samples
        rng: Random number generator
    
    Returns:
        EquityResult with win/tie/loss probabilities and equity share
    """
    if rng is None:
        rng = random.Random()
    
    if num_opponents < 1 or num_opponents > 6:
        return EquityResult(0.5, 0.0, 0.5, 0.5)
    
    wins = 0
    ties = 0
    
    for _ in range(num_simulations):
        # Rough simulation: assign random hand strength to opponents
        my_strength = sum(hole_cards) / 28.0 * 0.8  # Normalize roughly
        
        opponent_strengths = [
            rng.random() * 0.9 for _ in range(num_opponents)
        ]
        board_boost = min(len(board_cards) / 5.0, 0.4)
        my_strength = min(my_strength + board_boost, 0.99)
        
        max_opponent = max(opponent_strengths) if opponent_strengths else 0
        
        if my_strength > max_opponent:
            wins += 1
        elif my_strength == max_opponent:
            ties += 1
    
    total = num_simulations + num_opponents  # Rough tie accounting
    win_prob = wins / num_simulations
    tie_prob = ties / (num_simulations * max(1, num_opponents))
    loss_prob = 1.0 - win_prob - tie_prob
    win_equity = win_prob + (tie_prob / max(1, num_opponents + 1))
    
    return EquityResult(
        win_prob=win_prob,
        tie_prob=tie_prob,
        loss_prob=loss_prob,
        win_equity=win_equity,
    )


# ============================================================================
# Tool 2: Pot-Odds and Break-Even Calculator
# ============================================================================

@dataclass
class PotOddsResult:
    pot_odds: float  # ratio of call size to total pot after call
    break_even_equity: float  # equity % needed to call
    ev_if_call: float  # expected value of calling in chips
    ev_if_fold: float  # 0, by definition
    ev_recommendation: str  # "call", "fold", or "indifferent"


def calculate_pot_odds(
    to_call: int,
    pot: int,
    equity: float,
    expected_future_bet: int = 0,
) -> PotOddsResult:
    """Calculate pot odds and break-even equity.
    
    Args:
        to_call: Chips needed to call
        pot: Current pot size (before call)
        equity: Estimated equity % (0.0 to 1.0)
        expected_future_bet: Expected additional bets on future streets
    
    Returns:
        PotOddsResult with odds, break-even, and EV recommendation
    """
    if to_call == 0:
        return PotOddsResult(
            pot_odds=0.0,
            break_even_equity=0.0,
            ev_if_call=0.0,
            ev_if_fold=0.0,
            ev_recommendation="check",
        )
    
    total_pot_after_call = pot + to_call
    pot_odds = to_call / total_pot_after_call if total_pot_after_call > 0 else 0.5
    break_even_equity = pot_odds
    
    # EV calculation: equity share of pot minus call cost
    ev_if_call = (equity * total_pot_after_call) - to_call
    ev_if_fold = 0.0
    
    # Future bets reduce call EV slightly (rough adjustment)
    if expected_future_bet > 0:
        future_loss_prob = (1.0 - equity) * 0.5  # Assume 50% of losing hands face future bet
        ev_if_call -= future_loss_prob * expected_future_bet
    
    recommendation = "indifferent"
    if equity > break_even_equity + 0.05:
        recommendation = "call"
    elif equity < break_even_equity - 0.05:
        recommendation = "fold"
    
    return PotOddsResult(
        pot_odds=pot_odds,
        break_even_equity=break_even_equity,
        ev_if_call=ev_if_call,
        ev_if_fold=ev_if_fold,
        ev_recommendation=recommendation,
    )


# ============================================================================
# Tool 4: Opponent Profiler
# ============================================================================

@dataclass
class OpponentProfile:
    name: str
    vpip: float  # % hands entered voluntarily
    pfr: float  # % hands raised preflop
    aggression: float  # 0.0 to 1.0, higher = more aggressive
    fold_to_pressure: float  # 0.0 to 1.0, higher = folds more
    bluff_tendency: float  # estimated bluff frequency
    profile_type: str  # "tight", "loose", "balanced"
    aggression_type: str  # "passive", "balanced", "aggressive"


class OpponentProfiler:
    """Track and profile opponent tendencies."""
    
    def __init__(self):
        self.stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "hands_played": 0,
                "raises": 0,
                "calls": 0,
                "folds": 0,
                "folds_to_pressure": 0,
                "pressure_spots": 0,
                "showdown_hands": 0,
                "bluffs": 0,
                "chat_count": 0,
            }
        )
    
    def record_action(
        self,
        opponent_name: str,
        action: str,
        is_pressure: bool = False,
    ) -> None:
        """Record opponent action."""
        stats = self.stats[opponent_name]
        stats["hands_played"] += 1
        
        if action == "raise":
            stats["raises"] += 1
        elif action == "call":
            stats["calls"] += 1
        elif action == "fold":
            stats["folds"] += 1
            if is_pressure:
                stats["folds_to_pressure"] += 1
        
        if is_pressure:
            stats["pressure_spots"] += 1
    
    def record_bluff_attempt(self, opponent_name: str, succeeded: bool) -> None:
        """Record bluff outcome for opponent."""
        self.stats[opponent_name]["bluffs"] += 1
    
    def record_showdown(self, opponent_name: str, hand_strength: str) -> None:
        """Record opponent showdown hand type."""
        self.stats[opponent_name]["showdown_hands"] += 1
    
    def get_profile(self, opponent_name: str) -> OpponentProfile:
        """Generate opponent profile from stats."""
        stats = self.stats[opponent_name]
        hands = max(1, stats["hands_played"])
        
        vpip = stats["raises"] + stats["calls"] / hands
        pfr = stats["raises"] / hands
        
        fold_rate = stats["folds"] / hands
        aggression = (stats["raises"] / max(1, stats["raises"] + stats["calls"])) if hands > 0 else 0.5
        
        fold_to_pressure = (
            stats["folds_to_pressure"] / max(1, stats["pressure_spots"])
            if stats["pressure_spots"] > 0
            else 0.5
        )
        
        bluff_tendency = stats["bluffs"] / hands if hands > 0 else 0.1
        
        # Classify profile
        profile_type = "balanced"
        if vpip < 0.35:
            profile_type = "tight"
        elif vpip > 0.60:
            profile_type = "loose"
        
        aggression_type = "balanced"
        if aggression < 0.35:
            aggression_type = "passive"
        elif aggression > 0.65:
            aggression_type = "aggressive"
        
        return OpponentProfile(
            name=opponent_name,
            vpip=vpip,
            pfr=pfr,
            aggression=aggression,
            fold_to_pressure=fold_to_pressure,
            bluff_tendency=bluff_tendency,
            profile_type=profile_type,
            aggression_type=aggression_type,
        )


# ============================================================================
# Tool 5: Range Tracker
# ============================================================================

@dataclass
class RangeEntry:
    hand_description: str  # "AA", "AK", "87s", etc.
    confidence: float  # 0.0 to 1.0
    likelihood: float  # probability in estimated range


class RangeTracker:
    """Track estimated opponent hand ranges by action."""
    
    def __init__(self):
        self.ranges: dict[str, dict[str, list[RangeEntry]]] = defaultdict(
            lambda: defaultdict(list)
        )
    
    def update_range_after_action(
        self,
        opponent_name: str,
        street: str,
        action: str,
        board_cards: list[str],
    ) -> None:
        """Update opponent range estimate after action."""
        # Simplified: just track that we observed action on this street
        key = f"{street}_{action}"
        if not self.ranges[opponent_name][key]:
            self.ranges[opponent_name][key] = [
                RangeEntry("AK", 0.6, 0.1),
                RangeEntry("QQ", 0.5, 0.08),
                RangeEntry("JJ", 0.5, 0.08),
                RangeEntry("TT", 0.4, 0.06),
            ]
    
    def get_range_summary(
        self,
        opponent_name: str,
        street: str,
    ) -> str:
        """Get readable range summary for opponent."""
        range_data = self.ranges[opponent_name]
        if not range_data:
            return "Unknown range"
        
        actions_observed = list(range_data.keys())
        return f"{opponent_name} on {street}: observed {', '.join(actions_observed)}"


# ============================================================================
# Tool 6: Bet-Size Recommender
# ============================================================================

@dataclass
class BetSizeRecommendation:
    small_size: int
    medium_size: int
    large_size: int
    recommended_size: int
    recommendation_reason: str


def recommend_bet_size(
    pot: int,
    stack: int,
    min_raise: int,
    objective: str,  # "value", "bluff", "deny_equity", "protection"
    board_texture: str,  # "dry", "wet", "connected", "high_card"
    equity: float = 0.5,
) -> BetSizeRecommendation:
    """Recommend bet sizes based on objective.
    
    Args:
        pot: Current pot size
        stack: Remaining stack
        min_raise: Minimum raise amount
        objective: Betting goal
        board_texture: Type of board
        equity: Hand equity %
    
    Returns:
        BetSizeRecommendation with sizes and reasoning
    """
    # Calculate size options
    small_size = max(min_raise, pot // 3)
    medium_size = max(min_raise, pot // 2)
    large_size = max(min_raise, pot)
    
    recommended_size = medium_size
    reason = "standard bet"
    
    # Adjust by objective
    if objective == "value":
        recommended_size = medium_size
        reason = "value bet: medium build"
    elif objective == "bluff":
        recommended_size = large_size
        reason = "bluff: credible sizing"
    elif objective == "deny_equity":
        recommended_size = large_size
        reason = "denial: price out draws"
    elif objective == "protection":
        recommended_size = medium_size
        reason = "protection: charge draws"
    
    # Adjust by board
    if board_texture == "wet":
        recommended_size = min(recommended_size + 10, stack)
        reason += "; wet board: bigger"
    elif board_texture == "dry":
        recommended_size = max(small_size, recommended_size - 10)
        reason += "; dry board: can check"
    
    return BetSizeRecommendation(
        small_size=small_size,
        medium_size=medium_size,
        large_size=large_size,
        recommended_size=recommended_size,
        recommendation_reason=reason,
    )


# ============================================================================
# Tool 7: Bluff Planner
# ============================================================================

@dataclass
class BluffPlan:
    should_bluff: bool
    fold_equity: float  # estimated % opponent folds to bluff
    ev_of_bluff: float  # expected value
    confidence: float  # 0.0 to 1.0
    blocker_bonus: float  # +EV from removed cards
    plan_summary: str


def plan_bluff(
    equity: float,
    pot: int,
    bet_size: int,
    opponent_fold_to_pressure: float,
    has_blockers: bool = False,
    board_runout_bad: bool = False,
) -> BluffPlan:
    """Plan a bluff with EV and fold equity calculation.
    
    Args:
        equity: Hand equity against opponent
        pot: Current pot
        bet_size: Proposed bet size
        opponent_fold_to_pressure: Opponent's fold-to-pressure tendency
        has_blockers: Whether we have blocker cards
        board_runout_bad: Whether runout favors opponent
    
    Returns:
        BluffPlan with EV and reasoning
    """
    call_probability = 1.0 - opponent_fold_to_pressure
    fold_equity = opponent_fold_to_pressure
    
    # EV of bluff = fold_equity * pot - (1 - fold_equity) * bet_size + equity * (pot + bet_size)
    win_on_call = equity * (pot + bet_size)
    lose_on_call = (1.0 - equity) * (-bet_size)
    ev_if_called = win_on_call + lose_on_call
    
    ev_of_bluff = (fold_equity * pot) + (call_probability * ev_if_called)
    
    blocker_bonus = 0.1 if has_blockers else 0.0
    
    should_bluff = (
        ev_of_bluff > 0 
        and fold_equity > 0.30
        and not (board_runout_bad and equity < 0.3)
    )
    
    confidence = min(1.0, fold_equity + blocker_bonus)
    
    summary = "bluff" if should_bluff else "check/fold"
    if has_blockers:
        summary += " (strong blockers)"
    
    return BluffPlan(
        should_bluff=should_bluff,
        fold_equity=fold_equity,
        ev_of_bluff=ev_of_bluff,
        confidence=confidence,
        blocker_bonus=blocker_bonus,
        plan_summary=summary,
    )


# ============================================================================
# Tool 10: Memory Retrieval
# ============================================================================

@dataclass
class MemoryRecord:
    hand_number: int
    street: str
    my_action: str
    result: str  # "won", "lost"
    board_type: str  # "dry", "wet", "paired", etc.
    similarity_score: float


class HandMemory:
    """Store and retrieve similar past hands."""
    
    def __init__(self, max_memory: int = 100):
        self.max_memory = max_memory
        self.hands: list[dict[str, Any]] = []
    
    def record_hand(
        self,
        hand_number: int,
        street: str,
        action: str,
        board_type: str,
        result: str,
        equity: float,
    ) -> None:
        """Record a completed hand."""
        self.hands.append({
            "hand_number": hand_number,
            "street": street,
            "action": action,
            "board_type": board_type,
            "result": result,
            "equity": equity,
        })
        if len(self.hands) > self.max_memory:
            self.hands.pop(0)
    
    def find_similar_hands(
        self,
        street: str,
        board_type: str,
        equity: float,
        top_n: int = 3,
    ) -> list[MemoryRecord]:
        """Find similar past hands."""
        results = []
        
        for hand in self.hands:
            if hand["street"] != street:
                continue
            
            # Simple similarity: same board type, close equity
            equity_diff = abs(hand["equity"] - equity)
            if equity_diff > 0.3:
                continue
            
            similarity = 1.0 - equity_diff
            results.append(
                MemoryRecord(
                    hand_number=hand["hand_number"],
                    street=street,
                    my_action=hand["action"],
                    result=hand["result"],
                    board_type=board_type,
                    similarity_score=similarity,
                )
            )
        
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:top_n]


# ============================================================================
# Tool 11: Table-Talk Strategy
# ============================================================================

@dataclass
class TalkStrategy:
    should_speak: bool
    tone: str  # "confident", "cautious", "misdirection", "pressure"
    suggested_message: str
    strategic_purpose: str


def plan_table_talk(
    recent_chat: list[str],
    hand_strength: float,
    to_call: int,
    stack: int,
    opponent_profiles: dict[str, OpponentProfile],
    player_name: str,
) -> TalkStrategy:
    """Plan table talk aligned with strategy.
    
    Args:
        recent_chat: Recent table conversation
        hand_strength: Our hand strength (0.0-1.0)
        to_call: Amount to call
        stack: Remaining stack
        opponent_profiles: Profiles of opponents at table
        player_name: Our name
    
    Returns:
        TalkStrategy with tone and message suggestion
    """
    should_speak = True
    pressure_level = to_call / max(1, stack) if stack > 0 else 0
    
    if pressure_level > 0.5:
        should_speak = False  # Quiet under pressure
    
    if not recent_chat or len(recent_chat) < 2:
        should_speak = False  # Don't speak first
    
    tone = "balanced"
    if hand_strength > 0.75:
        tone = "confident"
    elif hand_strength < 0.35:
        tone = "cautious"
    
    # Respond to last message if exists
    purpose = "observation"
    suggested_msg = "Interesting board."
    
    if hand_strength > 0.8:
        tone = "confident"
        suggested_msg = "Texture favors aggression here."
        purpose = "project strength"
    elif hand_strength < 0.3 and pressure_level > 0.2:
        tone = "cautious"
        suggested_msg = "Let's see what happens."
        purpose = "minimize info leak"
    else:
        suggested_msg = "Pot odds make sense."
        purpose = "strategic narrative"
    
    return TalkStrategy(
        should_speak=should_speak,
        tone=tone,
        suggested_message=suggested_msg,
        strategic_purpose=purpose,
    )


# ============================================================================
# Tool 12: Hand Review and Leak Detector
# ============================================================================

@dataclass
class LeakFlag:
    leak_type: str  # "overfolding_turn", "underbluffing_river", etc.
    severity: str  # "minor", "moderate", "major"
    adjustment_suggestion: str


class LeakDetector:
    """Analyze hands to find exploitable patterns."""
    
    def __init__(self):
        self.action_patterns: dict[str, list[str]] = defaultdict(list)
    
    def record_hand_action(
        self,
        street: str,
        action: str,
        hand_strength: float,
        is_fold: bool = False,
    ) -> None:
        """Record action for pattern analysis."""
        key = f"{street}_{hand_strength:.1f}"
        self.action_patterns[key].append(action)
    
    def detect_leaks(self) -> list[LeakFlag]:
        """Detect exploitable patterns in recent hands."""
        leaks = []
        
        for pattern, actions in self.action_patterns.items():
            if len(actions) < 3:
                continue
            
            fold_rate = actions.count("fold") / len(actions)
            raise_rate = actions.count("raise") / len(actions)
            
            # Detect overfolding weak hands
            if "0." in pattern and fold_rate > 0.7:
                leaks.append(
                    LeakFlag(
                        leak_type="overfolding_weak",
                        severity="moderate",
                        adjustment_suggestion="defend more on turns/rivers",
                    )
                )
            
            # Detect underraising strong hands
            if "0.8" in pattern and raise_rate < 0.3:
                leaks.append(
                    LeakFlag(
                        leak_type="underaggression_strong",
                        severity="major",
                        adjustment_suggestion="3bet+ strong hands more often",
                    )
                )
        
        return leaks
