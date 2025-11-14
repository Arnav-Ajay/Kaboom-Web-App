# room_store.py
from typing import Any, Dict, List, Optional

from firebase_client import fb_get, fb_patch, fb_post, fb_put, current_timestamp


# Data model (stored under /rooms/<room_id> in RTDB)
# {
#   "room_name": str,
#   "max_players": int,
#   "status": "open" | "started" | "closed",
#   "host_name": str,
#   "created_at": float (timestamp),
#   "players": {
#       "<player_id>": {
#           "name": str,
#           "joined_at": float
#       },
#       ...
#   }
# }


def create_room(room_name: str, max_players: int, host_id: str, host_name: str) -> str:
    data = {
        "room_name": room_name,
        "max_players": max_players,
        "status": "open",
        "host_name": host_name,
        "created_at": current_timestamp(),
        "players": {
            host_id: {
                "name": host_name,
                "joined_at": current_timestamp(),
            }
        },
    }
    room_id = fb_post("/rooms", data)
    return room_id


def get_room(room_id: str) -> Optional[Dict[str, Any]]:
    room = fb_get(f"/rooms/{room_id}")
    return room


def list_open_rooms() -> List[Dict[str, Any]]:
    """
    Returns list like:
    [
      {"id": "<room_id>", "room_name": ..., "max_players": ..., "status": ..., "players": {...}},
      ...
    ]
    """
    rooms = fb_get("/rooms") or {}
    result = []
    for room_id, room in rooms.items():
        if not room:
            continue
        status = room.get("status", "open")
        players = room.get("players", {}) or {}
        max_players = room.get("max_players", 0)
        # Show rooms that are still open and not full
        if status == "open" and len(players) < max_players:
            result.append(
                {
                    "id": room_id,
                    **room,
                }
            )
    # Sort by created_at (oldest first)
    result.sort(key=lambda r: r.get("created_at", 0.0))
    return result


def join_room(room_id: str, player_id: str, player_name: str) -> bool:
    room = get_room(room_id)
    if not room:
        return False

    status = room.get("status", "open")
    if status != "open":
        return False

    players = room.get("players", {}) or {}
    max_players = room.get("max_players", 0)

    # Already in room?
    if player_id in players:
        return True

    if len(players) >= max_players:
        return False

    players[player_id] = {
        "name": player_name,
        "joined_at": current_timestamp(),
    }
    fb_put(f"/rooms/{room_id}/players", players)
    return True


def leave_room(room_id: str, player_id: str) -> None:
    room = get_room(room_id)
    if not room:
        return
    players = room.get("players", {}) or {}
    if player_id in players:
        del players[player_id]
        fb_put(f"/rooms/{room_id}/players", players)

    # If room becomes empty, close it
    if not players:
        fb_patch(f"/rooms/{room_id}", {"status": "closed"})


def start_game(room_id: str) -> bool:
    room = get_room(room_id)
    if not room:
        return False

    players = room.get("players", {}) or {}
    max_players = room.get("max_players", 0)

    # Only start when room is full
    if len(players) < max_players:
        return False

    fb_patch(
        f"/rooms/{room_id}",
        {
            "status": "started",
            "started_at": current_timestamp(),
        },
    )
    return True
