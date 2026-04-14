from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
import random

SUITS = ["S", "H", "D", "C"]
RANKS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]


@dataclass(frozen=True)
class Card:
    rank: int
    suit: str

    def __str__(self) -> str:
        names = {11: "J", 12: "Q", 13: "K", 14: "A"}
        rank = names.get(self.rank, str(self.rank))
        return f"{rank}{self.suit}"


def build_deck() -> list[Card]:
    return [Card(rank, suit) for suit in SUITS for rank in RANKS]


def deal_hand(deck: list[Card], hand_size: int = 5) -> list[Card]:
    hand = deck[:hand_size]
    del deck[:hand_size]
    return hand


def deal_one(deck: list[Card]) -> Card:
    card = deck[0]
    del deck[0]
    return card


def shuffled_deck(rng: random.Random) -> list[Card]:
    deck = build_deck()
    rng.shuffle(deck)
    return deck


def evaluate_five_card_hand(hand: list[Card]) -> tuple[int, tuple[int, ...]]:
    """Return a sortable rank tuple: higher is better.

    Category order:
    8: straight flush
    7: four of a kind
    6: full house
    5: flush
    4: straight
    3: three of a kind
    2: two pair
    1: one pair
    0: high card
    """
    ranks = sorted((card.rank for card in hand), reverse=True)
    suits = [card.suit for card in hand]
    counts = Counter(ranks)
    count_values = sorted(counts.values(), reverse=True)

    # Handle low-ace straight (A,5,4,3,2)
    unique_ranks = sorted(set(ranks), reverse=True)
    is_wheel = unique_ranks == [14, 5, 4, 3, 2]
    is_flush = len(set(suits)) == 1
    is_straight = len(unique_ranks) == 5 and (
        unique_ranks[0] - unique_ranks[-1] == 4 or is_wheel
    )
    straight_high = 5 if is_wheel else unique_ranks[0]

    if is_straight and is_flush:
        return (8, (straight_high,))

    if count_values == [4, 1]:
        four_rank = max(counts, key=lambda r: (counts[r], r))
        kicker = max(r for r in ranks if r != four_rank)
        return (7, (four_rank, kicker))

    if count_values == [3, 2]:
        three_rank = max(r for r, c in counts.items() if c == 3)
        pair_rank = max(r for r, c in counts.items() if c == 2)
        return (6, (three_rank, pair_rank))

    if is_flush:
        return (5, tuple(ranks))

    if is_straight:
        return (4, (straight_high,))

    if count_values == [3, 1, 1]:
        three_rank = max(r for r, c in counts.items() if c == 3)
        kickers = sorted((r for r in ranks if r != three_rank), reverse=True)
        return (3, (three_rank, *kickers))

    if count_values == [2, 2, 1]:
        pairs = sorted((r for r, c in counts.items() if c == 2), reverse=True)
        kicker = max(r for r, c in counts.items() if c == 1)
        return (2, (pairs[0], pairs[1], kicker))

    if count_values == [2, 1, 1, 1]:
        pair_rank = max(r for r, c in counts.items() if c == 2)
        kickers = sorted((r for r in ranks if r != pair_rank), reverse=True)
        return (1, (pair_rank, *kickers))

    return (0, tuple(ranks))


def evaluate_best_hand(cards: list[Card]) -> tuple[int, tuple[int, ...]]:
    """Evaluate the best 5-card hand from a set of 5-7 cards."""
    if len(cards) < 5:
        raise ValueError("Need at least 5 cards to evaluate a poker hand.")

    best: tuple[int, tuple[int, ...]] | None = None
    for combo in combinations(cards, 5):
        score = evaluate_five_card_hand(list(combo))
        if best is None or score > best:
            best = score
    if best is None:
        raise RuntimeError("Failed to evaluate hand combinations.")
    return best


def hand_to_text(hand: list[Card]) -> str:
    return " ".join(str(card) for card in sorted(hand, key=lambda c: c.rank, reverse=True))


def cards_to_text(cards: list[Card]) -> str:
    return " ".join(str(card) for card in cards)
