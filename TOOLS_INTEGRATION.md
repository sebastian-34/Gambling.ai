# Poker Agent Tools Integration Guide

This document explains the 9 tools now integrated into your poker agents' decision-making system.

---

## Overview

The tools are integrated into the `LLMPokerAgent` class and automatically run during each decision. They provide structured analysis across three main flows:

1. **Decision prompts** - Use tools to inform `decide()` calls
2. **Talk prompts** - Use tools to guide `speak()` calls  
3. **Background tracking** - Continuously record observations for future decisions

---

## The 9 Integrated Tools

### **Tool 1: Odds and Equity Estimator**

**File:** `tools.py` - `estimate_equity()`

**What it does:**
- Estimates hand equity (win probability) using Monte Carlo simulation
- Inputs: your hole cards, community cards, number of opponents
- Outputs: win_prob, tie_prob, loss_prob, win_equity

**Where it's used:**
- In `_build_prompt()` to provide equity context to the LLM
- Called during decision phase to estimate hand strength objectively

**Example output:**
```
Equity Analysis: hand_equity=62.3%; break_even=45.0%; pot_odds_recommendation=call.
```

---

### **Tool 2: Pot-Odds and Break-Even Calculator**

**File:** `tools.py` - `calculate_pot_odds()`

**What it does:**
- Calculates pot odds (ratio of call to total pot)
- Determines break-even equity needed to call profitably
- Computes expected value of calling vs folding
- Gives EV-based recommendation (call/fold/indifferent)

**Where it's used:**
- In `_build_prompt()` to provide EV analysis to the LLM
- Helps LLM understand if a call is mathematically justified

**Example output:**
```
break_even=42.5%; ev_if_call=+8.3 chips; ev_recommendation=call
```

---

### **Tool 4: Opponent Profiler**

**File:** `tools.py` - `OpponentProfiler` class

**What it does:**
- Tracks opponent stats: VPIP (voluntarily put money in), PFR (preflop raise rate), aggression
- Classifies opponents as: tight/loose, passive/balanced/aggressive
- Estimates fold-to-pressure and bluff tendency

**Where it's used:**
- In `observe_event()` - records opponent actions as they happen
- In `_build_prompt()` - provides opponent profile summary
- Called whenever opponent raises, calls, or folds

**Example output:**
```
Opponent Reads: Llama Agent=loose,aggressive; Mistral Agent=tight,passive
```

**How to use the data:**
```python
profile = agent._opponent_profiler.get_profile("Opponent Name")
print(f"Fold to pressure: {profile.fold_to_pressure:.1%}")
```

---

### **Tool 5: Range Tracker**

**File:** `tools.py` - `RangeTracker` class

**What it does:**
- Estimates opponent hand ranges based on observed actions
- Tracks what hands they likely have on each street
- Provides readable range summaries

**Where it's used:**
- In `observe_event()` - updates ranges as opponent acts
- In decision phase - provides range context to LLM

**Example output:**
```
Range summary: Opponent on flop: observed raise, call, fold
```

---

### **Tool 6: Bet-Size Recommender**

**File:** `tools.py` - `recommend_bet_size()`

**What it does:**
- Recommends three bet sizes: small, medium, large
- Adjusts sizing based on objective: value, bluff, deny_equity, protection
- Adjusts for board texture: dry, wet, connected, high_card

**Where it's used:**
- In `_build_prompt()` to suggest raise sizes to the LLM
- Provides specific chip amounts as guidance

**Example output:**
```
Sizing_recommendation=150 chips (value bet: medium build; wet board: bigger)
```

**Logic:**
- **Value hands** → medium sizing
- **Bluffing** → large sizing (credible)
- **Deny equity** (vs draws) → large sizing
- **Wet boards** → increase size
- **Dry boards** → can go smaller

---

### **Tool 7: Bluff Planner**

**File:** `tools.py` - `plan_bluff()`

**What it does:**
- Calculates fold equity (% opponent will fold to bluff)
- Computes EV of bluffing
- Considers blockers and board runout
- Returns should_bluff recommendation with confidence

**Where it's used:**
- In `_build_prompt()` when agent has weak hand
- Helps LLM decide if bluff is EV-positive

**Example output:**
```
Bluff_plan=bluff (strong blockers) (fold_equity=62.3%)
```

**EV Formula:**
```
EV = (fold_equity × pot) + (call_probability × ev_if_called)
```

---

### **Tool 10: Memory Retrieval Tool**

**File:** `tools.py` - `HandMemory` class

**What it does:**
- Stores up to 100 recent hands
- Retrieves similar past hands by: street, board type, equity range
- Finds patterns: "similar hand on turn with 55% equity: I won via call"

**Where it's used:**
- In `end_hand()` - records hand outcomes
- In `_build_personal_context()` - retrieves similar hands for insight
- Helps agents learn from recent table dynamics

**Example output:**
```
Similar recent hand: call → won
```

**How to manually retrieve:**
```python
similar = agent._hand_memory.find_similar_hands(
    street="turn",
    board_type="wet", 
    equity=0.55,
    top_n=3
)
```

---

### **Tool 11: Table-Talk Strategy Tool**

**File:** `tools.py` - `plan_table_talk()`

**What it does:**
- Decides whether to speak at table
- Selects tone: confident, cautious, misdirection
- Suggests aligned message
- Gives strategic purpose: pressure, minimize_info_leak, etc.

**Where it's used:**
- In `_build_talk_prompt()` to guide talking decisions
- Provides structured strategy to LLM instead of random banter

**Example output:**
```
Talk_Strategy: should_speak=True; tone=confident; purpose=project strength; 
suggestion='Texture favors aggression here'.
```

**Decision factors:**
- Quiet under high pressure (to_call / stack > 50%)
- Quiet early in hand (need context first)
- Confident tone if hand_strength > 75%
- Cautious tone if hand_strength < 35%

---

### **Tool 12: Hand-Review and Leak Detector**

**File:** `tools.py` - `LeakDetector` class

**What it does:**
- Analyzes action patterns across hands
- Detects exploitable leaks:
  - Overfolding weak hands
  - Underaggression with strong hands
  - Predictable patterns by street
- Returns leak flags with severity and adjustment suggestions

**Where it's used:**
- In `end_hand()` - records action for analysis
- In `_build_personal_context()` - alerts to active leaks
- Helps agents self-correct over tournament

**Example output:**
```
Active Leaks: overfolding_weak(moderate); underaggression_strong(major).
```

**How to manually check:**
```python
leaks = agent._leak_detector.detect_leaks()
for leak in leaks:
    print(f"{leak.leak_type}: {leak.adjustment_suggestion}")
```

---

## Data Flow Diagram

```
Start Hand
    ↓
Agent decides (decide() called)
    ├─ Tool 1: Equity estimate
    ├─ Tool 2: Pot-odds calc
    ├─ Tool 4: Opponent profile lookup
    ├─ Tool 6: Bet-size recommend
    ├─ Tool 7: Bluff planning
    └─ LLM gets analysis → makes JSON decision
    ↓
Agent speaks (speak() called)
    ├─ Tool 11: Talk strategy
    └─ LLM gets guidance → speaks or stays quiet
    ↓
Action happens
    ↓
observe_event() called
    ├─ Tool 4: Record opponent action
    └─ Tool 5: Update range estimate
    ↓
End Hand
    ├─ Tool 10: Store hand in memory
    ├─ Tool 12: Record action for leak detection
    └─ Analyze leaks → feed into next hand
```

---

## Example: Integration in Action

### Setup
```python
from poker.agents import build_default_agents
agents = build_default_agents()
agent = agents[0]  # Llama Agent
```

### During a hand
```python
# Agent makes decision
from poker.agents import DecisionContext
ctx = DecisionContext(
    hand_strength=0.65,
    to_call=50,
    current_bet=50,
    pot=200,
    min_raise=50,
    stack=1000,
    street="flop",
    community_count=3,
    player_name="Llama Agent",
    recent_chat=[]
)

decision = agent.decide(ctx, random.Random())
print(decision.action)  # Internally used Tool 1, 2, 4, 6, 7
```

### After hand completes
```python
# Agent records hand and detects leaks
agent.end_hand(chip_delta=+150, won=True)
# Internally used Tool 10 (memory) and Tool 12 (leak detection)

# Check detected leaks
leaks = agent._leak_detector.detect_leaks()
if leaks:
    print(f"Alert: {leaks[0].leak_type}")
```

### Access tool data directly
```python
# Get opponent profile
profile = agent._opponent_profiler.get_profile("Mistral Agent")
print(f"Mistral is {profile.profile_type} and {profile.aggression_type}")

# Get recent similar hands
similar = agent._hand_memory.find_similar_hands(
    street="turn", 
    board_type="wet", 
    equity=0.60,
    top_n=2
)

# Check active leaks
for leak in agent._leak_detector.detect_leaks():
    print(f"Leak: {leak.leak_type} - {leak.adjustment_suggestion}")
```

---

## Key Design Principles

1. **Readable code** - Each tool is a simple, self-contained function or class
2. **Clear inputs/outputs** - Every tool documents what it takes and returns
3. **Non-blocking** - Tools run fast; LLM still has fallback if tools are slow
4. **Progressive learning** - Memory and profiling improve over tournament
5. **Explainability** - All tool outputs are included in LLM prompt for transparency

---

## Extending the Tools

To add a new metric or tool:

1. **Add to `tools.py`**
   ```python
   def my_new_tool(input1, input2) -> MyResult:
       # logic
       return MyResult(...)
   ```

2. **Initialize in `LLMPokerAgent.__init__`**
   ```python
   self._my_tool = MyTool()
   ```

3. **Call in decision/speak flow**
   ```python
   result = self._my_tool.analyze(ctx)
   # Add result to prompt
   ```

4. **Update tracking in `observe_event()` or `end_hand()`**
   ```python
   self._my_tool.record(data)
   ```

---

## Testing Tools Individually

```python
from poker.tools import estimate_equity, calculate_pot_odds

# Test equity
equity = estimate_equity([14, 13], [12, 11, 10], num_opponents=3)
print(f"AA on 980 flop: {equity.win_equity:.1%}")

# Test pot odds
odds = calculate_pot_odds(to_call=100, pot=400, equity=0.60)
print(f"Break-even: {odds.break_even_equity:.1%}, EV: {odds.ev_if_call}")
```

---

## Summary Table

| Tool | Module | Key Class/Function | Used in | Output |
|------|--------|-------------------|---------|--------|
| 1 | tools | `estimate_equity()` | decide prompt | equity % |
| 2 | tools | `calculate_pot_odds()` | decide prompt | call/fold recommendation |
| 4 | tools | `OpponentProfiler` | observe_event, decide prompt | opponent profile |
| 5 | tools | `RangeTracker` | observe_event | range summary |
| 6 | tools | `recommend_bet_size()` | decide prompt | size recommendation |
| 7 | tools | `plan_bluff()` | decide prompt | bluff recommendation |
| 10 | tools | `HandMemory` | end_hand, personal context | similar hand |
| 11 | tools | `plan_table_talk()` | speak prompt | talk strategy |
| 12 | tools | `LeakDetector` | end_hand, personal context | leak alerts |

