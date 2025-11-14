from typing import Any, Dict, List, Optional, Tuple

GameState = Dict[str, Any]


def find_player_index(state: GameState, player_id: str) -> Optional[int]:
    for idx, player in enumerate(state["players"]):
        if player["id"] == player_id:
            return idx
    return None


def find_player(state: GameState, player_id: str) -> Optional[Dict[str, Any]]:
    idx = find_player_index(state, player_id)
    if idx is None:
        return None
    return state["players"][idx]


def current_player(state: GameState) -> Optional[Dict[str, Any]]:
    current_id = state.get("current_player_id")
    if current_id is None:
        return None
    return find_player(state, current_id)


def is_my_turn(state: GameState, player_id: str) -> bool:
    current = current_player(state)
    if current is None:
        return False
    return current["id"] == player_id


def player_order(state: GameState) -> List[Dict[str, Any]]:
    return state["players"]


def get_player_hand(state: GameState, player_id: str) -> Tuple[List[Any], bool]:
    player = find_player(state, player_id)
    if not player:
        return [], False
    return player["hand"], player["revealed"]
