"""CLI entrypoint for running a five-agent poker tournament."""

from __future__ import annotations

import argparse
import sys

from poker.agents import build_default_agents, build_default_dealer_agent
try:
	from poker.dashboard import PokerResultsDashboard
except Exception:
	PokerResultsDashboard = None
from poker.game import PokerGame

try:
	from poker.ui import PokerTableUI
except Exception:
	PokerTableUI = None


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
		choices=["ask", "live", "replay", "visual", "dashboard"],
		default="ask",
		help="Show hands live line-by-line, replay after tournament, visual table UI, dashboard, or ask at startup",
	)
	parser.add_argument(
		"--play-along",
		choices=["ask", "on", "off"],
		default="ask",
		help="Allow a human seat in the game with hidden opponent cards",
	)
	parser.add_argument(
		"--player-name",
		default="You",
		help="Name used for the human seat in play-along mode",
	)
	parser.add_argument(
		"--step-through",
		choices=["ask", "on", "off"],
		default="ask",
		help="In visual mode, advance hand states using a Next button",
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
		print("Display mode: 1) live line-by-line  2) replay after tournament  3) visual table UI  4) results dashboard")
		answer = input("Choose [1/2/3/4]: ").strip()
		if not answer:
			return default
		if answer == "1":
			return "live"
		if answer == "2":
			return "replay"
		if answer == "3":
			return "visual"
		if answer == "4":
			return "dashboard"
		print("Please enter '1', '2', '3', or '4'.")


def _prompt_play_along(default: bool = False) -> bool:
	return _prompt_yes_no("Enable play-along mode (you take one seat)?", default=default)


def _prompt_step_through(default: bool = True) -> bool:
	return _prompt_yes_no("Enable click-through turn stepping?", default=default)


def resolve_runtime_options(args: argparse.Namespace) -> tuple[bool, str, bool, bool]:
	table_talk = True
	if args.table_talk == "on":
		table_talk = True
	elif args.table_talk == "off":
		table_talk = False
	elif sys.stdin.isatty():
		table_talk = _prompt_yes_no("Enable agent table talk?", default=True)

	display_mode = "live"
	if args.display_mode in {"live", "replay", "visual", "dashboard"}:
		display_mode = args.display_mode
	elif sys.stdin.isatty():
		display_mode = _prompt_display_mode(default="live")

	play_along = False
	if args.play_along == "on":
		play_along = True
	elif args.play_along == "off":
		play_along = False
	elif sys.stdin.isatty():
		play_along = _prompt_play_along(default=False)

	step_through = False
	if args.step_through == "on":
		step_through = True
	elif args.step_through == "off":
		step_through = False
	elif sys.stdin.isatty() and display_mode == "visual":
		step_through = _prompt_step_through(default=True)

	return table_talk, display_mode, play_along, step_through


def main() -> None:
	args = parse_args()
	table_talk, display_mode, play_along, step_through = resolve_runtime_options(args)
	agents = build_default_agents()
	dealer_agent = build_default_dealer_agent()
	if play_along and agents:
		agents[0].name = args.player_name

	table_ui = None
	if display_mode == "visual" and PokerTableUI is not None:
		table_ui = PokerTableUI(title="Gambling.ai Table")
	elif display_mode == "visual" and PokerTableUI is None:
		print("Visual mode unavailable (tkinter missing). Falling back to live mode.")
		display_mode = "live"
	game = PokerGame(
		agents=agents,
		starting_stack=args.starting_stack,
		small_blind=args.small_blind,
		big_blind=args.big_blind,
		seed=args.seed,
		verbose=display_mode not in {"visual", "dashboard"},
		enable_table_talk=table_talk,
		output_mode="live" if display_mode == "visual" else display_mode,
		table_ui=table_ui,
		play_along=play_along,
		human_player_name=args.player_name,
		dealer_agent=dealer_agent,
		step_through=step_through,
	)
	standings = game.play_tournament(rounds=args.rounds)

	if display_mode == "replay":
		replay = game.get_replay_text()
		if replay:
			print("\nTournament Replay")
			print("=" * 40)
			print(replay)

	report = game.get_tournament_report()
	if PokerResultsDashboard is not None:
		try:
			PokerResultsDashboard(report, title="Gambling.ai Tournament Results").show()
		except Exception:
			print("Dashboard UI failed to launch. Results were still collected.")
	else:
		print("Dashboard UI unavailable. Results were still collected.")

	print("\nFinal Standings")
	print("=" * 40)
	for idx, (name, chips) in enumerate(standings, start=1):
		print(f"{idx:>2}. {name:<18} {chips:>6} chips")


if __name__ == "__main__":
	main()