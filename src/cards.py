import random
from typing import List, Tuple

Card = Tuple[str, str]

RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
SUITS = ['♠', '♥', '♦', '♣']


def create_deck() -> List[Card]:
    deck = [(rank, suit) for rank in RANKS for suit in SUITS]
    random.shuffle(deck)
    return deck


def card_label(card: Card) -> str:
    rank, suit = card
    return f"{rank}{suit}"


def is_red_king(card: Card) -> bool:
    rank, suit = card
    return rank == 'K' and suit in ['♥', '♦']


def card_value(card: Card) -> int:
    if is_red_king(card):
        return 0
    rank, _ = card
    if rank == 'A':
        return 1
    if rank in ['J', 'Q', 'K']:
        return 10
    return int(rank)
