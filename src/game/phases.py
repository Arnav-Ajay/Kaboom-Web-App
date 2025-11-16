# src/game/phases.py

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.firebase import fb_get, fb_put
from src.game.cards import Card, card_label
from src.game.game_state import (
    GameState,
    create_game_state,
    deal_initial_hands,
    draw_from_deck,
    check_instant_win,
    end_game_instant_win,
    compute_final_scores,
    advance_turn,
)

# ---------- Firebase helpers ----------


def _game_state_path(room_id: str) -> str:
    return f"/rooms/{room_id}/game_state"


def load_game_state(room_id: str) -> Optional[GameState]:
    data = fb_get(_game_state_path(room_id))
    return data or None


def save_game_state(room_id: str, state: GameState) -> None:
    fb_put(_game_state_path(room_id), state)


def _load_room(room_id: str) -> Optional[Dict[str, Any]]:
    return fb_get(f"/rooms/{room_id}")


def _room_players_list(room: Dict[str, Any]) -> List[Dict[str, Any]]:
    players = room.get("players", {}) or {}
    room_players = []
    for pid, pdata in players.items():
        room_players.append(
            {
                "id": pid,
                "name": pdata.get("name", "Player"),
            }
        )
    return room_players


def ensure_game_state(room_id: str) -> Optional[GameState]:
    """
    Load existing GameState from Firebase, or create + deal hands if missing.
    Also ensures peek-related helpers exist.
    """
    state = load_game_state(room_id)
    if state:
        # Backwards-compatibility: ensure peek helpers exist
        if "peek_ready" not in state:
            state["peek_ready"] = {p["id"]: False for p in state["players"]}
        if "peeks_used" not in state:
            state["peeks_used"] = {p["id"]: 0 for p in state["players"]}
        return state

    room = _load_room(room_id)
    if not room:
        return None

    room_players = _room_players_list(room)
    if not room_players:
        return None

    max_players = room.get("max_players", len(room_players))
    state = create_game_state(max_players=max_players, room_players=room_players)
    deal_initial_hands(state)

    # Simultaneous peek-phase helpers
    state["peek_ready"] = {p["id"]: False for p in state["players"]}
    state["peeks_used"] = {p["id"]: 0 for p in state["players"]}

    save_game_state(room_id, state)
    return state


# ---------- Layout helpers (radial board) ----------

POSITIONS_BY_N = {
    2: ["top", "bottom"],
    3: ["top", "bottom_left", "bottom_right"],
    4: ["top", "left", "bottom", "right"],
    5: ["top", "top_left", "bottom_left", "bottom", "bottom_right"],
    6: ["top", "top_left", "bottom_left", "bottom", "bottom_right", "top_right"],
}

GRID_SLOTS = {
    "top_left": (0, 0),
    "top": (0, 1),
    "top_right": (0, 2),
    "left": (1, 0),
    "center": (1, 1),
    "right": (1, 2),
    "bottom_left": (2, 0),
    "bottom": (2, 1),
    "bottom_right": (2, 2),
}


def _get_viewer_id() -> Optional[str]:
    return st.session_state.get("player_id")


def _get_player_index_by_id(state: GameState, player_id: str) -> Optional[int]:
    for idx, player in enumerate(state["players"]):
        if player["id"] == player_id:
            return idx
    return None


def _get_perspective_order(state: GameState, viewer_id: Optional[str]) -> List[int]:
    """
    Returns list of indices into state["players"], starting from viewer on top,
    then clockwise.
    """
    n = len(state["players"])
    if n == 0:
        return []

    start_idx = 0
    if viewer_id:
        idx = _get_player_index_by_id(state, viewer_id)
        if idx is not None:
            start_idx = idx

    order: List[int] = []
    for i in range(n):
        order.append((start_idx + i) % n)
    return order


def _render_center_piles(state: GameState) -> None:
    deck_size = len(state.get("deck", []))
    st.markdown("### Center")
    st.write(f"Deck: **{deck_size}** cards remaining")

    discard = state.get("discard_pile", []) or []
    if discard:
        top_card: Card = discard[-1]
        st.write(f"Discard top: **{card_label(top_card)}**")
    else:
        st.write("Discard pile: *(empty)*")


def _render_player_box(
    state: GameState,
    player_idx: int,
    viewer_id: Optional[str],
    phase: str,
    room_id: str,
) -> None:
    """
    Renders a single player's panel in the radial layout.

    Peek Phase behavior:
    - All players see all cards face-down.
    - ONLY the viewer's 4 cards are clickable (peek up to 2).
    - Viewer also gets an "I'm ready" button under their cards.
    """
    player = state["players"][player_idx]
    name = player["name"]
    pid = player["id"]

    is_viewer = viewer_id == pid
    is_current = state.get("current_player_id") == pid
    active = player.get("active", True)

    label = name
    if is_viewer:
        label += " (You)"
    if not active:
        label += " (out)"

    badge = ""
    if is_current and phase == "playing":
        badge = " — Your turn"

    # Highlight current player during main game
    if is_current and phase == "playing":
        st.markdown(
            "<div style='border:2px solid #f39c12; border-radius:8px; padding:4px;'>",
            unsafe_allow_html=True,
        )

    st.markdown(f"**{label}{badge}**")

    # Safety: ensure helpers exist
    if "peeks_used" not in state:
        state["peeks_used"] = {p["id"]: 0 for p in state["players"]}
    if "peek_ready" not in state:
        state["peek_ready"] = {p["id"]: False for p in state["players"]}

    hand = player.get("hand", [])
    cols = st.columns(len(hand)) if hand else []

    for i, card in enumerate(hand):
        with cols[i]:
            if phase == "pre_peek":
                if is_viewer:
                    # Your 4 cards are clickable, up to 2 peeks
                    used = state["peeks_used"].get(pid, 0)
                    disabled = used >= 2
                    if st.button(
                        f"Card {i + 1}",
                        key=f"peek_card_button_{pid}_{i}",
                        disabled=disabled,
                    ):
                        st.info(f"Card {i + 1}: **{card_label(card)}**")
                        state["peeks_used"][pid] = used + 1
                        save_game_state(room_id, state)
                        st.rerun()
                else:
                    # Other players' cards: visible as face-down but not clickable
                    st.button(
                        f"Card {i + 1}",
                        key=f"card_{pid}_{i}",
                        disabled=True,
                    )
            else:
                # Non-peek phases: all cards are just face-down placeholders here
                st.button(
                    f"Card {i + 1}",
                    key=f"card_{pid}_{i}",
                    disabled=True,
                )

    # Under YOUR cards: Ready button in peek phase
    if phase == "pre_peek" and is_viewer:
        used = state["peeks_used"].get(pid, 0)
        ready = state["peek_ready"].get(pid, False)
        st.caption(f"Peek used: **{used}/2**")

        if not ready:
            if st.button("I'm ready (done peeking)", key=f"peek_ready_{pid}"):
                state["peek_ready"][pid] = True
                save_game_state(room_id, state)
                st.rerun()
        else:
            st.success("You are ready! Waiting for other players…")

    if is_current and phase == "playing":
        st.markdown("</div>", unsafe_allow_html=True)


def render_board_layout(state: GameState, phase: str, room_id: str) -> None:
    """
    Render the geometric layout for all players + center piles.
    """
    viewer_id = _get_viewer_id()
    players = state.get("players", [])
    n = len(players)
    if n == 0:
        st.warning("No players in this game.")
        return

    positions = POSITIONS_BY_N.get(n)
    if not positions:
        st.error(f"Board layout not defined for {n} players.")
        return

    order = _get_perspective_order(state, viewer_id)
    player_pos: Dict[int, str] = {}
    for idx, pos in zip(order, positions):
        player_pos[idx] = pos

    # 3x3 grid
    rows = [
        st.columns(3),
        st.columns(3),
        st.columns(3),
    ]

    # Place players
    for p_idx in order:
        pos_name = player_pos[p_idx]
        if pos_name == "center":
            continue
        r, c = GRID_SLOTS[pos_name]
        with rows[r][c]:
            _render_player_box(state, p_idx, viewer_id, phase, room_id)

    # Center cell: deck + discard
    r, c = GRID_SLOTS["center"]
    with rows[r][c]:
        _render_center_piles(state)


# ---------- Peek phase (simultaneous) ----------


def render_pre_peek(state: GameState, room_id: str) -> None:
    """
    Simultaneous peek phase:

    - All players see full board with all cards face-down.
    - Each player can click ONLY their own 4 cards (up to 2 peeks).
    - Each player has an "I'm ready" button under their own cards.
    - Game advances to 'playing' only when EVERY player is ready.
    - No auto-refresh here, to avoid constant flicker/lag.
    """
    st.header("Kaboom — Peek Phase")

    # Ensure helper structures exist
    if "peek_ready" not in state:
        state["peek_ready"] = {p["id"]: False for p in state["players"]}
    if "peeks_used" not in state:
        state["peeks_used"] = {p["id"]: 0 for p in state["players"]}
    save_game_state(room_id, state)

    viewer_id = _get_viewer_id()
    if not viewer_id:
        st.warning("You are not recognized as a player in this room.")
        return

    st.info(
        "Peek Phase: You may click **up to 2** of your own face-down cards to see them "
        "temporarily. When you're done, click **\"I'm ready (done peeking)\"** under "
        "your cards. The game will start once **everyone** is ready."
    )

    # Main layout: all cards face-down, only your four clickable
    render_board_layout(state, phase="pre_peek", room_id=room_id)

    # Ready summary
    total_players = len(state["players"])
    ready_count = sum(1 for p in state["players"] if state["peek_ready"].get(p["id"]))
    st.markdown("---")
    st.caption(f"Ready players: **{ready_count}/{total_players}**")

    # Transition to playing when ALL ready
    all_ready = all(
        state["peek_ready"].get(p["id"], False) for p in state["players"]
    )
    if all_ready:
        state["phase"] = "playing"
        save_game_state(room_id, state)
        st.rerun()


# ---------- Main playing phase ----------


def _render_kaboom_button(state: GameState, room_id: str) -> None:
    viewer_id = _get_viewer_id()
    current_id = state.get("current_player_id")
    if not viewer_id or viewer_id != current_id:
        return

    if st.button("Call Kaboom!"):
        state["phase"] = "kaboom"
        state["kaboom_caller_id"] = viewer_id
        # Mark caller as out & revealed
        for p in state["players"]:
            if p["id"] == viewer_id:
                p["active"] = False
                p["revealed"] = True
                break
        save_game_state(room_id, state)
        st.rerun()


def render_playing(state: GameState, room_id: str) -> None:
    st.header("Kaboom — Main Game")

    render_board_layout(state, phase="playing", room_id=room_id)

    viewer_id = _get_viewer_id()
    players = state.get("players", [])

    # Winner check (instant 0 cards)
    winner_id = check_instant_win(state)
    if winner_id is not None:
        end_game_instant_win(state, winner_id)
        save_game_state(room_id, state)
        st.rerun()
        return

    current_id = state.get("current_player_id")
    current_player = next((p for p in players if p["id"] == current_id), None)

    if not current_player:
        st.error("Current player not found.")
        return

    if viewer_id != current_id:
        st.subheader(f"It is {current_player['name']}'s turn.")
        _render_kaboom_button(state, room_id)
        return

    # This is the current viewer's turn
    st.subheader("Your turn")

    drawn = state.get("drawn_card")

    if drawn is None:
        if st.button("Draw card"):
            state["drawn_card"] = draw_from_deck(state)
            save_game_state(room_id, state)
            st.rerun()
            return
    else:
        st.info(f"You drew: **{card_label(drawn)}**")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Replace one of your cards**")
            hand: List[Card] = current_player.get("hand", [])
            if hand:
                replace_cols = st.columns(len(hand))
                for i, _card in enumerate(hand):
                    with replace_cols[i]:
                        if st.button(
                            f"Replace card {i + 1}",
                            key=f"replace_{current_id}_{i}",
                        ):
                            replaced = hand[i]
                            state.setdefault("discard_pile", []).append(replaced)
                            hand[i] = drawn
                            state["drawn_card"] = None
                            advance_turn(state)
                            save_game_state(room_id, state)
                            st.rerun()
                            return

        with col2:
            st.markdown("**Discard drawn card**")
            if st.button("Discard card"):
                state.setdefault("discard_pile", []).append(drawn)
                state["drawn_card"] = None
                advance_turn(state)
                save_game_state(room_id, state)
                st.rerun()
                return

    st.markdown("---")
    st.markdown("### Kaboom")
    _render_kaboom_button(state, room_id)


# ---------- Kaboom & Game over (simplified) ----------


def render_kaboom(state: GameState, room_id: str) -> None:
    st.header("Kaboom Called!")

    caller_id = state.get("kaboom_caller_id")
    caller = next((p for p in state["players"] if p["id"] == caller_id), None)

    if caller:
        st.subheader(f"{caller['name']} has called Kaboom and is now out of the game.")
        st.write("Their cards are revealed:")

        hand: List[Card] = caller.get("hand", [])
        if hand:
            cols = st.columns(len(hand))
            for i, card in enumerate(hand):
                with cols[i]:
                    st.button(card_label(card), key=f"caller_{caller_id}_{i}")
        else:
            st.caption("Caller has no cards.")
    else:
        st.warning("Kaboom caller not found.")

    st.write(
        "Simplified implementation: we skip the full final-round logic and go "
        "directly to final scoring when any player clicks the button below."
    )

    if st.button("Compute Final Scores"):
        compute_final_scores(state)
        state["phase"] = "game_over"
        save_game_state(room_id, state)
        st.rerun()


def render_game_over(state: GameState, room_id: str) -> None:
    st.header("Game Over")

    instant_winner_id = state.get("instant_winner_id")
    players = state.get("players", [])

    if instant_winner_id is not None:
        winner = next((p for p in players if p["id"] == instant_winner_id), None)
        if winner:
            st.subheader(
                f"Instant Win! {winner['name']} reached 0 cards and wins the game!"
            )
        else:
            st.subheader("Instant Win (winner not found in player list).")

        st.write("Final card counts:")
        for player in players:
            st.write(f"{player['name']}: {len(player.get('hand', []))} cards")
    else:
        if not state.get("final_scores"):
            compute_final_scores(state)
            save_game_state(room_id, state)

        st.subheader("Final Scores (lower is better):")
        for rank, (pid, name, score) in enumerate(state["final_scores"], start=1):
            st.write(f"{rank}. **{name}** — {score} points")

        if state.get("final_scores"):
            best_score = state["final_scores"][0][2]
            winners = [
                name
                for _, name, score in state["final_scores"]
                if score == best_score
            ]
            if len(winners) == 1:
                st.success(f"Winner: {winners[0]}")
            else:
                st.warning(f"It's a draw between: {', '.join(winners)}")

    st.markdown("---")
    st.caption("To play again, the host can create a new room from the landing page.")


# ---------- Top-level entry for game_page() ----------


def render_room_game(room_id: str) -> None:
    """
    Main entry point for the game screen.
    - Loads room & game_state from Firebase
    - Auto-refreshes every 2 seconds ONLY after peek phase
    - Routes to the correct phase renderer
    """
    room = _load_room(room_id)
    if not room:
        st.error("Room no longer exists.")
        return

    status = room.get("status", "open")
    if status != "started":
        st.warning("Game has not started yet or room is no longer active.")
        return

    state = ensure_game_state(room_id)
    if not state:
        st.error("Unable to initialize game state.")
        return

    phase = state.get("phase", "pre_peek")

    # 🔄 Auto-refresh ONLY after peek, for live turns/reactions
    if phase != "pre_peek":
        st_autorefresh(interval=2000, key=f"game_autorefresh_{room_id}")

    if phase == "pre_peek":
        render_pre_peek(state, room_id)
    elif phase == "playing":
        render_playing(state, room_id)
    elif phase == "kaboom":
        render_kaboom(state, room_id)
    elif phase == "game_over":
        render_game_over(state, room_id)
    else:
        st.error(f"Unknown game phase: {phase}")