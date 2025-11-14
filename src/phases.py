import streamlit as st

from cards import card_label
from game_state import (
    GameState,
    check_instant_win,
    compute_final_scores,
    draw_from_deck,
    end_game_instant_win,
    trigger_reaction,
)
from player_utils import (
    current_player,
    find_player,
    find_player_index,
    is_my_turn,
)
from reaction_ui import render_reaction_window
from ui_helpers import maybe_reshuffle_info, show_hand_for_owner, show_public_info


def _format_peek_history(state: GameState) -> None:
    if not state["peek_log"]:
        return
    st.markdown("**Peek history**")
    for name, idx, label in state["peek_log"][-5:]:
        st.info(f"{name} peeked at card {idx}: **{label}**")


def render_pre_peek(state: GameState, player_id: str) -> None:
    st.header("Pre-game peek phase")
    peeker_id = state.get("peeking_player_id")
    if peeker_id is None:
        st.warning("No player is scheduled to peek.")
        return
    peeker = find_player(state, peeker_id)
    if not peeker:
        st.warning("Peeking player cannot be found.")
        return

    st.markdown(f"### {peeker['name']}, it's your peek turn")
    used = state["peeks_used"].get(peeker_id, 0)
    st.write(
        "You may look at up to **2** of your own cards. "
        f"You have used {used}/2."
    )

    is_owner = peeker_id == player_id
    max_peeks = 2
    for idx, card in enumerate(peeker["hand"]):
        disabled = not is_owner or used >= max_peeks or (peeker_id, idx) in state["peeked_cards"]
        label = f"Peek card {idx + 1}"
        if st.button(label, key=f"peek_{peeker_id}_{idx}", disabled=disabled):
            state["peeked_cards"].add((peeker_id, idx))
            state["peeks_used"][peeker_id] = state["peeks_used"].get(peeker_id, 0) + 1
            state["peek_log"].append(
                (peeker["name"], idx + 1, card_label(card))
            )
            st.rerun()

    _format_peek_history(state)

    if is_owner and st.button("Done peeking for this player"):
        order_index = find_player_index(state, peeker_id)
        if order_index is None:
            return
        if order_index < len(state["players"]) - 1:
            next_player = state["players"][order_index + 1]
            state["peeking_player_id"] = next_player["id"]
        else:
            state["phase"] = "playing"
        st.rerun()

    if not is_owner:
        st.info(f"Waiting for {peeker['name']} to finish peeking.")


def _render_kaboom_button(state: GameState, player) -> None:
    if player is None or not player["active"]:
        return
    if st.button("Call Kaboom!"):
        state["phase"] = "kaboom"
        state["kaboom_caller_id"] = player["id"]
        player["active"] = False
        player["revealed"] = True
        st.rerun()


def render_playing(state: GameState, player_id: str) -> None:
    st.header("Kaboom - Main Game")

    show_public_info(state)
    maybe_reshuffle_info(state)

    if state["reaction_state"]:
        render_reaction_window(state, player_id)
        return

    player = current_player(state)
    if not player:
        st.error("No active player.")
        return

    show_hand_for_owner(state, player_id, reveal_all=False)

    if player["id"] != player_id:
        st.info(f"Waiting for {player['name']} to take their turn.")
        return

    if state["drawn_card"] is None:
        if st.button("Draw card"):
            state["drawn_card"] = draw_from_deck(state)
            st.rerun()
            return
    else:
        drawn = state["drawn_card"]
        st.info(f"You drew: **{card_label(drawn)}**")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Replace one of your cards**")
            if player["hand"]:
                replace_cols = st.columns(len(player["hand"]))
                for idx, card in enumerate(player["hand"]):
                    with replace_cols[idx]:
                        if st.button(
                            f"Replace card {idx + 1}",
                            key=f"replace_{player_id}_{idx}",
                        ):
                            replaced = player["hand"][idx]
                            state["discard_pile"].append(replaced)
                            player["hand"][idx] = drawn
                            state["drawn_card"] = None
                            trigger_reaction(state, replaced[0], player_id, source="replace")
                            st.rerun()
                            return

        with col2:
            st.markdown("**Discard drawn card**")
            if st.button("Discard card"):
                state["discard_pile"].append(drawn)
                state["drawn_card"] = None
                trigger_reaction(state, drawn[0], player_id, source="discard")
                st.rerun()
                return

    st.markdown("---")
    st.markdown("### Kaboom")
    _render_kaboom_button(state, player)


def render_kaboom(state: GameState, player_id: str) -> None:
    st.header("Kaboom Called!")

    caller_id = state.get("kaboom_caller_id")
    caller = find_player(state, caller_id) if caller_id else None
    if not caller:
        st.warning("Kaboom caller is missing.")
        return

    st.subheader(
        f"{caller['name']} has called Kaboom and is now out of the game."
    )
    st.write("Their cards are revealed:")

    if caller["hand"]:
        cols = st.columns(len(caller["hand"]))
        for idx, card in enumerate(caller["hand"]):
            with cols[idx]:
                st.button(card_label(card), key=f"caller_{caller_id}_{idx}")

    st.write(
        "Each remaining active player gets **one final turn**. "
        "After that, all cards are revealed and the lowest total wins."
    )

    if st.button("Play Final Round (simplified)"):
        compute_final_scores(state)
        state["phase"] = "game_over"
        st.rerun()


def render_game_over(state: GameState, player_id: str) -> None:
    st.header("Game Over")

    winner_id = state.get("instant_winner_id")
    if winner_id:
        winner = find_player(state, winner_id)
        if winner:
            st.subheader(
                f"Instant Win! {winner['name']} reached 0 cards and wins the game!"
            )
        st.write("Final card counts:")
        for player in state["players"]:
            st.write(f"{player['name']}: {len(player['hand'])} cards")
        return

    if not state["final_scores"]:
        compute_final_scores(state)
    st.subheader("Final Scores (lower is better):")
    for rank, (_, name, score) in enumerate(state["final_scores"], start=1):
        st.write(f"{rank}. **{name}** - {score} points")

    if state["final_scores"]:
        best_score = state["final_scores"][0][2]
        winners = [
            name
            for (_, name, score) in state["final_scores"]
            if score == best_score
        ]
        if len(winners) == 1:
            st.success(f"Winner: {winners[0]}")
        else:
            st.warning(f"It's a draw between: {', '.join(winners)}")
