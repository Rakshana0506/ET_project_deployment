from dash import html
from components import header

# This layout now uses the corrected structure for proper centering
home_layout = html.Div(className='layout-wrapper', children=[
    header,
    html.Div(className='main-container', children=[
        html.Div(className='card', children=[
            # This H2's content is set by the show_welcome callback in callbacks.py
            html.H2(id='home-welcome-message'),

            # This empty Div will be filled by the callback if keys are missing
            html.Div(id='api-key-warning-container'),

            # --- NEW: STATIC FRIENDLY INSTRUCTION ---
            # This message will ALWAYS be here.
            html.P(
                "Please visit Settings to add your API keys and avoid any interruptions during your debate sessions.",
                className='home-ps-message'
            ),
            # --- END OF ADDITION ---

            # These buttons trigger navigation in callbacks.py
            html.Button('Practice Mode', id='practice-mode-button', n_clicks=0, className='btn btn-primary'),
            html.Button('Judge Mode', id='judge-mode-button', n_clicks=0, className='btn btn-secondary'),
            html.Button('View Debate History', id='history-button', n_clicks=0, className='btn btn-secondary'),
            
            # --- NEW: Added Settings Button ---
            html.Button('Settings', id='settings-button', n_clicks=0, className='btn btn-secondary'),
            html.Button('User Manual', id='user-manual-button', n_clicks=0, className='btn btn-secondary'),
            
            html.Button('Logout', id='logout-button', n_clicks=0, className='btn btn-danger')
        ])
    ])
])