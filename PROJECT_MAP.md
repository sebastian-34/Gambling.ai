# Project Map

This repository is a five-player Texas Hold'em simulation where each seat is controlled by an LLM-backed poker agent, with deterministic fallback logic when local model access is unavailable.

## File Map

| File | Purpose | How it interacts |
| --- | --- | --- |
| [main.py](main.py) | CLI entrypoint. Parses arguments, resolves startup prompts, builds the default agents, and starts the tournament. | Imports `build_default_agents` from `poker/agents.py` and `PokerGame` from `poker/game.py`. It is the top-level orchestration layer. |
| [README.md](README.md) | User-facing overview and run instructions. | Documents the runtime flags and the model setup expected by `main.py` and the agent layer. |
| [poker/__init__.py](poker/__init__.py) | Package marker and short package description. | Makes `poker` importable as a package. |
| [poker/cards.py](poker/cards.py) | Card model, deck utilities, and hand evaluation logic. | Used by `poker/game.py` to deal cards, format hands, and score showdowns. |
| [poker/agents.py](poker/agents.py) | Agent abstractions, LLM-backed poker agent, fallback policy, and default agent factory. | Used by `main.py` to construct the five seats and by `poker/game.py` for decisions, table talk, and post-hand memory updates. |
| [poker/game.py](poker/game.py) | Core game engine. Handles player state, blinds, betting rounds, table talk, showdowns, tournament progression, and replay logging. | Depends on `poker/cards.py` for all poker math and on `poker/agents.py` for decision-making and dialogue. |

## Runtime Flow

1. `main.py` parses CLI flags such as rounds, stack size, blinds, seed, table talk, and display mode.
2. `main.py` creates five agents with `build_default_agents()`.
3. `PokerGame` is initialized with those agents and the chosen runtime settings.
4. `PokerGame.play_tournament()` loops through hands until the requested rounds finish or a winner is effectively determined.
5. Each hand is handled by `PokerGame.play_round()`, which deals cards, posts blinds, runs betting streets, optionally runs table talk, and resolves the showdown.
6. During each betting decision, the game builds a `DecisionContext` and asks the current agent to choose an action.
7. If the LLM call fails or returns unusable output, the agent falls back to a deterministic policy so the simulation keeps running.

## How The Pieces Fit Together

### `main.py`

This file is only orchestration. It does not know poker rules. Its job is to:

- collect runtime options from the command line or startup prompts
- build the default five agents
- create the `PokerGame`
- run the tournament
- print either a replay or final standings

That keeps CLI concerns separate from game logic.

### `poker/agents.py`

This module defines the decision interface used by the game engine:

- `Decision` represents the result of a betting choice.
- `DecisionContext` packages the facts an agent needs for one turn.
- `PokerAgent` is the abstract base class used by the game engine.
- `LLMPokerAgent` attempts to query a local model through Microsoft Agent Framework and Ollama.
- If the LLM path is unavailable, the fallback logic uses the same context to produce a stable, deterministic-enough action.
- `build_default_agents()` creates the five named models used by the tournament.

This module is the boundary between poker mechanics and model behavior.

### `poker/cards.py`

This module is intentionally pure utility code:

- `Card` models a single playing card.
- `build_deck()`, `shuffled_deck()`, `deal_hand()`, and `deal_one()` handle deck operations.
- `evaluate_five_card_hand()` and `evaluate_best_hand()` score poker hands.
- `hand_to_text()` and `cards_to_text()` format cards for logs and prompts.

The game engine depends on these functions, but this module does not depend on anything else in the repo.

### `poker/game.py`

This is the main simulation engine. It owns:

- player state and chip stacks
- dealer rotation
- blinds and betting rounds
- community card progression through preflop, flop, turn, and river
- showdown resolution
- tournament loop and replay logging

It asks agents what to do, but it enforces the rules. That makes the engine the authority for legal action, pot movement, and winner resolution.

## Important Behavior Notes

- The game expects exactly five agents.
- The betting model is simplified; there is no side-pot handling.
- If a player cannot cover a required blind or call, the current logic may force a fold or sit-out behavior depending on the point in the hand.
- Table talk is woven into the hand state and broadcast back to all agents as shared context.
- Replay mode stores log lines instead of printing them immediately.

## Room For Improvement

1. Add automated tests for hand evaluation, betting edge cases, and showdown resolution.
2. Split `poker/game.py` into smaller units for state management, betting logic, showdown logic, and logging.
3. Add side-pot support so all-in hands resolve correctly.
4. Replace the current string-based event parsing in agents with structured event objects.
5. Add a configuration file or environment-based model registry instead of hard-coding the five default profiles.
6. Separate simulation logging from console output so replay generation, file export, and live UI can evolve independently.
7. Consider caching or batching LLM calls if you want faster tournaments.
8. Add richer statistics tracking across hands, such as VPIP, aggression, fold-to-raise, and showdown frequency.
9. Harden the agent output parsers with clearer validation and retry behavior.
10. Add a small CLI help example set for common tournament modes and replay workflows.

## Suggested Next Step

If you want, the next useful upgrade is a small test suite that covers the poker evaluator and the betting engine first, because those are the parts most likely to break silently.