# room_store.py

from typing import Dict, Any, List, Optional, Tuple
import time
import uuid

Room = Dict[str, Any]

# TRUE GLOBAL SHARED STORE
_ROOM_STORE: Dict[str, Room] = {}


def get_store() -> Dict[str, Room]:
    return _ROOM_STORE


def list_open_rooms() -> List[Room]:
    store = get_store()
    return sorted(
        [
            room for room in store.values()
            if not room["is_started"]
            and len(room["players"]) < room["settings"]["max_players"]
        ],
        key=lambda r: r["created_at"]
    )


def get_room(room_id: str) -> Optional[Room]:
    if not room_id:
        return None
    return get_store().get(room_id)


def create_room(host_id: str, host_name: str, max_players: int) -> Room:
    store = get_store()
    room_id = str(uuid.uuid4())[:8]
    room = {
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


def add_player_to_room(room_id: str, player_id: str, player_name: str) -> Tuple[bool, str]:
    store = get_store()
    room = store.get(room_id)
    if not room:
        return False, "Room does not exist."
    if room["is_started"]:
        return False, "Room already started."
    if any(p["id"] == player_id for p in room["players"]):
        return True, "Already joined."
    if len(room["players"]) >= room["settings"]["max_players"]:
        return False, "Room full."
    room["players"].append(
        {"id": player_id, "name": player_name, "joined_at": time.time()}
    )
    return True, "Joined room."


def mark_room_started(room_id: str, state: Dict[str, Any]) -> None:
    room = get_store().get(room_id)
    if room:
        room["game_state"] = state
        room["is_started"] = True


def persist_room_state(room_id: str, state: Dict[str, Any]) -> None:
    room = get_store().get(room_id)
    if room:
        room["game_state"] = state


def reset_room(room_id: str) -> None:
    room = get_store().get(room_id)
    if room:
        room["is_started"] = False
        room["game_state"] = None


def remove_player_from_room(room_id: str, player_id: str) -> None:
    room = get_store().get(room_id)
    if not room:
        return
    room["players"] = [p for p in room["players"] if p["id"] != player_id]
    if not room["players"]:
        del get_store()[room_id]
    elif room["host_id"] == player_id:
        # reassign host
        room["host_id"] = room["players"][0]["id"]
        room["host_name"] = room["players"][0]["name"]
