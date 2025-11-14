from typing import Any, Dict

import streamlit as st

from cards import card_label
from player_utils import find_player

GameState = Dict[str, Any]


def show_hand_for_owner(
    state: GameState, player_id: str, reveal_all: bool = False
) -> None:
    player = find_player(state, player_id)
    if not player:
        return
    st.write(f"Your cards, {player['name']}:")
    hand = player["hand"]
    cols = st.columns(len(hand) if hand else 1)
    for idx, card in enumerate(hand):
        label = card_label(card) if reveal_all else f"Card {idx + 1} (hidden)"
        with cols[idx]:
            st.button(label, key=f"dummy_show_{player_id}_{idx}")


def show_public_info(state: GameState) -> None:
    st.subheader("Table Status")
    for player in state["players"]:
        status = " (inactive)" if not player["active"] else ""
        st.markdown(f"**{player['name']}**{status} - {len(player['hand'])} card(s)")


def maybe_reshuffle_info(state: GameState) -> None:
    st.caption(
        f"Deck size: {len(state['deck'])} | Discard pile: {len(state['discard_pile'])}"
    )
