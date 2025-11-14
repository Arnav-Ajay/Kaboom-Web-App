import uuid

import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

from game_state import GameState, create_game_state, deal_initial_hands
from phases import (
    render_game_over,
    render_kaboom,
    render_playing,
    render_pre_peek,
)
from room_store import (
    Room,
    add_player_to_room,
    create_room,
    get_room,
    list_open_rooms,
    mark_room_started,
    persist_room_state,
    remove_player_from_room,
    reset_room,
)

# Auto-refresh the page so every tab stays in sync with the shared room store.
# REFRESH_INTERVAL_MS = 2500


# def _autorefresh(interval_ms: int) -> None:
#     components.html(
#         f"""
#         <script>
#             const interval = {interval_ms};
#             setTimeout(() => window.location.reload(), interval);
#         </script>
#         """,
#         height=0,
#     )


def _ensure_player_identity() -> None:
    st.session_state.setdefault("player_id", str(uuid.uuid4()))
    st.session_state.setdefault("room_id", None)
    st.session_state.setdefault("player_name", "")


def _start_room_game(room: Room) -> bool:
    max_players = room["settings"]["max_players"]
    if len(room["players"]) < max_players:
        return False
    state: GameState = create_game_state(max_players, room["players"])
    deal_initial_hands(state)
    mark_room_started(room["id"], state)
    return True


def render_home_page() -> None:
    st.title("Kaboom 💣 – Card Game")
    st.markdown(
        "Create a room, share the room code, and open the app in another browser to "
        "simulate multiple players. Your display name is remembered once you join."
    )

    create_col, join_col = st.columns(2)
    with create_col:
        st.subheader("Create a room")
        host_name = st.text_input(
            "Your display name",
            value=st.session_state.get("home_host_name", "Host Player"),
            key="home_host_name",
        )
        max_players = st.slider(
            "Players in this room",
            2,
            6,
            value=st.session_state.get("home_max_players", 3),
            key="home_max_players",
        )
        if st.button("Create room"):
            room = create_room(
                host_id=st.session_state.player_id,
                host_name=host_name,
                max_players=max_players,
            )
            st.session_state.player_name = host_name
            st.session_state.room_id = room["id"]
            st.rerun()

    with join_col:
        st.subheader("Join a room")
        open_rooms = list_open_rooms()
        if open_rooms:
            selected_room = st.selectbox(
                "Select open room",
                options=open_rooms,
                format_func=lambda room: f"{room['label']} ({len(room['players'])}/{room['settings']['max_players']})",
                key="home_join_room",
            )
            join_name = st.text_input(
                "Your display name",
                value=st.session_state.get("home_join_name", "Player"),
                key="home_join_name",
            )
            if st.button("Join room"):
                if not join_name.strip():
                    st.warning("Please enter a display name.")
                else:
                    success, message = add_player_to_room(
                        selected_room["id"],
                        st.session_state.player_id,
                        join_name,
                    )
                    if success:
                        st.session_state.player_name = join_name
                        st.session_state.room_id = selected_room["id"]
                        st.rerun()
                    else:
                        st.warning(message)
        else:
            st.info("No open rooms right now.")

    st.caption("Open this app in another browser and join the same room to play together.")


def render_lobby(room: Room) -> None:
    st.title("Kaboom 💣 – Lobby")
    st.subheader(
        f"{room['label']} ({len(room['players'])}/{room['settings']['max_players']})"
    )
    st.caption(f"Room code: {room['id']}")
    st.markdown("### Players")
    for idx, player in enumerate(room["players"], 1):
        tag = " (host)" if player["id"] == room["host_id"] else ""
        st.write(f"{idx}. {player['name']}{tag}")

    is_host = st.session_state.player_id == room["host_id"]
    if is_host:
        remaining = room["settings"]["max_players"] - len(room["players"])
        if remaining > 0:
            st.info(f"Waiting on {remaining} player(s) to fill the room.")
        start_disabled = remaining != 0
        if st.button("Start game", disabled=start_disabled):
            if _start_room_game(room):
                st.rerun()
            else:
                st.warning("Room needs all players present before starting.")
    else:
        st.info("Waiting on the host to start the game.")

    if st.button("Leave room"):
        remove_player_from_room(room["id"], st.session_state.player_id)
        st.session_state.room_id = None
        st.rerun()


def render_room_game(room: Room) -> None:
    state = room.get("game_state")
    if state is None:
        st.warning("Game is initializing…")
        return

    player_id = st.session_state.player_id
    st.title("Kaboom 💣 – Game")
    persist_room_state(room["id"], state)
    st.caption(f"Room code: {room['id']}")
    phase = state["phase"]
    if phase == "pre_peek":
        render_pre_peek(state, player_id)
    elif phase == "playing":
        render_playing(state, player_id)
    elif phase == "kaboom":
        render_kaboom(state, player_id)
    elif phase == "game_over":
        render_game_over(state, player_id)
        if st.button("Return to lobby"):
            reset_room(room["id"])
            st.rerun()
        return
    else:
        st.error(f"Unknown phase: {phase}")

    st.info("Leaving mid-game is disabled. Wait for the current round to finish to exit.")


def main() -> None:
    st.set_page_config(page_title="Kaboom Card Game", page_icon="💣")
    # _autorefresh(REFRESH_INTERVAL_MS)
    st_autorefresh(interval=2000, limit=None, key="kaboom_sync")
    _ensure_player_identity()

    room = get_room(st.session_state.room_id)
    if room is None:
        render_home_page()
        return
    if not room["is_started"]:
        render_lobby(room)
        return

    render_room_game(room)


if __name__ == "__main__":
    main()
