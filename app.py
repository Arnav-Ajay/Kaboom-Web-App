import streamlit as st

from src.ui.views import landing_page, lobby_page, game_page


def main() -> None:
    st.set_page_config(page_title="Kaboom Lobby", page_icon="💣")
    if "page" not in st.session_state:
        st.session_state.page = "landing"

    page = st.session_state.page
    if page == "landing":
        landing_page()
    elif page == "lobby":
        lobby_page()
    elif page == "game":
        game_page()
    else:
        st.session_state.page = "landing"
        landing_page()


if __name__ == "__main__":
    main()
