import streamlit as st
import streamlit.components.v1 as components
from src.ui.views import landing_page, lobby_page, game_page

def main() -> None:
    st.set_page_config(page_title="Kaboom Lobby", page_icon="💣")
    # Inject GA4 script so it's present on every page
    components.html(
        """
        <!-- Google tag (gtag.js) -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-J1BNPF4QCV"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', 'G-J1BNPF4QCV');
        </script>
        """,
        height=0,
    )

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
