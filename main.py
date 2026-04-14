"""CLI entrypoint for running a five-agent poker tournament."""

from __future__ import annotations

import argparse
import sys

from poker.agents import build_default_agents
from poker.game import PokerGame


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Run a Texas Hold'em simulation where five AI agents compete."
	)
	parser.add_argument("--rounds", type=int, default=25, help="Number of hands to play")
	parser.add_argument("--starting-stack", type=int, default=1000, help="Starting chips")
	parser.add_argument("--small-blind", type=int, default=5, help="Small blind amount")
	parser.add_argument("--big-blind", type=int, default=10, help="Big blind amount")
	parser.add_argument("--seed", type=int, default=None, help="Random seed")
	parser.add_argument(
		"--table-talk",
		choices=["ask", "on", "off"],
		default="ask",
		help="Enable agent banter (on/off) or ask at startup",
	)
	parser.add_argument(
		"--display-mode",
		choices=["ask", "live", "replay"],
		default="ask",
		help="Show hands live line-by-line, replay after tournament, or ask at startup",
	)
	return parser.parse_args()


def _prompt_yes_no(question: str, default: bool) -> bool:
	default_hint = "Y/n" if default else "y/N"
	while True:
		answer = input(f"{question} [{default_hint}]: ").strip().lower()
		if not answer:
			return default
		if answer in {"y", "yes"}:
			return True
		if answer in {"n", "no"}:
			return False
		print("Please answer with 'y' or 'n'.")


def _prompt_display_mode(default: str = "live") -> str:
	while True:
		print("Display mode: 1) live line-by-line  2) replay full games after tournament")
		answer = input("Choose [1/2]: ").strip()
		if not answer:
			return default
		if answer == "1":
			return "live"
		if answer == "2":
			return "replay"
		print("Please enter '1' or '2'.")


def resolve_runtime_options(args: argparse.Namespace) -> tuple[bool, str]:
	table_talk = True
	if args.table_talk == "on":
		table_talk = True
	elif args.table_talk == "off":
		table_talk = False
	elif sys.stdin.isatty():
		table_talk = _prompt_yes_no("Enable agent table talk?", default=True)

	display_mode = "live"
	if args.display_mode in {"live", "replay"}:
		display_mode = args.display_mode
	elif sys.stdin.isatty():
		display_mode = _prompt_display_mode(default="live")

	return table_talk, display_mode


def main() -> None:
	args = parse_args()
	table_talk, display_mode = resolve_runtime_options(args)
	agents = build_default_agents()
	game = PokerGame(
		agents=agents,
		starting_stack=args.starting_stack,
		small_blind=args.small_blind,
		big_blind=args.big_blind,
		seed=args.seed,
		verbose=True,
		enable_table_talk=table_talk,
		output_mode=display_mode,
	)
	standings = game.play_tournament(rounds=args.rounds)

	if display_mode == "replay":
		replay = game.get_replay_text()
		if replay:
			print("\nTournament Replay")
			print("=" * 40)
			print(replay)

	print("\nFinal Standings")
	print("=" * 40)
	for idx, (name, chips) in enumerate(standings, start=1):
		print(f"{idx:>2}. {name:<18} {chips:>6} chips")


if __name__ == "__main__":
	main()