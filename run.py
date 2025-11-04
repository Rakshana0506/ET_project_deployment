# --- ADD THESE TWO LINES AT THE VERY TOP ---
from dotenv import load_dotenv
load_dotenv() # This loads variables from your .env file into os.environ
# ------------------------------------------

# --- 1. REMOVED OLD API KEY CONFIGURATION ---
# We no longer configure the API key here.
# It is now configured inside callbacks.py using environment variables.

# --- 2. Import App and Layouts ---
from app import app, server # 'server' is crucial for gunicorn
from dash import html, dcc, Input, Output, State

# Import layouts and callbacks
from register import register_layout
from home import home_layout
from login import login_layout
from practice_room import practice_layout
from judge_mode import judge_mode_layout 
from practice_dashboard import practice_dashboard_layout
from judge_dashboard import judge_dashboard_layout
from history import history_layout

# --- NEW: Import the settings layout ---
from settings import settings_layout

import callbacks  # This line IMPORTS and REGISTERS all callbacks

# --- 3. Main App Layout (The "Router") ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    # This stores the active_user, debate_state, chat_history, etc.
    dcc.Store(id='session-storage', storage_type='session'), 
    html.Div(id='page-content')
])

# --- 4. Page Routing & Login-Protection Callback ---
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')],
    [State('session-storage', 'data')]
)
def display_page(pathname, session_data):
    session_data = session_data or {}
    active_user = session_data.get('active_user')

    # Public pages
    if pathname in ['/login', '/register']:
        if active_user:
            return home_layout # Redirect to home if already logged in
        return login_layout if pathname == '/login' else register_layout

    # Protected pages
    if not active_user:
        # If user is not logged in, redirect to login
        return login_layout

    # User is logged in
    if pathname == '/practice':
        return practice_layout
    elif pathname == '/judge':
        return judge_mode_layout
    elif pathname == '/history':
        return history_layout
        
    # --- NEW: Route for the settings page ---
    elif pathname == '/settings':
        return settings_layout
        
    elif pathname == '/practice-results':
        return practice_dashboard_layout
    elif pathname == '/judge-results':
        return judge_dashboard_layout
    
    else:
        # Default to home page for any other path
        return home_layout

# --- 5. Run the App (for Local Development) ---
if __name__ == '__main__':
    # This block is only for running locally (e.g., 'python run.py')
    # Render will use 'gunicorn run:server' instead
    app.run(debug=True, port=8052)