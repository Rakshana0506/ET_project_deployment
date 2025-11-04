from dash import html

# This is the shared header component used across all pages.
# It is imported into each layout file (home.py, login.py, etc.).
header = html.Header(className='app-header', children=[
    html.Div(className='header-content', children=[
        # You could add a logo here if you wanted, e.g., html.Img(src='/assets/logo.png')
        html.H1('AI Debate Arena')
    ])
])
