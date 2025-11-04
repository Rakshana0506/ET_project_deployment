from dash import html, dcc
from components import header

# This layout now uses the corrected structure for proper centering
practice_layout = html.Div(className='layout-wrapper', children=[
    header,
    html.Div(className='main-container', children=[
        
        # This dcc.Store must be outside the hidden div so it always loads
        dcc.Store(id='stt-output-store'),
        dcc.Store(id='timer-store'), # <-- ADDED THIS LINE
        
        html.Div(className='card practice-card', children=[
            # This outer div contains both the setup and the chat interface
            html.Div([
                # --- DEBATE SETUP UI ---
                html.Div(id='debate-setup-div', children=[
                    html.H2("Practice Room"),
                    html.H4("Start a New Debate"),
                    dcc.Input(
                        id='debate-topic-input', type='text',
                        placeholder='Enter the debate topic...',
                        className='input-field'
                    ),
                    dcc.RadioItems(
                        id='debate-stance-radio',
                        options=[
                            {'label': 'I will argue FOR', 'value': 'For'},
                            {'label': 'I will argue AGAINST', 'value': 'Against'}
                        ],
                        className='radio-items'
                    ),
                    dcc.Input(
                        id='debate-turns-input', type='number',
                        placeholder='Number of turns (e.g., 3)',
                        min=1, max=10, step=1,
                        className='input-field'
                    ),
                    html.Button('Start Debate', id='start-debate-button', n_clicks=0, className='btn btn-primary')
                ]),

                # --- CHAT INTERFACE UI (Hidden by default) ---
                html.Div(id='debate-interface-div', style={'display': 'none'}, children=[
                    html.H3(id='debate-topic-display'),
                    html.Div(id='chat-window', className='chat-window'),
                    dcc.Textarea(
                        id='user-input-textarea',
                        placeholder='Type your argument...',
                        className='textarea-field'
                    ),
                    
                    # --- Wrapper for Record Button and Timer ---
                    html.Div([
                        # --- This button is controlled by recorder.js ---
                        html.Button('🎤 Record Argument', 
                                    id='stt-button', 
                                    n_clicks=0, 
                                    className='btn btn-secondary'
                        ),
                        # --- Timer Display ---
                        html.Span('00:00', 
                                  id='recording-timer', 
                                  style={
                                      'marginLeft': '15px', 
                                      'fontFamily': 'monospace', 
                                      'fontSize': '1.4rem',
                                      'fontWeight': 'bold'
                                  }
                        )
                    # --- Styling for the wrapper div ---
                    ], style={
                        'display': 'flex', 
                        'alignItems': 'center', 
                        'marginBottom': '15px'
                    }),
                    
                    html.Button('Send Argument', id='send-argument-button', n_clicks=0, className='btn btn-primary'),
                    
                    html.Button('View Final Results', 
                                id='view-results-button', 
                                n_clicks=0, 
                                className='btn btn-primary', 
                                style={'display': 'none', 'marginTop': '10px'} 
                    ),
                    
                    dcc.Loading(
                        id="loading-spinner", type="default",
                        children=html.Div(id="loading-output")
                    )
                ]),
                
                html.Button('Exit to Home', id='exit-practice-button', n_clicks=0, className='btn btn-secondary')
            ])
        ])
    ])
])