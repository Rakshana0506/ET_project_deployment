from dash import html, dcc
from components import header

# Helper function to create a styled mandatory label
def mandatory_label(text):
    return html.Label([
        text,
        html.Span(' *', style={'color': 'red', 'fontWeight': 'bold'})
    ], className='input-label')

register_layout = html.Div(className='layout-wrapper', children=[
    header,
    html.Div(className='main-container', children=[
        html.Div(className='card', children=[
            html.H2("Register"),

            # Form elements for user input
            mandatory_label('Name:'),
            dcc.Input(id='reg-name', type='text', placeholder='Your full name', className='input-field'),
            
            # --- EMAIL FIELD REMOVED ---
            
            mandatory_label('Username:'),
            dcc.Input(id='reg-username', type='text', placeholder='Choose a unique username', className='input-field'),
            
            mandatory_label('Password:'),
            dcc.Input(id='reg-password', type='password', placeholder='At least 8 characters, with A-Z, a-z, and 0-9', className='input-field'),
            
            mandatory_label('Confirm Password:'),
            dcc.Input(id='reg-password-confirm', type='password', placeholder='Re-type your password', className='input-field'),

            # Register button and message area
            html.Button('Register', id='register-button', n_clicks=0, className='btn btn-primary'),
            html.Div(id='register-message', className='message'), 

            # Link to the login page
            dcc.Link("Already have an account? Login here.", href='/login', className='switch-form-link')
        ])
    ])
])