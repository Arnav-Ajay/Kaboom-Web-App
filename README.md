# Kaboom Multiplayer Card Game

This project is a Streamlit-based multiplayer version of the classic **Kaboom** memory card game. Players join a shared room (via the host), take turns peeking at cards, swapping and discarding, and then call “Kaboom” when they believe an opponent is vulnerable. Reactions, peeks, and the final showdown are all managed through a shared room state so multiple browser sessions can act as different players.

## Key files

- `src/kaboom_app.py`: Streamlit entry point that presents the landing page, lobby, and routed gameplay phases.
- `src/room_store.py`: In-memory (pickle-backed) room store so every user sees the same lobby and game state.
- `src/game_state.py`: Core game logic (deck, hands, phases, reactions) wired to player IDs.
- `src/phases.py`, `src/reaction_ui.py`, `src/ui_helpers.py`: UI helpers that respect per-player views, peek limits, and reaction gating.
- `src/cards.py`: Card utilities and deck generation, used across the game logic.

## How to run

1. Activate the Python environment (`venv`).
2. Install dependencies listed in `requirements.txt` (if you add one) or run `pip install streamlit`.
3. Launch the app:  
   ```bash
   streamlit run src/kaboom_app.py
   ```
4. Open the URL in two different browsers (or use an incognito window) and use the landing page to create/join the same room.

## Gameplay overview

1. **Room creation** – A player becomes host, chooses the number of players, and shares the room code.
2. **Lobby** – Each joining player sets a display name. The host sees the full list and can start once the room is full.
3. **Peeking** – Each player peeks at up to two cards on their turn before the main round. Others only watch.
4. **Main play** – The current player draws, can replace or discard, and every action triggers the shared reaction window so other players may respond (including the discarder, to match Kaboom rules).
5. **Kaboom & scoring** – A player may call Kaboom to end the round; the final scoring logic runs and displays the winner.

## Notes

- The shared room store writes every state change to disk, so new browser tabs immediately read the latest lobby.
- Hands remain hidden except when peeking; even the active player only sees placeholders once the main phase begins, preserving the memory challenge.
- Leaving mid-game is disabled to keep the turn order stable.

Feel free to expand by adding persistence, better draw animations, or a waitlist for additional players.
