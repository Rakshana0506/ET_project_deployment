from dash import html, dcc
from components import header

# This is the layout for the NEW /settings page
settings_layout = html.Div(className='layout-wrapper', children=[
    header,
    html.Div(className='main-container', children=[
        html.Div(className='card', children=[
            
            html.H2("API Key Settings"),
            html.P("Your API keys are saved securely in your browser session and are never stored on our server."),
            
            # --- Google Gemini Key ---
            html.H5("Google AI Studio"),
            dcc.Input(
                id='google-key-input',
                type='password',
                placeholder='Enter your Google Gemini API Key...',
                className='input-field'
            ),

            # --- Azure Speech Keys ---
            html.H5("Microsoft Azure Speech"),
            dcc.Input(
                id='azure-key-input',
                type='password',
                placeholder='Enter your Azure Speech API Key...',
                className='input-field'
            ),
            dcc.Input(
                id='azure-region-input',
                type='text',
                placeholder='Enter your Azure Speech Region (e.g., centralindia)',
                className='input-field'
            ),
            
            html.Button('Save Keys', id='save-keys-btn', n_clicks=0, className='btn btn-primary'),
            
            html.Div(id='save-keys-message', className='message'), # For success/error
            
            # Button to go back home
            html.Button(
                'Back to Home', 
                id='settings-back-home-button', 
                n_clicks=0, 
                className='btn btn-secondary', 
                style={'marginTop': '20px'}
            )
        ])
    ])
])