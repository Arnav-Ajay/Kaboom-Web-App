# views.py
import uuid
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.multiplayer.room_store import (
    create_room,
    list_open_rooms,
    get_room,
    join_room,
    leave_room,
    start_game,
)


def ensure_identity():
    """Create a simple per-tab identity using session_state."""
    if "player_id" not in st.session_state:
        st.session_state.player_id = str(uuid.uuid4())
    if "player_name" not in st.session_state:
        st.session_state.player_name = ""
    if "current_room_id" not in st.session_state:
        st.session_state.current_room_id = None
    if "page" not in st.session_state:
        st.session_state.page = "landing"
    if "is_host" not in st.session_state:
        st.session_state.is_host = False


def landing_page():
    st.header("Kaboom 🎮 — Multiplayer Lobby (No Game Yet)")

    ensure_identity()

    st.text_input(
        "Your name",
        key="player_name",
        placeholder="Enter your name",
    )

    if not st.session_state.player_name.strip():
        st.info("Enter your name to create or join a room.")
        st.stop()

    st.markdown("### Create a Room")

    with st.form("create_room_form", clear_on_submit=False):
        room_name = st.text_input(
            "Room name",
            value="Fun Room",
            key="create_room_name",
        )
        max_players = st.slider(
            "Number of players", min_value=2, max_value=6, value=4, key="create_max_players"
        )
        create_submitted = st.form_submit_button("Create & Join Room")

    if create_submitted:
        if not room_name.strip():
            st.warning("Room name cannot be empty.")
        else:
            room_id = create_room(
                room_name=room_name.strip(),
                max_players=max_players,
                host_id=st.session_state.player_id,
                host_name=st.session_state.player_name.strip(),
            )
            st.session_state.current_room_id = room_id
            st.session_state.is_host = True
            st.session_state.page = "lobby"
            st.rerun()

    st.markdown("---")
    st.markdown("### Join an Open Room")

    rooms = list_open_rooms()
    if not rooms:
        st.caption("No open rooms available right now. Create one above!")
    else:
        for room in rooms:
            room_id = room["id"]
            room_name = room.get("room_name", "Unnamed")
            max_players = room.get("max_players", 0)
            players = room.get("players", {}) or {}
            host_name = room.get("host_name", "Host")

            cols = st.columns([3, 2, 2, 2])
            with cols[0]:
                st.markdown(f"**{room_name}**")
                st.caption(f"Host: {host_name}")
            with cols[1]:
                st.write(f"Players: {len(players)}/{max_players}")
            with cols[2]:
                st.caption(f"Room ID: `{room_id[:6]}...`")
            with cols[3]:
                if st.button("Join", key=f"join_{room_id}"):
                    ok = join_room(
                        room_id=room_id,
                        player_id=st.session_state.player_id,
                        player_name=st.session_state.player_name.strip(),
                    )
                    if not ok:
                        st.error("Unable to join room (maybe it's full or already started).")
                    else:
                        st.session_state.current_room_id = room_id
                        st.session_state.is_host = False
                        st.session_state.page = "lobby"
                        st.rerun()


def lobby_page():
    ensure_identity()

    room_id = st.session_state.current_room_id
    if not room_id:
        st.warning("You are not in a room.")
        if st.button("Back to landing"):
            st.session_state.page = "landing"
            st.rerun()
        return

    # Auto-refresh lobby every 2 seconds
    st_autorefresh(interval=2000, key="lobby_autorefresh")

    room = get_room(room_id)
    if not room:
        st.error("Room no longer exists.")
        if st.button("Back to landing"):
            st.session_state.current_room_id = None
            st.session_state.page = "landing"
            st.rerun()
        return

    status = room.get("status", "open")
    room_name = room.get("room_name", "Unnamed Room")
    max_players = room.get("max_players", 0)
    players = room.get("players", {}) or {}
    host_name = room.get("host_name", "Host")

    # If game has started, redirect to game page
    if status == "started":
        st.session_state.page = "game"
        st.rerun()
        return

    st.header(f"Lobby — {room_name}")
    st.caption(f"Room ID: `{room_id}`")
    st.caption(f"Host: **{host_name}**")

    st.markdown("### Players in Room")
    st.write(f"{len(players)}/{max_players} players")

    for pid, pdata in players.items():
        name = pdata.get("name", "Unknown")
        label = name
        if name == host_name:
            label += " 👑 (Host)"
        if pid == st.session_state.player_id:
            label += " (You)"
        st.markdown(f"- {label}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Leave Room"):
            leave_room(room_id, st.session_state.player_id)
            st.session_state.current_room_id = None
            st.session_state.is_host = False
            st.session_state.page = "landing"
            st.rerun()

    with col2:
        # Only host can start the game, and only when room is full
        if st.session_state.is_host:
            can_start = len(players) == max_players
            disabled_text = ""
            if not can_start:
                disabled_text = " (waiting for room to be full)"
            if st.button(f"Start Game{disabled_text}", disabled=not can_start):
                ok = start_game(room_id)
                if not ok:
                    st.error("Cannot start game yet. Room must be full.")
                else:
                    st.success("Game started!")
                    st.session_state.page = "game"
                    st.rerun()
        else:
            st.info("Waiting for host to start the game once the room is full.")


def game_page():
    ensure_identity()

    room_id = st.session_state.current_room_id
    if not room_id:
        st.warning("You are not in a room.")
        if st.button("Back to landing"):
            st.session_state.page = "landing"
            st.rerun()
        return

    room = get_room(room_id)
    if not room:
        st.error("Room no longer exists.")
        if st.button("Back to landing"):
            st.session_state.current_room_id = None
            st.session_state.page = "landing"
            st.rerun()
        return

    status = room.get("status", "open")
    if status != "started":
        # If someone reset the room back or closed it
        st.warning("Game has not started yet or room is no longer active.")
        if st.button("Back to lobby"):
            st.session_state.page = "lobby"
            st.rerun()
        return

    st.header("Kaboom — Game Placeholder")
    st.write(
        "The lobby has successfully transitioned to a started game state.\n\n"
        "This page is just a placeholder. Next step: plug in actual Kaboom game logic here."
    )

    if st.button("Leave Game & Room"):
        leave_room(room_id, st.session_state.player_id)
        st.session_state.current_room_id = None
        st.session_state.is_host = False
        st.session_state.page = "landing"
        st.rerun()
