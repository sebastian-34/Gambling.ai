# Poker Agent Tools - Quick Start Guide

## What You Have

You now have **9 professional poker decision-support tools** integrated into your agents. They automatically enhance every decision without requiring any code changes to run the game.

---

## Files Created/Modified

### New Files
- **`poker/tools.py`** (870 lines)
  - All 9 tool implementations
  - Clean, understandable code
  - Well-documented functions and classes

- **`TOOLS_INTEGRATION.md`** (500+ lines)
  - Complete tool documentation
  - Data flow diagrams
  - API reference and examples

- **`demo_tools.py`** (400+ lines)
  - Runnable demonstrations of each tool
  - Real output examples
  - Easy to understand and extend

### Modified Files
- **`poker/agents.py`**
  - Added tool imports
  - Instantiated all tool instances in `LLMPokerAgent.__init__`
  - Enhanced `_build_prompt()` with tool analysis
  - Enhanced `_build_talk_prompt()` with talk strategy
  - Enhanced `_build_personal_context()` with leak detection + memory
  - Enhanced `observe_event()` to feed opponent data to tools
  - Enhanced `end_hand()` to record hands for memory and leak detection

---

## Run Your Agents

Your agents now automatically use all tools. Just run the game normally:

```bash
cd c:\Users\benme\VisStudioC\NLP\Gambling.ai
python main.py --rounds 25
```

**Behind the scenes:**
- Every decision automatically gets equity analysis, pot-odds, opponent profiles, bet sizing, bluff planning
- Every table talk uses strategic guidance
- Every action updates opponent models and range estimates
- Every hand ending updates memory and leak detection
- Agents learn and adapt over the tournament

---

## See Tools in Action

Run the demo to see all tools working:

```bash
python demo_tools.py
```

Output shows:
1. Equity estimation (AK on broadway flop)
2. Pot-odds calculations
3. Opponent profiling (aggressive vs tight)
4. Range tracking
5. Bet-size recommendations
6. Bluff planning with EV
7. Hand memory retrieval
8. Table-talk strategy
9. Leak detection

---

## Access Tool Data Programmatically

```python
from poker.agents import build_default_agents

agents = build_default_agents()
agent = agents[0]  # Get any agent

# Tool 4: Get opponent profile
profile = agent._opponent_profiler.get_profile("Opponent Name")
print(f"Aggression: {profile.aggression:.1%}")
print(f"Type: {profile.profile_type}")

# Tool 10: Find similar past hands
similar = agent._hand_memory.find_similar_hands(
    street="turn",
    board_type="wet",
    equity=0.60,
    top_n=3
)
for hand in similar:
    print(f"Hand #{hand.hand_number}: {hand.my_action} → {hand.result}")

# Tool 12: Detect leaks
leaks = agent._leak_detector.detect_leaks()
for leak in leaks:
    print(f"Leak: {leak.leak_type}")
    print(f"Suggestion: {leak.adjustment_suggestion}")
```

---

## The 9 Tools at a Glance

| # | Tool | What It Does | When Used |
|---|------|-------------|-----------|
| 1 | **Equity Estimator** | Calculates hand win% via simulation | Every decision |
| 2 | **Pot-Odds Calculator** | Computes break-even equity + EV | Every decision |
| 4 | **Opponent Profiler** | Tracks VPIP, PFR, aggression, tendencies | Observe action + decision time |
| 5 | **Range Tracker** | Estimates opponent hand ranges | Observe action |
| 6 | **Bet-Size Recommender** | Suggests sizing by objective + board | Every decision |
| 7 | **Bluff Planner** | Calculates fold equity + EV of bluff | Every decision |
| 10 | **Hand Memory** | Stores/retrieves similar past hands | End of hand + decision time |
| 11 | **Table-Talk Strategy** | Decides when/how to talk | Every speak() call |
| 12 | **Leak Detector** | Finds exploitable patterns | End of hand + decision time |

---

## How Tools Are Integrated Into Prompts

### Decision Prompt Includes:
```
Tool Analysis: 
  - Equity Analysis: hand_equity=62.3%; break_even=45.0%; pot_odds_recommendation=call
  - Sizing_recommendation=150 chips (value bet: medium build; wet board: bigger)
  - Bluff_plan=bluff (strong blockers) (fold_equity=62.3%)
  - Opponent Reads: Llama Agent=loose,aggressive; Mistral Agent=tight,passive
```

### Talk Prompt Includes:
```
Talk_Strategy: should_speak=True; tone=confident; purpose=project strength; 
suggestion='Texture favors aggression here'
```

### Personal Context Includes:
```
Active Leaks: overfolding_weak(moderate); underaggression_strong(major)
Similar recent hand: call → won
```

---

## Extend the Tools

To add your own tool:

### 1. Add to `poker/tools.py`
```python
def my_new_tool(context) -> MyResult:
    """Your tool description."""
    # Logic here
    return MyResult(...)
```

### 2. Initialize in `LLMPokerAgent.__init__`
```python
self._my_tool = MyTool()
```

### 3. Use in decision flow
```python
result = self._my_tool.analyze(ctx)
# Include in prompt
```

### 4. Update in observation/end-hand
```python
self._my_tool.record(data)  # In observe_event() or end_hand()
```

---

## Troubleshooting

### Tools not affecting agent behavior?
- The tools provide input to the LLM prompts
- If LLM ignores them, it's an LLM model choice, not the tools
- Try a different model or adjust prompt weighting

### Performance slow?
- Tools are lightweight (mostly math, no deep learning)
- Monte Carlo equity estimation (Tool 1) uses 1000 samples—adjust if needed:
  ```python
  equity = estimate_equity(..., num_simulations=500)  # Faster
  ```

### Want to disable a tool?
- Comment out in `_build_prompt()` or `_build_talk_prompt()`
- Remove from `observe_event()` if you don't want tracking

---

## Examples

### Example 1: Check opponent stats after tournament
```python
game = PokerGame(agents=[...], starting_stack=1000)
game.play_tournament(rounds=100)

for agent in game.players:
    print(f"\n{agent.agent.name}:")
    for opp in ["Opponent 1", "Opponent 2"]:
        profile = agent.agent._opponent_profiler.get_profile(opp)
        if profile:
            print(f"  {opp}: {profile.profile_type} {profile.aggression_type}")
```

### Example 2: Manually test a decision
```python
from poker.agents import DecisionContext, build_default_agents
import random

agent = build_default_agents()[0]
ctx = DecisionContext(
    hand_strength=0.72,
    to_call=50,
    current_bet=50,
    pot=200,
    min_raise=50,
    stack=1000,
    street="flop",
    community_count=3,
    player_name="Test Agent",
    recent_chat=[],
)

decision = agent.decide(ctx, random.Random())
print(f"Decision: {decision.action} {decision.raise_amount}")
```

### Example 3: Monitor leaks over time
```python
leaks_by_round = []
for round_num in range(1, 51):
    # ... play hand ...
    leaks = agent._leak_detector.detect_leaks()
    leaks_by_round.append((round_num, len(leaks)))

for round_num, leak_count in leaks_by_round:
    print(f"Round {round_num}: {leak_count} active leaks")
```

---

## Key Design Principles

✅ **Simple and readable** - Each tool is understandable  
✅ **Independent** - Tools don't depend on each other  
✅ **Fast** - All run in milliseconds  
✅ **Progressive** - Get smarter as tournament progresses  
✅ **Transparent** - All outputs in LLM prompts  
✅ **Extensible** - Easy to add new tools  

---

## Next Steps

1. **Run your game normally** - Tools work automatically
2. **Read TOOLS_INTEGRATION.md** - Detailed documentation
3. **Run demo_tools.py** - See each tool in action
4. **Experiment** - Try different models, board textures, opponent profiles
5. **Extend** - Add custom tools as needed

---

## Questions?

Refer to:
- **`TOOLS_INTEGRATION.md`** - Full API documentation
- **`demo_tools.py`** - Working code examples
- **`poker/tools.py`** - Source code (well-commented)
- **`poker/agents.py`** - Integration examples

