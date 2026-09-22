"""Router: places the logo, defines the app's 3 top-nav pages, and hands off
to st.navigation. All 8 of the original single-purpose page files have now
been deleted -- leagues.py/teams.py/players.py carry their content for real.

streamlit run app/streamlit_app.py
"""

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="footyDB", layout="wide")
# Path(__file__)-relative, not a CWD-relative string -- st.logo/st.image
# resolve a local path via plain os.path.isfile()/open() against the
# process's CWD (unlike st.Page, which resolves relative to this script's
# own directory), so a CWD-relative string breaks -- hard -- if this app is
# ever launched from a different working directory (confirmed live: a wrong
# CWD makes st.logo raise and abort the entire script, no nav, no page,
# nothing). Anchoring to this file's own location removes the hazard
# outright rather than just getting the currently-known launch paths right.
LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"
st.logo(str(LOGO_PATH), size="medium")

# Two CSS-only fixes, scoped tight enough to survive a Streamlit patch
# release without collateral damage -- both confirmed against the actual
# rendered DOM (Streamlit 1.63), not guessed from class names:
#
# 1. Every st.image (crests, flags) gets a hover "fullscreen" toolbar
#    Streamlit adds automatically; dataframes keep theirs (useful there --
#    e.g. the standings table's own search/download toolbar), only image
#    containers are targeted via :has().
# 2. Every @st.dialog(...) call in this app (leagues.py/teams.py/players.py)
#    uses a fixed, generic title ("League detail"/"Team detail"/"Player
#    detail") -- Streamlit's dialog title can't be made dynamic per
#    invocation without restructuring away from the decorator pattern, so
#    the real name renders as a second heading below it. Demoting the fixed
#    title to a small eyebrow label (Hanken Grotesk, uppercase, violet --
#    same treatment the design mockup uses for its own section eyebrows)
#    turns two competing headings into one. Selector is safe because
#    Streamlit's own dialog title is the only <h2> inside
#    [data-testid="stDialog"] -- the `### {name}` heading rendered below it
#    is an <h3>, so this can't collide with page content.
st.markdown(
    f"""
    <style>
    [data-testid="stElementContainer"]:has([data-testid="stImage"])
        [data-testid="stElementToolbar"] {{
        display: none;
    }}
    [data-testid="stDialog"] h2 {{
        font-family: 'Hanken Grotesk', sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {st.get_option("theme.violetColor")};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

pages = [
    st.Page("pages/leagues.py", title="Leagues"),
    st.Page("pages/teams.py", title="Teams"),
    st.Page("pages/players.py", title="Players"),
]
st.navigation(pages, position="top").run()
