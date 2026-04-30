"""Enhanced dialogue system for realistic, diverse poker table talk."""

from __future__ import annotations

import random
from typing import Any
from dataclasses import dataclass


@dataclass
class DialogueContext:
    hand_strength: float
    to_call: int
    pot: int
    stack: int
    street: str
    position: str  # "button", "sb", "bb", "utg", "co"
    opponent_count: int
    is_aggressor: bool
    just_raised: bool
    bet_size_ratio: float  # bet_size / pot


class PokerDialogueGenerator:
    """Generate diverse, realistic poker table talk based on context."""

    # Confident/Strong hand statements
    CONFIDENT_LINES = [
        "I like this spot.",
        "Feeling strong here.",
        "This is a value bet.",
        "Standard play.",
        "Money goes in good.",
        "I'm comfortable here.",
        "Let's see what you got.",
        "Not folding this.",
        "Pot odds work.",
        "I'm locked in.",
        "Running it twice?",
        "This texture is mine.",
        "Easy decision.",
        "The math is there.",
    ]

    # Cautious/Weak hand statements
    CAUTIOUS_LINES = [
        "Just seeing a card.",
        "Pot committed at this point.",
        "Taking the free card.",
        "Calling down.",
        "Curious.",
        "Can't fold.",
        "Price is right.",
        "Light call.",
        "Playing odds.",
        "Priced in.",
        "Let me see.",
        "Hanging around.",
        "Could go either way.",
        "Got the right odds.",
    ]

    # Pressure/Bluff lines
    PRESSURE_LINES = [
        "You got it?",
        "This is a real hand.",
        "Lot of money to get there.",
        "Not folding.",
        "You playing or folding?",
        "Let's go.",
        "Time is a factor.",
        "What's your play?",
        "Make a decision.",
        "Stack speaks.",
        "Pushing my luck.",
        "All business.",
        "No more free cards.",
        "Enough dancing around.",
    ]

    # Playful/Psychological lines
    PLAYFUL_LINES = [
        "Nice try!",
        "Saw that coming.",
        "You always do that here?",
        "Pattern recognition.",
        "You're too predictable.",
        "Got you tagged.",
        "That's ambitious.",
        "Interesting line.",
        "I respect the aggression.",
        "Bold move.",
        "Mixing it up?",
        "Too obvious.",
        "I've seen this movie.",
        "Time for a new strategy.",
    ]

    # Reaction to others' play
    REACTION_LINES = [
        "Didn't see that coming.",
        "Now that's interesting.",
        "That's spicy.",
        "Respect the ship.",
        "Well played.",
        "Good laydown.",
        "Nice bluff.",
        "Got coolered.",
        "That's a fast call.",
        "Snap call.",
        "Taking time for that?",
        "Interesting timing.",
        "Just lost value.",
        "Could have been bet.",
    ]

    # Banter/Social lines
    BANTER_LINES = [
        "Coffee's getting cold.",
        "Long day?",
        "How's the run?",
        "Variance is a grind.",
        "Just happy to be here.",
        "Keeping score?",
        "Next hand is mine.",
        "Coolers only.",
        "One outer.",
        "Bad luck, my friend.",
        "That's poker.",
        "Happens to the best of us.",
        "Brutal runout.",
        "Ship it.",
    ]

    # Short acknowledgments
    ACKNOWLEDGMENT_LINES = [
        "Check.",
        "Call.",
        "Fold.",
        "Raise.",
        "All in.",
        "Yep.",
        "Yeah.",
        "Sure.",
        "Okay.",
        "Fine.",
        "Whatever.",
        "You got me.",
        "Fair point.",
        "That's fair.",
    ]

    # Board texture comments
    TEXTURE_COMMENTS = [
        "Connects a lot of hands.",
        "Pretty dry.",
        "Tons of outs.",
        "No draws.",
        "Tons of draws.",
        "Two-tone.",
        "Paired.",
        "Back door possibilities.",
        "Texture favors aggression.",
        "Texture favors caution.",
        "Perfect for my range.",
        "Doesn't hit my range.",
        "Wide open.",
        "Very narrow.",
    ]

    # Stack-related comments
    STACK_LINES = [
        "Getting short.",
        "Comfortable.",
        "Middle of the pack.",
        "Short and mean.",
        "Chip leader stuff.",
        "Back in it.",
        "Still alive.",
        "Glass Joe.",
        "Moving up.",
        "Moving down.",
        "Grinding it out.",
        "Stalling out.",
        "All or nothing.",
        "Survival mode.",
    ]

    @staticmethod
    def generate_dialogue(ctx: DialogueContext, seed: int | None = None) -> str:
        """Generate realistic poker dialogue based on context.
        
        Args:
            ctx: DialogueContext with game state
            seed: Optional seed for reproducibility
        
        Returns:
            A poker table dialogue line
        """
        if seed is not None:
            rng = random.Random(seed)
        else:
            rng = random.Random()

        # Silence check - sometimes the best line is no line
        if rng.random() < 0.25:
            return ""

        # Select category based on context
        if ctx.street == "river" and ctx.to_call > 0 and ctx.to_call >= ctx.stack * 0.5:
            # High pressure river
            return rng.choice(PokerDialogueGenerator.PRESSURE_LINES)

        if ctx.hand_strength > 0.75:
            # Strong hand
            if ctx.is_aggressor:
                options = (
                    PokerDialogueGenerator.CONFIDENT_LINES +
                    PokerDialogueGenerator.PRESSURE_LINES
                )
                return rng.choice(options)
            else:
                return rng.choice(PokerDialogueGenerator.CONFIDENT_LINES)

        if ctx.hand_strength < 0.35 and ctx.to_call > 0:
            # Weak hand facing bet
            if ctx.bet_size_ratio > 2.0:
                # Large bet
                return rng.choice(
                    PokerDialogueGenerator.PRESSURE_LINES +
                    PokerDialogueGenerator.PLAYFUL_LINES
                )
            else:
                # Normal bet
                return rng.choice(PokerDialogueGenerator.CAUTIOUS_LINES)

        # Marginal/balanced hand
        if ctx.street in ["flop", "turn"] and ctx.opponent_count >= 3:
            # Multiway pots
            return rng.choice(PokerDialogueGenerator.TEXTURE_COMMENTS)

        if rng.random() < 0.3:
            # Social/banter
            return rng.choice(PokerDialogueGenerator.BANTER_LINES)

        if rng.random() < 0.5:
            # React to situation
            return rng.choice(PokerDialogueGenerator.REACTION_LINES)

        # Default to acknowledging
        return rng.choice(PokerDialogueGenerator.ACKNOWLEDGMENT_LINES)

    @staticmethod
    def generate_multiple_dialogues(
        ctx: DialogueContext,
        num_options: int = 3,
    ) -> list[str]:
        """Generate multiple dialogue options to choose from.
        
        Args:
            ctx: DialogueContext with game state
            num_options: Number of options to generate
        
        Returns:
            List of dialogue options
        """
        dialogues = set()
        attempts = 0
        max_attempts = 100

        while len(dialogues) < num_options and attempts < max_attempts:
            dialogue = PokerDialogueGenerator.generate_dialogue(ctx, seed=random.randint(0, 10000))
            if dialogue:
                dialogues.add(dialogue)
            attempts += 1

        return sorted(list(dialogues))[:num_options]
