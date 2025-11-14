import streamlit as st

from cards import card_label
from game_state import GameState, award_penalty_card, complete_reaction
from player_utils import find_player


def _player_display_name(player: dict) -> str:
    status = " (inactive)" if not player["active"] else ""
    return f"{player['name']}{status}"


def _format_card_option(idx: int) -> str:
    return f"Card {idx + 1}"


def render_reaction_window(state: GameState, player_id: str) -> None:
    reaction = state["reaction_state"]
    if not reaction:
        return

    rank = reaction["rank"]
    initiator_id = reaction["initiator_id"]
    initiator = find_player(state, initiator_id)

    st.sidebar.warning(
        f"Reaction window open: rank {rank} discarded by {initiator['name'] if initiator else 'a player'}."
    )
    st.subheader("Reaction Window")
    st.caption(
        "Only the eligible player sees the control to discard matching cards."
    )
    st.markdown(f"**Target rank:** {rank}")

    actor = find_player(state, player_id)
    if actor is None or not actor["active"]:
        st.info("You cannot react right now.")
        return
    if actor["id"] == initiator_id:
        st.info("You triggered the reaction and are not eligible to respond.")
        return

    actor_hand = actor["hand"]
    if not actor_hand:
        st.info("You have no cards to react with.")
        if st.button("Skip reaction"):
            complete_reaction(state)
            st.rerun()
        return

    st.markdown(f"Reacting as **{actor['name']}**")
    selected_cards = st.multiselect(
        "Select cards from your hand to discard:",
        options=list(range(len(actor_hand))),
        format_func=_format_card_option,
        key=f"reaction_self_select_{player_id}",
    )

    if st.button("Discard selected cards", key=f"reaction_discard_{player_id}"):
        if not selected_cards:
            st.warning("Select at least one card to discard.")
        else:
            invalid = [idx for idx in selected_cards if actor_hand[idx][0] != rank]
            if invalid:
                idx = invalid[0]
                card = actor_hand.pop(idx)
                state["discard_pile"].append(card)
                st.warning("You discarded a non-matching card and trigger a penalty.")
                award_penalty_card(state, actor["id"])
                return
            for idx in sorted(selected_cards, reverse=True):
                card = actor_hand.pop(idx)
                state["discard_pile"].append(card)
                st.info(
                    f"{actor['name']} matched the rank with {card_label(card)} and discarded it."
                )
            complete_reaction(state)
            st.rerun()
            return

    st.markdown("**Attempt a wrong match (penalty applies)**")
    penalty_idx = st.selectbox(
        "Choose a card to attempt",
        options=list(range(len(actor_hand))),
        format_func=_format_card_option,
        key=f"reaction_penalty_select_{player_id}",
    )
    if st.button("Attempt wrong match", key=f"reaction_penalty_btn_{player_id}"):
        card = actor_hand.pop(penalty_idx)
        state["discard_pile"].append(card)
        award_penalty_card(state, actor["id"])
        return

    st.markdown("**Steal an opponent's matching card**")
    steal_candidates = [
        player
        for player in state["players"]
        if player["id"] != actor["id"]
        and player["active"]
        and any(card[0] == rank for card in player["hand"])
    ]
    if steal_candidates:
        target = st.selectbox(
            "Choose opponent to steal from:",
            options=steal_candidates,
            format_func=_player_display_name,
            key=f"reaction_target_select_{player_id}",
        )
        matching = [
            idx for idx, card in enumerate(target["hand"]) if card[0] == rank
        ]
        if matching:
            target_choice = st.selectbox(
                "Choose which matching card to discard:",
                options=matching,
                format_func=_format_card_option,
                key=f"reaction_target_card_{player_id}",
            )
            give_choice = st.selectbox(
                "Select one of your cards to give away:",
                options=list(range(len(actor_hand))),
                format_func=_format_card_option,
                key=f"reaction_give_card_{player_id}",
            )
            if st.button("Execute steal", key=f"reaction_steal_{player_id}"):
                card_to_discard = target["hand"].pop(target_choice)
                state["discard_pile"].append(card_to_discard)
                given_card = actor_hand.pop(give_choice)
                target["hand"].append(given_card)
                st.info(
                    f"{actor['name']} stole {card_label(card_to_discard)} from {target['name']}."
                )
                complete_reaction(state)
                st.rerun()
                return
        else:
            st.caption("No matching card available from this opponent.")
    else:
        st.caption("No opponents currently have matching cards to steal.")

    if st.button("No match / Continue"):
        complete_reaction(state)
        st.rerun()
