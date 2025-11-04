from dash import html, dcc
from components import header

# This layout now uses the corrected structure for proper centering
register_layout = html.Div(className='layout-wrapper', children=[
    header,
    html.Div(className='main-container', children=[
        html.Div(className='card', children=[
            html.H2("Register"),

            # Form elements for user input
            dcc.Input(id='reg-name', type='text', placeholder='Name', className='input-field'),
            dcc.Input(id='reg-email', type='email', placeholder='Email', className='input-field'),
            dcc.Input(id='reg-username', type='text', placeholder='Username', className='input-field'),
            dcc.Input(id='reg-password', type='password', placeholder='Password', className='input-field'),

            # Register button and message area
            html.Button('Register', id='register-button', n_clicks=0, className='btn btn-primary'),
            html.Div(id='register-message', className='message message-success'),

            # Link to the login page
            dcc.Link("Already have an account? Login here.", href='/login', className='switch-form-link')
        ])
    ])
])

