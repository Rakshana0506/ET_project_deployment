from dash import html, dcc
from components import header

# This layout is for the "hot-seat" judge mode.
judge_mode_layout = html.Div(className='layout-wrapper', children=[
    header,
    html.Div(className='main-container', children=[
        
        # --- Stores for STT. REUSING IDs from practice_room ---
        # This is fine because the pages are never loaded at the same time.
        # This allows recorder.js to work on this page for free.
        dcc.Store(id='stt-output-store'),
        dcc.Store(id='timer-store'),
        
        html.Div(className='card practice-card', children=[
            # This outer div contains both the setup and the chat interface
            html.Div([
                
                # --- NEW: JUDGE SETUP UI ---
                html.Div(id='judge-setup-div', children=[
                    html.H2("Judge Mode Setup"),
                    html.H4("Set up a new human-vs-human debate."),
                    
                    dcc.Input(
                        id='judge-topic-input', type='text',
                        placeholder='Enter the debate topic...',
                        className='input-field'
                    ),
                    dcc.Input(
                        id='judge-turns-input', type='number',
                        placeholder='Number of turns (per player)',
                        min=1, max=10, step=1,
                        className='input-field'
                    ),

                    html.Hr(style={'marginTop': '20px', 'marginBottom': '20px'}),

                    # --- Player A ---
                    html.H5("Player A"),
                    dcc.Input(
                        id='player-a-name-input', type='text',
                        placeholder="Player A's Name",
                        className='input-field'
                    ),
                    dcc.RadioItems(
                        id='player-a-stance-radio',
                        options=[
                            {'label': 'Argues FOR', 'value': 'For'},
                            {'label': 'Argues AGAINST', 'value': 'Against'}
                        ],
                        className='radio-items'
                    ),

                    html.Hr(style={'marginTop': '20px', 'marginBottom': '20px'}),
                    
                    # --- Player B ---
                    html.H5("Player B"),
                    dcc.Input(
                        id='player-b-name-input', type='text',
                        placeholder="Player B's Name",
                        className='input-field'
                    ),
                    # Player B's stance will be set automatically by a callback
                    dcc.Input(
                        id='player-b-stance-display', type='text',
                        placeholder="Player B's Stance (auto-set)",
                        className='input-field',
                        disabled=True
                    ),
                    
                    html.Button('Start Debate', id='start-judge-debate-btn', n_clicks=0, className='btn btn-primary', style={'marginTop': '20px'})
                ]),

                # --- CHAT INTERFACE UI (Hidden by default) ---
                # This reuses the exact same layout and IDs as practice_room.py
                # This is so recorder.js and STT callbacks work automatically.
                html.Div(id='judge-interface-div', style={'display': 'none'}, children=[
                    html.H3(id='judge-topic-display'),
                    
                    # --- NEW: Turn Display ---
                    html.H4(id='judge-turn-display', style={'textAlign': 'center', 'marginBottom': '10px'}),

                    html.Div(id='judge-chat-window', className='chat-window'), # Unique ID
                    
                    dcc.Textarea(
                        id='user-input-textarea', # REUSED ID
                        placeholder='Type argument here...',
                        className='textarea-field'
                    ),
                    
                    # Wrapper for Record Button and Timer
                    html.Div([
                        html.Button('🎤 Record Argument', 
                                    id='stt-button', # REUSED ID
                                    n_clicks=0, 
                                    className='btn btn-secondary'
                        ),
                        html.Span('00:00', 
                                  id='recording-timer', # REUSED ID
                                  style={
                                      'marginLeft': '15px', 
                                      'fontFamily': 'monospace', 
                                      'fontSize': '1.4rem',
                                      'fontWeight': 'bold'
                                  }
                        )
                    ], style={
                        'display': 'flex', 
                        'alignItems': 'center', 
                        'marginBottom': '15px'
                    }),
                    
                    html.Button('Send Argument', id='judge-send-argument-btn', n_clicks=0, className='btn btn-primary'), # Unique ID
                    
                    html.Button('End Debate & Get Scores', 
                                id='judge-end-debate-btn', # Unique ID
                                n_clicks=0, 
                                className='btn btn-danger', 
                                style={'marginTop': '10px', 'display': 'none'} # Hidden until debate ends
                    ),
                    
                    dcc.Loading(
                        id="judge-loading-spinner", type="default",
                        children=html.Div(id="judge-loading-output")
                    )
                ]),
                
                html.Button('Exit to Home', id='judge-exit-home-btn', n_clicks=0, className='btn btn-secondary') # Unique ID
            ])
        ])
    ])
])