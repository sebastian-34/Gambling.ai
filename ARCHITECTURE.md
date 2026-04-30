# Poker Tools Architecture Reference

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         POKER GAME                              │
│                      (main.py / game.py)                        │
└──────────────┬──────────────────────────────────────────────────┘
               │
               │ Each Decision
               ↓
       ┌───────────────────┐
       │  LLMPokerAgent    │
       │   .decide(ctx)    │
       └────────┬──────────┘
                │
    ┌───────────┼───────────┬────────────┬────────────┬────────────┐
    │           │           │            │            │            │
    ↓           ↓           ↓            ↓            ↓            ↓
┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Tool 1 │ │ Tool 2 │ │ Tool 4  │ │ Tool 6   │ │ Tool 7   │ │ Memory   │
│Equity  │ │Pot Odds│ │Opponent │ │Bet Size  │ │Bluff     │ │ insights │
│Estimate│ │Calc   │ │Profile  │ │Recommend │ │Planning  │ │(Tool 10) │
└────────┘ └────────┘ └─────────┘ └──────────┘ └──────────┘ └──────────┘
    │           │           │            │            │            │
    └───────────┴───────────┴────────────┴────────────┴────────────┘
                            │
                    Analysis Results
                            │
                            ↓
                  ┌─────────────────────┐
                  │  Enhanced Prompt    │
                  │   (with analysis)   │
                  └──────────┬──────────┘
                             │
                             ↓
                  ┌─────────────────────┐
                  │  LLM Model          │
                  │  (ollama/external)  │
                  └──────────┬──────────┘
                             │
                             ↓
                  ┌─────────────────────┐
                  │  Decision Output    │
                  │  (JSON: action +    │
                  │   raise_amount)     │
                  └─────────────────────┘
```

---

## Tool Interaction Matrix

```
Tool   Used In        Called By         Data From         Data To
────────────────────────────────────────────────────────────────────
1      decide()       _build_prompt()   Hand + board      Equity %
2      decide()       _build_prompt()   Pot + equity      EV + rec
4      observe_event  _build_prompt()   Opponent action   Profile
5      observe_event  (tracking only)   Action history    Range
6      decide()       _build_prompt()   Pot + objective   Sizes
7      decide()       _build_prompt()   Equity + opp      Bluff plan
10     end_hand()     personal_context  Hand result       Similar hands
11     speak()        talk_prompt()     Hand + chat       Talk strategy
12     end_hand()     personal_context  Action pattern    Leaks
```

---

## Time-Series Data Collection

```
Hand 1     Hand 2     Hand 3     ...     Hand 50
  │          │          │                  │
  ├─ Tool 4: Profile    Profile    Profile  (cumulative)
  ├─ Tool 5: Range      Range      Range    (cumulative)
  ├─ Tool 10: Memory ←──────────────────→  (searchable)
  └─ Tool 12: Leaks     Leaks      Leaks   (detectable)
```

---

## Agent State Initialization

```python
LLMPokerAgent.__init__()
    ├─ self.name = profile.name
    ├─ self.profile = LLMProfile (model, host, timeout)
    ├─ self._decision_agent = None (lazy init)
    ├─ self._talk_agent = None (lazy init)
    ├─ self._opponent_stats = defaultdict (legacy tracking)
    ├─ self._opponent_profiler = OpponentProfiler()    ← Tool 4
    ├─ self._range_tracker = RangeTracker()            ← Tool 5
    ├─ self._hand_memory = HandMemory(max_memory=100)  ← Tool 10
    └─ self._leak_detector = LeakDetector()            ← Tool 12
```

---

## Decision Flow (Step-by-Step)

```
1. Agent.decide(ctx, rng) called
   │
   ├─ _build_prompt(ctx)
   │  ├─ Tool 1: estimate_equity() → equity_result
   │  ├─ Tool 2: calculate_pot_odds() → pot_odds_result
   │  ├─ Tool 4: get_profile(opponent) for each opponent
   │  ├─ Tool 6: recommend_bet_size() → bet_rec
   │  ├─ Tool 7: plan_bluff() → bluff_plan
   │  └─ Format all into enhanced prompt string
   │
   ├─ _call_llm(prompt) → response_text
   │  └─ LLM processes tools output + makes decision
   │
   ├─ _parse_decision(response_text) → Decision object
   │  └─ Validate and convert JSON to Decision
   │
   └─ Return Decision(action, raise_amount)
```

---

## Event Observation Flow (Step-by-Step)

```
1. Agent.observe_event(event) called
   │
   ├─ Append to _recent_observations (max 40)
   │
   ├─ Detect actor from event
   │
   └─ If opponent action:
      ├─ Tool 4: record_action(opponent, action, is_pressure)
      └─ Tool 5: update_range_after_action(opponent, street, action)
```

---

## Hand End Flow (Step-by-Step)

```
1. Agent.end_hand(chip_delta, won) called
   │
   ├─ Update chip_trend (legacy)
   │
   ├─ Append to hand_journal (max 18)
   │
   ├─ Tool 10: record_hand(hand_number, street, action, result, equity)
   │  └─ Store in memory for later retrieval
   │
   └─ Tool 12: record_hand_action(street, action, equity, is_fold)
      └─ Track patterns for leak detection
```

---

## Talk Flow (Step-by-Step)

```
1. Agent.speak(ctx, rng) called
   │
   ├─ _build_talk_prompt(ctx)
   │  ├─ Tool 11: plan_table_talk()
   │  │  ├─ Analyze recent_chat
   │  │  ├─ Evaluate hand strength
   │  │  ├─ Check pressure level
   │  │  ├─ Get opponent profiles
   │  │  └─ Return TalkStrategy
   │  │
   │  └─ Format strategy into prompt
   │
   ├─ _call_llm_chat(prompt) → response_text
   │  └─ LLM generates spoken message
   │
   ├─ _parse_chat_message(response_text) → message string
   │
   └─ Return message (or "" if staying silent)
```

---

## Personal Context Assembly (Step-by-Step)

```
_build_personal_context() returns string with:

1. Opponent tendencies
   └─ From self._opponent_stats (legacy)

2. Bankroll trend
   └─ From self._chip_trend

3. Dialogue impact
   └─ From self._dialogue_impact

4. Recent results
   └─ From self._hand_journal (last 3)

5. Active leaks
   └─ Tool 12: _leak_detector.detect_leaks()
      └─ Return leak alerts

6. Memory insights
   └─ Tool 10: _hand_memory.find_similar_hands(...)
      └─ Return similar past hand outcomes
```

---

## Tool Lifecycle

```
┌──────────────────────────────────────────────────┐
│           Tournament (N hands)                    │
└──────────────────┬───────────────────────────────┘
                   │
          ┌────────┴────────┐
          │                 │
          ↓                 ↓
     Hand 1-N          Hand 1-N
     ├─ Tool 4:        ├─ Tool 4:
     │  Profile        │  Accumulate
     │  builds from    │  opponent
     │  0              │  data
     │                 │
     ├─ Tool 10:       ├─ Tool 10:
     │  Memory         │  Store and
     │  starts empty   │  search
     │                 │
     ├─ Tool 12:       ├─ Tool 12:
     │  Leaks start    │  Detect and
     │  empty          │  correct
     │                 │
     └─ Tools 1,2,     └─ Tools 1,2,
        5,6,7,11       5,6,7,11
        Fresh each     Fresh each
        hand           hand
```

---

## Memory Storage Details (Tool 10)

```
HandMemory stores list of dicts:
[
    {
        hand_number: 1,
        street: "river",
        action: "raise",
        board_type: "wet",
        result: "won",
        equity: 0.55,
    },
    { hand_number: 2, ... },
    ...
    { hand_number: 100, ... }  ← max_memory=100
]

When query:
  find_similar_hands(street="turn", board_type="wet", equity=0.60)
  ├─ Filter by street
  ├─ Filter by board_type
  ├─ Filter by equity (±0.3)
  └─ Score by similarity
      └─ Return top_n sorted by similarity
```

---

## Opponent Profile Details (Tool 4)

```
OpponentProfile:
  name: str
  vpip: float              # % hands played
  pfr: float               # % hands raised preflop
  aggression: float        # raise/(raise+call)
  fold_to_pressure: float  # % fold when pressured
  bluff_tendency: float    # estimated bluff %
  profile_type: str        # "tight", "balanced", "loose"
  aggression_type: str     # "passive", "balanced", "aggressive"

Classification logic:
  vpip < 35% → "tight"
  vpip 35-60% → "balanced"
  vpip > 60% → "loose"

  aggression < 35% → "passive"
  aggression 35-65% → "balanced"
  aggression > 65% → "aggressive"
```

---

## Decision Context (Input to all Tools)

```python
@dataclass
class DecisionContext:
    hand_strength: float      # 0.0 to 1.0 (heuristic)
    to_call: int             # Chips needed to call
    current_bet: int         # Current bet level
    pot: int                 # Total pot size
    min_raise: int           # Minimum raise amount
    stack: int               # Remaining stack
    street: str              # "preflop", "flop", "turn", "river"
    community_count: int     # 0, 3, 4, or 5 cards
    player_name: str         # Agent name
    recent_chat: list[str]   # Recent table talk
```

---

## Tool Output Examples

### Tool 1 Output
```
hand_equity=62.3%
(From: estimate_equity([14,13], [12,11,10], num_opponents=2))
```

### Tool 2 Output
```
break_even_equity=42.5%;
ev_if_call=+8.3 chips;
ev_recommendation=call
```

### Tool 4 Output
```
Opponent Reads: Llama Agent=loose,aggressive; Mistral Agent=tight,passive
```

### Tool 6 Output
```
Sizing_recommendation=150 chips (value bet: medium build; wet board: bigger)
```

### Tool 7 Output
```
Bluff_plan=bluff (strong blockers) (fold_equity=62.3%)
```

### Tool 10 Output
```
Similar recent hand: raise on wet → won (similarity: 95.0%)
```

### Tool 11 Output
```
Talk_Strategy: should_speak=True; tone=confident; purpose=project strength
```

### Tool 12 Output
```
Active Leaks: overfolding_weak(moderate); underaggression_strong(major)
```

---

## Prompt Structure After Tool Integration

```
[Base Instructions]
"You are deciding a single Texas Hold'em action..."

[Game State]
"You are [player_name]."
"Street=[street]; hand_strength=[hand_strength];"
"to_call=[to_call]; pot=[pot]; stack=[stack];"

[Tool Analysis] ← NEW
"Tool Analysis:"
"  Equity Analysis: hand_equity=62.3%; break_even=45.0%;"
"  Sizing_recommendation=150 chips (...);"
"  Bluff_plan=bluff (...); fold_equity=62.3%;"
"  Opponent Reads: Llama=loose,aggressive; ..."

[Personal Context]
"Personal context:"
"  bankroll_trend=up;"
"  dialogue_signal=effective;"
"  opponent_reads=...;"
"  recent_results=...;"
"  Active Leaks: ...;"
"  Similar recent hand: ...;"

[Rules]
"Rules: if to_call is 0 then choose check or raise..."

[Expected Output]
'{"action":"fold|call|check|raise","raise_amount":number}'
```

---

## Key Metrics Tracked Over Tournament

```
Tool 4 (Opponent Profiler) tracks per opponent:
  - hands_played: int
  - raises: int
  - calls: int
  - folds: int
  - folds_to_pressure: int
  - pressure_spots: int
  - showdown_hands: int
  - bluffs: int

Tool 10 (Hand Memory) stores per hand:
  - hand_number
  - street
  - action taken
  - board type
  - result (won/lost)
  - equity

Tool 12 (Leak Detector) accumulates per pattern:
  - action_patterns: dict[street_equity_key, list[actions]]
  - fold_rate by equity range
  - raise_rate by equity range
```

---

## Integration Checklist

✓ Tools module created (tools.py)  
✓ All 9 tools implemented  
✓ Imports added to agents.py  
✓ Tools instantiated in __init__  
✓ Tools integrated in _build_prompt()  
✓ Tools integrated in _build_talk_prompt()  
✓ Tools integrated in observe_event()  
✓ Tools integrated in end_hand()  
✓ Tools integrated in _build_personal_context()  
✓ Syntax validated  
✓ Imports verified  
✓ Agents load successfully  
✓ Demo tests all tools  
✓ Documentation complete  

