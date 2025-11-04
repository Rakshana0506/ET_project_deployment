import dash

# This is the ONLY app = dash.Dash() in your entire project
# It is imported by run.py and callbacks.py

# Added the external stylesheet for the Google Fonts 'Poppins' font family.
# This ensures the font specified in your CSS is available to the browser.
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=['https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap']
)

server = app.server # Expose server for deployment

