"""Demo script showing all 9 integrated poker tools in action."""

from poker.tools import (
    estimate_equity,
    calculate_pot_odds,
    OpponentProfiler,
    RangeTracker,
    recommend_bet_size,
    plan_bluff,
    HandMemory,
    plan_table_talk,
    LeakDetector,
    OpponentProfile,
)
import random


def demo_tool_1_equity():
    """Tool 1: Odds and Equity Estimator"""
    print("\n" + "="*60)
    print("TOOL 1: ODDS AND EQUITY ESTIMATOR")
    print("="*60)
    
    # Estimate equity for Ace-King on a high board
    equity = estimate_equity(
        hole_cards=[14, 13],  # AK
        board_cards=[12, 11, 10],  # QJT (broadway)
        num_opponents=2,
        num_simulations=1000,
        rng=random.Random(42),
    )
    
    print(f"Your hand: AK")
    print(f"Board: QJT (broadway)")
    print(f"Opponents: 2")
    print(f"\nResults:")
    print(f"  Win probability:  {equity.win_prob:.1%}")
    print(f"  Tie probability:  {equity.tie_prob:.1%}")
    print(f"  Loss probability: {equity.loss_prob:.1%}")
    print(f"  Your equity:      {equity.win_equity:.1%}")


def demo_tool_2_pot_odds():
    """Tool 2: Pot-Odds and Break-Even Calculator"""
    print("\n" + "="*60)
    print("TOOL 2: POT-ODDS AND BREAK-EVEN CALCULATOR")
    print("="*60)
    
    odds = calculate_pot_odds(
        to_call=100,
        pot=350,
        equity=0.55,  # 55% equity
        expected_future_bet=0,
    )
    
    print(f"To call: 100 chips")
    print(f"Current pot: 350 chips")
    print(f"Your equity: 55%")
    print(f"\nResults:")
    print(f"  Pot odds:            {odds.pot_odds:.1%}")
    print(f"  Break-even equity:   {odds.break_even_equity:.1%}")
    print(f"  EV if call:          {odds.ev_if_call:+.1f} chips")
    print(f"  EV if fold:          {odds.ev_if_fold:.1f} chips")
    print(f"  Recommendation:      {odds.ev_recommendation.upper()}")


def demo_tool_4_opponent_profiler():
    """Tool 4: Opponent Profiler"""
    print("\n" + "="*60)
    print("TOOL 4: OPPONENT PROFILER")
    print("="*60)
    
    profiler = OpponentProfiler()
    
    # Simulate an aggressive opponent
    for _ in range(5):
        profiler.record_action("Aggressive Opponent", "raise", is_pressure=False)
    for _ in range(3):
        profiler.record_action("Aggressive Opponent", "call", is_pressure=False)
    for _ in range(2):
        profiler.record_action("Aggressive Opponent", "fold", is_pressure=False)
    
    # Simulate a tight opponent
    for _ in range(2):
        profiler.record_action("Tight Opponent", "raise", is_pressure=False)
    for _ in range(1):
        profiler.record_action("Tight Opponent", "call", is_pressure=False)
    for _ in range(7):
        profiler.record_action("Tight Opponent", "fold", is_pressure=False)
    
    agg_profile = profiler.get_profile("Aggressive Opponent")
    tight_profile = profiler.get_profile("Tight Opponent")
    
    print(f"\nAggressive Opponent:")
    print(f"  VPIP:                {agg_profile.vpip:.1%}")
    print(f"  PFR:                 {agg_profile.pfr:.1%}")
    print(f"  Aggression:          {agg_profile.aggression:.1%}")
    print(f"  Profile type:        {agg_profile.profile_type}")
    print(f"  Aggression type:     {agg_profile.aggression_type}")
    print(f"  Bluff tendency:      {agg_profile.bluff_tendency:.1%}")
    
    print(f"\nTight Opponent:")
    print(f"  VPIP:                {tight_profile.vpip:.1%}")
    print(f"  PFR:                 {tight_profile.pfr:.1%}")
    print(f"  Aggression:          {tight_profile.aggression:.1%}")
    print(f"  Profile type:        {tight_profile.profile_type}")
    print(f"  Aggression type:     {tight_profile.aggression_type}")


def demo_tool_5_range_tracker():
    """Tool 5: Range Tracker"""
    print("\n" + "="*60)
    print("TOOL 5: RANGE TRACKER")
    print("="*60)
    
    tracker = RangeTracker()
    
    # Opponent raises on flop
    tracker.update_range_after_action("Opponent", "flop", "raise", [])
    summary = tracker.get_range_summary("Opponent", "flop")
    print(f"After opponent raises on flop:")
    print(f"  {summary}")
    
    # Opponent calls on turn
    tracker.update_range_after_action("Opponent", "turn", "call", [])
    summary = tracker.get_range_summary("Opponent", "turn")
    print(f"\nAfter opponent calls on turn:")
    print(f"  {summary}")


def demo_tool_6_bet_size_recommender():
    """Tool 6: Bet-Size Recommender"""
    print("\n" + "="*60)
    print("TOOL 6: BET-SIZE RECOMMENDER")
    print("="*60)
    
    # Value bet on wet board
    rec_value = recommend_bet_size(
        pot=200,
        stack=1000,
        min_raise=50,
        objective="value",
        board_texture="wet",
        equity=0.75,
    )
    
    # Bluff on dry board
    rec_bluff = recommend_bet_size(
        pot=200,
        stack=1000,
        min_raise=50,
        objective="bluff",
        board_texture="dry",
        equity=0.25,
    )
    
    print(f"\nValue bet on WET board with 75% equity:")
    print(f"  Small size:      {rec_value.small_size} chips")
    print(f"  Medium size:     {rec_value.medium_size} chips")
    print(f"  Large size:      {rec_value.large_size} chips")
    print(f"  Recommended:     {rec_value.recommended_size} chips")
    print(f"  Reason:          {rec_value.recommendation_reason}")
    
    print(f"\nBluff on DRY board with 25% equity:")
    print(f"  Small size:      {rec_bluff.small_size} chips")
    print(f"  Medium size:     {rec_bluff.medium_size} chips")
    print(f"  Large size:      {rec_bluff.large_size} chips")
    print(f"  Recommended:     {rec_bluff.recommended_size} chips")
    print(f"  Reason:          {rec_bluff.recommendation_reason}")


def demo_tool_7_bluff_planner():
    """Tool 7: Bluff Planner"""
    print("\n" + "="*60)
    print("TOOL 7: BLUFF PLANNER")
    print("="*60)
    
    # Good bluff spot
    good_bluff = plan_bluff(
        equity=0.20,
        pot=300,
        bet_size=200,
        opponent_fold_to_pressure=0.65,
        has_blockers=True,
        board_runout_bad=False,
    )
    
    # Bad bluff spot
    bad_bluff = plan_bluff(
        equity=0.20,
        pot=300,
        bet_size=200,
        opponent_fold_to_pressure=0.25,
        has_blockers=False,
        board_runout_bad=True,
    )
    
    print(f"\nGood bluff opportunity:")
    print(f"  Should bluff:       {good_bluff.should_bluff}")
    print(f"  Fold equity:        {good_bluff.fold_equity:.1%}")
    print(f"  EV of bluff:        {good_bluff.ev_of_bluff:+.1f} chips")
    print(f"  Confidence:         {good_bluff.confidence:.1%}")
    print(f"  Blockers bonus:     {good_bluff.blocker_bonus:+.1%}")
    print(f"  Plan:               {good_bluff.plan_summary}")
    
    print(f"\nBad bluff opportunity:")
    print(f"  Should bluff:       {bad_bluff.should_bluff}")
    print(f"  Fold equity:        {bad_bluff.fold_equity:.1%}")
    print(f"  EV of bluff:        {bad_bluff.ev_of_bluff:+.1f} chips")
    print(f"  Reason:             Low fold equity + bad runout")


def demo_tool_10_memory():
    """Tool 10: Memory Retrieval Tool"""
    print("\n" + "="*60)
    print("TOOL 10: MEMORY RETRIEVAL TOOL")
    print("="*60)
    
    memory = HandMemory(max_memory=100)
    
    # Record some hands
    for i in range(1, 6):
        memory.record_hand(
            hand_number=i,
            street="river",
            action="raise" if i % 2 == 0 else "call",
            board_type="wet" if i % 2 == 0 else "dry",
            result="won" if i <= 3 else "lost",
            equity=0.55 + (i * 0.05),
        )
    
    # Find similar hands
    similar = memory.find_similar_hands(
        street="river",
        board_type="wet",
        equity=0.60,
        top_n=2,
    )
    
    print(f"Stored 5 hands in memory")
    print(f"\nSearching for similar hands on RIVER with ~60% equity on WET board:")
    for hand in similar:
        print(f"  Hand #{hand.hand_number}: {hand.my_action} on {hand.board_type} → {hand.result} "
              f"(similarity: {hand.similarity_score:.1%})")
    
    if not similar:
        print(f"  No similar hands found")


def demo_tool_11_table_talk():
    """Tool 11: Table-Talk Strategy Tool"""
    print("\n" + "="*60)
    print("TOOL 11: TABLE-TALK STRATEGY TOOL")
    print("="*60)
    
    profiler = OpponentProfiler()
    
    # Strong hand, no pressure
    strategy_strong = plan_table_talk(
        recent_chat=["Opponent: Could be anything", "You: Not sure yet"],
        hand_strength=0.85,
        to_call=0,
        stack=2000,
        opponent_profiles={},
        player_name="You",
    )
    
    # Weak hand, high pressure
    strategy_weak = plan_table_talk(
        recent_chat=["Opponent: I'm all-in", "You: Folding this"],
        hand_strength=0.20,
        to_call=500,
        stack=600,  # Very short stack
        opponent_profiles={},
        player_name="You",
    )
    
    print(f"\nWith STRONG hand, no pressure:")
    print(f"  Should speak:       {strategy_strong.should_speak}")
    print(f"  Tone:               {strategy_strong.tone}")
    print(f"  Strategy:           {strategy_strong.strategic_purpose}")
    print(f"  Suggestion:         '{strategy_strong.suggested_message}'")
    
    print(f"\nWith WEAK hand, HIGH pressure:")
    print(f"  Should speak:       {strategy_weak.should_speak}")
    print(f"  Tone:               {strategy_weak.tone}")
    print(f"  Strategy:           {strategy_weak.strategic_purpose}")


def demo_tool_12_leak_detector():
    """Tool 12: Hand-Review and Leak Detector"""
    print("\n" + "="*60)
    print("TOOL 12: HAND-REVIEW AND LEAK DETECTOR")
    print("="*60)
    
    detector = LeakDetector()
    
    # Record overfolding weak hands
    for _ in range(5):
        detector.record_hand_action(street="turn", action="fold", hand_strength=0.25)
        detector.record_hand_action(street="turn", action="fold", hand_strength=0.30)
    
    # Record underaggression with strong hands
    for _ in range(3):
        detector.record_hand_action(street="river", action="call", hand_strength=0.85)
    
    leaks = detector.detect_leaks()
    
    print(f"\nDetected {len(leaks)} leak(s):")
    for leak in leaks:
        print(f"  • {leak.leak_type.upper()} ({leak.severity})")
        print(f"    → {leak.adjustment_suggestion}")


def main():
    """Run all tool demos."""
    print("\n" + "▓"*60)
    print("▓" + " "*58 + "▓")
    print("▓" + "  POKER AGENT TOOLS INTEGRATION DEMO  ".center(58) + "▓")
    print("▓" + " "*58 + "▓")
    print("▓"*60)
    
    demo_tool_1_equity()
    demo_tool_2_pot_odds()
    demo_tool_4_opponent_profiler()
    demo_tool_5_range_tracker()
    demo_tool_6_bet_size_recommender()
    demo_tool_7_bluff_planner()
    demo_tool_10_memory()
    demo_tool_11_table_talk()
    demo_tool_12_leak_detector()
    
    print("\n" + "▓"*60)
    print("▓" + "  Demo Complete!  ".center(58) + "▓")
    print("▓" + " "*58 + "▓")
    print("▓  All 9 tools are now integrated and ready to use.  ".ljust(59) + "▓")
    print("▓  See TOOLS_INTEGRATION.md for full documentation.  ".ljust(59) + "▓")
    print("▓"*60)


if __name__ == "__main__":
    main()
