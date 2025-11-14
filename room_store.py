from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

Room = Dict[str, Any]


_ROOM_STORE: Dict[str, Room] = {}


def get_room_store() -> Dict[str, Room]:
    return _ROOM_STORE


def list_open_rooms() -> List[Room]:
    store = get_room_store()
    rooms = [
        room
        for room in store.values()
        if not room["is_started"]
        and len(room["players"]) < room["settings"]["max_players"]
    ]
    return sorted(rooms, key=lambda r: r["created_at"])


def get_room(room_id: str) -> Optional[Room]:
    if not room_id:
        return None
    return get_room_store().get(room_id)


def create_room(host_id: str, host_name: str, max_players: int) -> Room:
    store = get_room_store()
    room_id = str(uuid.uuid4())[:8]
    room: Room = {
        "id": room_id,
        "label": f"Room {room_id}",
        "host_id": host_id,
        "host_name": host_name,
        "settings": {"max_players": max_players},
        "players": [
            {"id": host_id, "name": host_name, "joined_at": time.time()}
        ],
        "is_started": False,
        "game_state": None,
        "created_at": time.time(),
    }
    store[room_id] = room
    return room


def add_player_to_room(
    room_id: str, player_id: str, player_name: str
) -> Tuple[bool, str]:
    room = get_room(room_id)
    if room is None:
        return False, "Selected room no longer exists."
    if room["is_started"]:
        return False, "This room has already started."
    if any(player["id"] == player_id for player in room["players"]):
        return True, "Already joined this room."
    if len(room["players"]) >= room["settings"]["max_players"]:
        return False, "The room is already full."
    room["players"].append(
        {"id": player_id, "name": player_name, "joined_at": time.time()}
    )
    return True, "Joined room."


def remove_player_from_room(room_id: str, player_id: str) -> None:
    room = get_room(room_id)
    if room is None:
        return
    room["players"] = [
        player for player in room["players"] if player["id"] != player_id
    ]
    if not room["players"]:
        get_room_store().pop(room_id, None)
        return
    if room["host_id"] == player_id:
        room["host_id"] = room["players"][0]["id"]
        room["host_name"] = room["players"][0]["name"]


def update_room_label(room_id: str, new_label: str) -> None:
    room = get_room(room_id)
    if room:
        room["label"] = new_label


def mark_room_started(room_id: str, state: Dict[str, Any]) -> None:
    room = get_room(room_id)
    if not room:
        return
    room["game_state"] = state
    room["is_started"] = True


def reset_room(room_id: str) -> None:
    room = get_room(room_id)
    if not room:
        return
    room["game_state"] = None
    room["is_started"] = False
