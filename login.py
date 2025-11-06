from dash import html, dcc
from components import header

# You can put this helper function in a shared file, like components.py
def mandatory_label(text):
    return html.Label([
        text,
        html.Span(' *', style={'color': 'red', 'fontWeight': 'bold'})
    ], className='input-label')

login_layout = html.Div(className='layout-wrapper', children=[
    header,
    html.Div(className='main-container', children=[
        html.Div(className='card', children=[
            html.H2("Login"),

            # Form elements for user input
            mandatory_label('Username:'),
            dcc.Input(id='login-username', type='text', placeholder='Username', className='input-field'),
            
            mandatory_label('Password:'),
            dcc.Input(id='login-password', type='password', placeholder='Password', className='input-field'),

            # Login button and message area
            html.Button('Login', id='login-button', n_clicks=0, className='btn btn-primary'),
            html.Div(id='login-message', className='message'), # We'll control class via callback

            # Link to the registration page
            dcc.Link("Don't have an account? Register here.", href='/register', className='switch-form-link')
        ])
    ])
])