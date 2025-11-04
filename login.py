from dash import html, dcc
from components import header

# This layout now uses the corrected structure for proper centering
login_layout = html.Div(className='layout-wrapper', children=[
    header,
    html.Div(className='main-container', children=[
        html.Div(className='card', children=[
            html.H2("Login"),

            # Form elements for user input
            dcc.Input(id='login-username', type='text', placeholder='Username', className='input-field'),
            dcc.Input(id='login-password', type='password', placeholder='Password', className='input-field'),

            # Login button and message area
            html.Button('Login', id='login-button', n_clicks=0, className='btn btn-primary'),
            html.Div(id='login-message', className='message message-error'),

            # Link to the registration page
            dcc.Link("Don't have an account? Register here.", href='/register', className='switch-form-link')
        ])
    ])
])

