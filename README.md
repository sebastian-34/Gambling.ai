# Multi-Agent Poker Simulation

This project simulates a 5-player Texas Hold'em table where each player is controlled by a different LLM agent.

## New Features (Phase 1)
- Visual table mode with player panels, dealer button, cards, and speech bubbles.
- Optional play-along mode where you take one seat.
- In play-along mode, opponent hole cards are hidden while your cards remain visible.
- You can optionally send a chat line before choosing your action.

## New Features (Phase 2)
- Sixth non-playing dealer agent that validates action legality.
- Dealer commentary on flop, turn, river, and end-of-hand outcomes.
- Physical dealer avatar rendered at the table with a signature hat.
- Distinct visual features per player avatar (different apparel/headwear).
- Click-through stepping mode in visual display so each phase can be advanced with Next.

## Agents
- Llama Agent (`llama3.1:8b` via Microsoft Agent Framework + Ollama)
- Mistral Agent (`mistral:7b` via Microsoft Agent Framework + Ollama)
- Qwen Agent (`qwen2.5:7b` via Microsoft Agent Framework + Ollama)
- Gemma Agent (`gemma2:9b` via Microsoft Agent Framework + Ollama)
- Phi Agent (`phi3:mini` via Microsoft Agent Framework + Ollama)

## LLM Setup

The project will attempt to query local models each betting action using Microsoft Agent Framework clients.


- Run Ollama and make sure models are pulled:
	- `ollama pull llama3.1:8b`
	- `ollama pull mistral:7b`
	- `ollama pull qwen2.5:7b`
	- `ollama pull gemma2:9b`
	- `ollama pull phi3:mini`

If any endpoint or key is unavailable, that agent automatically uses a deterministic fallback policy so the game still runs.

## Run

```bash
python main.py --rounds 25 --seed 42
```

On startup, the app can ask:
- whether agents should use table talk
- whether to show live line-by-line output or a full replay after all hands finish

Optional flags:
- `--starting-stack 1000`
- `--small-blind 5`
- `--big-blind 10`
- `--table-talk ask|on|off`
- `--display-mode ask|live|replay|visual`
- `--play-along ask|on|off`
- `--player-name You`
- `--step-through ask|on|off`

Example (no startup prompts):

```bash
python main.py --table-talk off --display-mode replay --rounds 50
```

Visual play-along example:

```bash
python main.py --display-mode visual --play-along on --player-name You --step-through on --rounds 25
```

## Notes
- Uses Texas Hold'em structure with 2 hole cards per player and 5 shared community cards.
- Includes preflop, flop, turn, and river betting rounds.
- Showdown evaluates each player's best 5-card hand from their 7 available cards.
- Each agent sends JSON action requests through Microsoft Agent Framework clients.
- Agents perform a table-talk phase each street and can react to recent banter in decisions.
- Betting actions are also added into shared chat context to simulate social pressure dynamics.
- Each agent maintains personal context (opponent tendencies, bankroll trend, dialogue impact) and adapts over hands.
- Uses a simplified no-limit betting loop without side-pot handling.
- If a player cannot cover required blind/call/raise amounts, they fold.
