from dash import html, dcc
from components import header  # Assumes your header is in a components file
import textwrap  # <-- Correctly imported!

# This layout defines the content for the /manual page
manual_layout = html.Div(
    className='layout-wrapper',
    children=[
        header,
        html.Div(
            className='main-container',
            children=[
                # Card container for manual content
                html.Div(
                    className='card',
                    style={'maxWidth': '800px'},
                    children=[
                        html.H2("User Manual"),

                        # dcc.Markdown is used for formatted instructional text
                        dcc.Markdown(
                            # textwrap.dedent() correctly removes the Python indentation
                            # from the Markdown string.
                            textwrap.dedent(
                                '''
                                #### Welcome to **AI Debate Arena**
                                Your platform for structured, competitive debating — whether against AI or other players.

                                ---

                                ### **1. Add Your API Keys**
                                Before starting, go to **Settings** on the Home screen and enter:
                                - **Google (Gemini) API Key** – required for the AI Debater and AI Judge.
                                - **Azure Speech API Key and Region** – required for Speech-to-Text functionality.

                                > ⚠️ The app will not operate without these keys.

                                ---

                                ### **2. Choose Your Debate Mode**
                                Return to the **Home Page** and select your preferred mode:

                                #### 🧠 **Practice Mode**
                                - Debate **1-on-1 against the AI**.
                                - Configure the session by selecting:
                                  1. **Topic**
                                  2. **Number of turns**
                                  3. **Your stance** (*For* or *Against*)
                                
                                - During the debate, the AI will respond as your opponent.

                                **Results & Evaluation:**
                                - When the debate concludes, click **View Results** to open the **Results Page**.
                                - At the top, you’ll see a **circular performance scale** showing your **overall standing**, which combines your latest results with all previous Practice Mode performances.
                                - Below the scale, the **winner** and **scores** are displayed.
                                - To review the **strong and weak arguments** and the **judge’s feedback**, open the **Detailed Reasoning** dropdown .
                                
                                ---

                                #### 👥 **Judge Mode**
                                - A **two-player mode** for in-person debates.
                                - Before starting, set:
                                  1. **Number of turns per player**
                                  2. **Name of Player A** and their **stance** (*For* or *Against*)
                                  3. **Name of Player B** and their **stance** (*For* or *Against*)
                                - Players take turns presenting arguments on the same screen.
                                
                                **Results and Evaluation:**
                                - Once finished, click **View Results** to access the **Results Page**.
                                - The page displays the **winner** and **scores** for both participants.
                                - Open the **Detailed Reasoning** dropdown to view each player’s **strong and weak arguments**, along with **feedback from the AI Judge**.
                                
                                > Note: The **circular performance scale** appears only in Practice Mode, as it reflects a single user’s cumulative record.

                                ---

                                #### 📜 **View Debate History**
                                - Review your previous debates at any time by opening the given dropdown.

                                ---

                                ### **3. Enter the Arena**
                                Once your settings are complete, step into the **AI Debate Arena** and begin.
                                Select your mode, define your stance, and let the arguments unfold.
                                Good luck, and may the best debater prevail.
                                '''
                            ),  # <-- This parenthesis closes textwrap.dedent()
                            style={'textAlign': 'left', 'paddingTop': '15px'}
                        ),  # <-- This parenthesis closes dcc.Markdown()

                        html.Hr(),  # Adds a separator line

                        # Button to navigate back to home
                        html.Button(
                            'Back to Home',
                            id='manual-back-home-button',
                            n_clicks=0,
                            className='btn btn-secondary'
                        )
                    ]
                )
            ]
        )
    ]
)