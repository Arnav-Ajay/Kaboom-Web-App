from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import streamlit as st

from cards import Card, card_value, create_deck

GameState = Dict[str, Any]


def _default_player_names(players: List[Dict[str, Any]]) -> List[str]:
    return [player["name"] for player in players]


def create_game_state(
    max_players: int, room_players: List[Dict[str, Any]]
) -> GameState:
    players = [
        {
            "id": player["id"],
            "name": player["name"],
            "hand": [],
            "active": True,
            "revealed": False,
        }
        for player in room_players
    ]
    current_player_id = players[0]["id"] if players else None
    return {
        "phase": "setup",
        "num_players": max_players,
        "player_names": _default_player_names(players),
        "players": players,
        "deck": create_deck(),
        "discard_pile": [],
        "current_player_id": current_player_id,
        "drawn_card": None,
        "peeks_used": {player["id"]: 0 for player in players},
        "peeked_cards": set(),
        "peek_log": [],
        "peeking_player_id": current_player_id,
        "kaboom_caller_id": None,
        "final_scores": [],
        "reaction_state": None,
        "instant_winner_id": None,
    }


def init_state(
    state: GameState,
    max_players: int = 2,
    room_players: Optional[List[Dict[str, Any]]] = None,
) -> None:
    state.clear()
    players = room_players or []
    state.update(create_game_state(max_players, players))


def deal_initial_hands(state: GameState) -> None:
    for player in state["players"]:
        hand: List[Card] = []
        for _ in range(4):
            if not state["deck"]:
                state["deck"] = create_deck()
            hand.append(state["deck"].pop())
        player["hand"] = hand
        player["active"] = True
        player["revealed"] = False
    state["phase"] = "pre_peek"
    state["drawn_card"] = None
    state["peek_log"] = []
    state["peeked_cards"] = set()
    state["peeks_used"] = {player["id"]: 0 for player in state["players"]}
    state["kaboom_caller_id"] = None
    state["instant_winner_id"] = None
    first_player = state["players"][0] if state["players"] else None
    state["current_player_id"] = first_player["id"] if first_player else None
    state["peeking_player_id"] = state["current_player_id"]


def draw_from_deck(state: GameState) -> Card:
    if not state["deck"]:
        state["deck"] = create_deck()
    return state["deck"].pop()


def hand_total(hand: List[Card]) -> int:
    return sum(card_value(card) for card in hand)


def check_instant_win(state: GameState) -> Optional[str]:
    for player in state["players"]:
        if player["active"] and len(player["hand"]) == 0:
            return player["id"]
    return None


def end_game_instant_win(state: GameState, winner_id: str) -> None:
    state["phase"] = "game_over"
    state["final_scores"] = []
    state["kaboom_caller_id"] = None
    state["instant_winner_id"] = winner_id


def compute_final_scores(state: GameState) -> None:
    scores = []
    for player in state["players"]:
        total = hand_total(player["hand"])
        scores.append((player["id"], player["name"], total))
    scores.sort(key=lambda item: item[2])
    state["final_scores"] = scores


def advance_turn(state: GameState) -> None:
    if not state["players"]:
        return
    order = state["players"]
    if not any(player["active"] for player in order):
        return
    current_id = state["current_player_id"]
    start_index = 0
    if current_id is not None:
        for idx, player in enumerate(order):
            if player["id"] == current_id:
                start_index = idx
                break
    idx = start_index
    while True:
        idx = (idx + 1) % len(order)
        if order[idx]["active"]:
            state["current_player_id"] = order[idx]["id"]
            break


def trigger_reaction(
    state: GameState,
    rank: str,
    initiator_id: str,
    source: str = "discard",
) -> None:
    state["reaction_state"] = {
        "rank": rank,
        "initiator_id": initiator_id,
        "source": source,
        "pending_action": "advance_turn",
        "timestamp": time.time(),
    }


def complete_reaction(state: GameState) -> None:
    reaction = state["reaction_state"]
    state["reaction_state"] = None
    winner_id = check_instant_win(state)
    if winner_id is not None:
        end_game_instant_win(state, winner_id)
        st.rerun()
        return
    if reaction and reaction.get("pending_action") == "advance_turn":
        advance_turn(state)


def award_penalty_card(state: GameState, player_id: str) -> None:
    penalty_card = draw_from_deck(state)
    target = next(
        (player for player in state["players"] if player["id"] == player_id), None
    )
    if not target:
        return
    target["hand"].append(penalty_card)
    st.warning("Incorrect match! A hidden penalty card was added to your hand.")
    complete_reaction(state)
    st.rerun()
