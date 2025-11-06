print("\n\n*** V13.0: USER-PROVIDED API KEYS ***\n\n")

import json
import pandas as pd
import os
import sqlite3 # For database fallback
import re # For parsing JSON
import psycopg2 # <-- ADDED for Render PostgreSQL
from psycopg2.extras import DictCursor # <-- ADDED for Render PostgreSQL
from datetime import datetime
import re
import pytz # <-- IMPORT FOR TIMEZONE FIX

# --- NEW IMPORTS FOR AZURE STT ---
import base64
import azure.cognitiveservices.speech as speechsdk
import io
import wave # <-- ADDED for WAV parsing
import threading # <-- ADDED for continuous recognition
# --- END NEW IMPORTS ---

from dash import html, dcc, Input, Output, State, callback_context, no_update
import dash_daq as daq

# Import the main 'app' variable from app.py
from app import app # This line is essential

# --- Database Helper Function (MODIFIED FOR RENDER) ---
def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database on Render
    or a local SQLite DB for development (if DATABASE_URL is not set).
    """
    DATABASE_URL = os.environ.get('DATABASE_URL')

    if DATABASE_URL:
        # --- PRODUCTION (Render) ---
        con = psycopg2.connect(DATABASE_URL)
        con.cursor_factory = DictCursor # Allows accessing columns by name
    else:
        # --- LOCAL (Development) ---
        print("WARNING: DATABASE_URL not set. Falling back to local app_data.db")
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DB_FILE = os.path.join(BASE_DIR, 'app_data.db')
        con = sqlite3.connect(DB_FILE)
        con.row_factory = sqlite3.Row
    
    return con

# --- Hardcoded User Profile (for AI context during practice) ---
user_profile_for_ai = {
    "age": "20",
    "gender": "Male",
    "country": "India",
    "education": "Bachelor's"
}

# --- MASTER PROMPTS ---
DEBATE_OPPONENT_PROMPT = """
You are a highly skilled, assertive, and competitive debater AI.
Your *only* role is to engage in a formal debate with the human user and try to win.
**DEBATE RULES:**
1.  **TOPIC:** {topic}
2.  **YOUR STANCE:** You are arguing **{opponent_stance}**. You must defend this position at all costs.
3.  **OPPONENT'S STANCE:** The user is arguing **{user_stance}**.
**YOUR INSTRUCTIONS (CRITICAL):**
-   You are the **{opponent_stance}** side. You must *only* make arguments that support your stance.
-   Your goal is to *win* the debate by being more persuasive and logical than the user.
-   Directly rebut the user's previous points. Find flaws in their logic, evidence, or reasoning.
-   Present your own counter-arguments, evidence, and examples to strengthen your **{opponent_stance}** position.
-   Maintain a formal, respectful, and intelligent persona.
**!! IMPORTANT: WHAT *NOT* TO DO !!**
-   **DO NOT** act as a judge, coach, or assistant.
-   **DO NOT** give feedback on the user's performance.
-   **DO NOT** agree with the user or concede any points.
-   **DO NOT** summarize the debate or declare a winner.
-   **DO NOT** break character. You are a debater, *not* a helpful AI.
You will receive the chat history. Your job is to provide the *next* logical rebuttal from your assigned stance.
"""

DEBATE_JUDGE_PROMPT = """
You are an impartial, expert debate judge. Your sole task is to analyze the following debate transcript and provide a detailed evaluation in a specific JSON format.
**DEBATE DETAILS:**
-   **Topic:** {topic}
-   **User's Stance:** {user_stance}
-   **AI's Stance:** {ai_stance}
**TRANSCRIPT:**
{transcript}
---
**YOUR TASK:**
Evaluate both the 'User' and the 'AI' on the following five criteria.

**!! JUDGE'S CRITICAL RULE !!**
You MUST be strict and fair. Scores range from 0 (non-existent) to 10 (excellent).
**If an argument is non-existent, irrelevant (e.g., just says "hi"), or makes no attempt, you MUST give it a score of 0.**

**!! JUDICIAL GUARDRAILS (CRITICAL) !!**
- **BE IMPARTIAL:** Your evaluation must be based *only* on the arguments presented in the transcript. Do not introduce any external knowledge or personal opinions on the topic.
- **BE A JUDGE, NOT A COACH:** Do not provide motivational feedback or overly conversational praise. Your "constructiveFeedback" must be clinical, direct, and actionable.
- **DO NOT HALLUCINATE:** If a debater fails to provide evidence, their score for "evidenceAndExamples" MUST be low or 0. Do not invent arguments they *could* have made. Judge *only* what is in the transcript.
- **ADHERE TO THE FORMAT:** Your *only* output must be the JSON object. Do not add any text before or after it, such as "Here is the JSON:" or "```json".
- **USE THE FULL SCORING RANGE:** Do not hesitate to give a 10 for a perfect execution of a skill or a 0-2 for a very poor one. Avoid clustering all scores in the middle (4-7).
- **LINK FEEDBACK TO METRICS:** Your `constructiveFeedback` must be specific. For example, instead of "Be more persuasive," say "To improve your *evidenceAndExamples* score, cite a specific statistic."
- **PROVIDE JUSTIFICATION, NOT SUMMARY:** Your `reasoning` fields must *justify* the score, not just repeat what the debater said. Explain *why* an argument was weak or strong.
- **MAINTAIN A CONSISTENT STANDARD:** Apply the scoring metrics with the same level of scrutiny to both the 'User' and the 'AI'.

1.  **logicalConsistency (Score 0-10):**
    * **Focus:** The integrity of the argument's structure and its internal coherence.
    * **Judicial Insight (Referencing Fallacies):** Score based on how well the debater maintained a consistent thesis without introducing **internal contradictions** or relying on obvious logical **fallacies** (e.g., *slippery slope, circular reasoning, false dichotomy, hasty generalization*). A high score reflects arguments where the premises directly and unequivocally support the conclusion throughout the debate. Low scores indicate a fundamental breakdown in the logical chain, a significant shift in the central claim's definition, or the use of **non-sequiturs** (where the conclusion does not follow from the premise). **A score of 0 MUST be given for non-existent arguments.**

2.  **evidenceAndExamples (Score 0-10):**
    * **Focus:** The quality, relevance, and strategic deployment of supporting material.
    * **Judicial Insight (Referencing Toulmin/Credibility):** Score based on the **specificity**, **authority**, and **timeliness** of the evidence. Was the supporting data the *Grounds* for the *Claim* (Toulmin Model)? Did the debater move beyond mere assertion by providing sufficient **Warrant** (the link between evidence and claim)? High scores are reserved for those who cite specific, verifiable statistics, academic studies, or detailed, relevant historical precedents. Low scores result from relying on vague phrases ("Studies show...") or using anecdotal/emotional evidence where empirical facts are required. **A score of 0 MUST be given if no evidence is presented.**

3.  **clarityAndConcision (Score 0-10):**
    * **Focus:** The structural effectiveness and communicative efficiency of the argument.
    * **Judicial Insight (Referencing Rhetoric/Flowing):** Score based on the debater's use of **signposting** (e.g., "My first point is...", "Moving to my opponent's claim about X..."), clear topic sentences, and avoiding verbose or tangential explanations. A perfect score means the argument was immediately understandable, powerful, and free of filler, allowing the opponent and judge to Ee *flow"** (take notes on) the key claims. Low scores are given for rambling, confusing complexity, excessive jargon, or a lack of clear separation between arguments. **A score of 0 MUST be given for irrelevant or non-existent arguments.**

4.  **rebuttalEffectiveness (Score 0-10):**
    * **Focus:** The ability to directly engage with and dismantle the opponent's specific arguments.
    * **Judicial Insight (Referencing Line-by-Line):** Score based on a **"line-by-line"** approach rather than merely restating one's own position. Did the debater successfully isolate the opponent's core **Mechanism** or **Impact** and explain *why* it fails, rather than simply disagreeing? The most effective rebuttals challenge the opponent's **Warrant** or provide a strong, comparative counter-impact. Low scores are given for **shadow boxing** (attacking an argument the opponent never made) or dropping (failing to address) crucial, damaging points. **A score of 0 MUST be given if no rebuttal is attempted.**

5.  **overallPersuasiveness (Score 0-10):**
    * **Focus:** The holistic assessment of the argument's impact and the establishment of a superior position.
    * **Judicial Insight (Referencing Comparative Advantage):** This score is the final synthesis. It measures which debater more effectively established a **central narrative** (or *Framework*) and demonstrated a **comparative advantage**—proving their solution or view is *better* than the opponent's, even if the opponent's claims are partially true. A high score means the debater successfully **"weighed"** the key issues, showing why their metrics for success (e.g., public safety over economic cost) should be prioritized by the judge. The winning debater should be the one who best articulated *why* their side *matters more*. **A score of 0 MUST be given for non-existent arguments.**

**OUTPUT FORMAT (CRITICAL):**
Your response **MUST** be a valid JSON object. Do not include any text before or after the JSON, and do not use markdown like ```json.
The JSON structure must be *exactly* as follows:
{{
  "scores": {{
    "User": {{
      "logicalConsistency": <score_0_to_10>,
      "evidenceAndExamples": <score_0_to_10>,
      "clarityAndConcision": <score_0_to_10>,
      "rebuttalEffectiveness": <score_0_to_10>,
      "overallPersuasiveness": <score_0_to_10>
    }},
    "AI": {{
      "logicalConsistency": <score_0_to_10>,
      "evidenceAndExamples": <score_0_to_10>,
      "clarityAndConcision": <score_0_to_10>,
      "rebuttalEffectiveness": <score_0_to_10>,
      "overallPersuasiveness": <score_0_to_10>
    }}
  }},
  "reasoning": {{
    "strongestArgumentUser": "<Briefly describe the 'User's' best point. If 0, state 'No argument presented.'>",
    "strongestArgumentAI": "<Briefly describe the 'AI's' best point. If 0, state 'No argument presented.'>",
    "weakestArgumentUser": "<Briefly describe the 'User's' weakest point. If 0, state 'No argument presented.'>",
    "weakestArgumentAI": "<Briefly describe the 'AI's' weakest point. If 0, state 'No argument presented.'>",
    "rebuttalAnalysis": "<A summary of who was more effective at rebutting. If neither, state 'No rebuttals were made.'>",
    "overallWinner": "<'User', 'AI', or 'Draw'>",
    "constructiveFeedbackUser": "<One or two specific, actionable suggestions for the 'User' to improve. If 0, feedback can be 'No valid argument was presented.'>",
    "constructiveFeedbackAI": "<One or two specific, actionable suggestions for the 'AI' to improve. If 0, feedback can be 'No valid argument was presented.'>"
  }}
}}
**INSTRUCTIONS FOR JSON FIELDS:**
-   All scores: Must be a single number (integer or float) between 0 and 10.
-   reasoning fields: Provide concise, objective analysis.
-   overallWinner: Must be *one* of the three exact strings: "User", "AI", or "Draw".
-   **constructiveFeedbackUser**: Provide 1-2 concise, actionable pieces of advice for the 'User'.
-   **constructiveFeedbackAI**: Provide 1-2 concise, actionable pieces of advice for the 'AI'.
"""

# --- *** NEW: HELPER FUNCTION TO SAVE DEBATES *** ---
def save_debate_to_db(username, debate_state, chat_history, final_results):
    """
    Saves the completed debate transcript and results to the database.
    """
    print(f"--- Saving debate history for user: {username} ---")
    
    try:
        state_json = json.dumps(debate_state)
        history_json = json.dumps(chat_history)
        results_json = json.dumps(final_results)
    except Exception as e:
        print(f"CRITICAL ERROR: Could not serialize debate data to JSON: {e}")
        return 

    con = get_db_connection()
    ph = '?' if isinstance(con, sqlite3.Connection) else '%s'
    
    sql_insert = f"""
    INSERT INTO debate_history 
    (username, debate_mode, debate_topic, debate_state, chat_history, final_results, timestamp)
    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """
    
    try:
        cur = con.cursor()
        cur.execute(sql_insert, (
            username,
            debate_state.get('mode', 'unknown'),
            debate_state.get('topic', 'N/A'),
            state_json,
            history_json,
            results_json,
            datetime.now(pytz.utc) # <-- FIX 1: USE UTC TIMEZONE
        ))
        con.commit()
        print("--- Debate history saved successfully. ---")
    except Exception as e:
        con.rollback()
        print(f"CRITICAL ERROR: Could not save debate to database: {e}")
    finally:
        con.close()

# --- USER AUTHENTICATION & MANAGEMENT ---
def is_password_strong(password):
    """
    Checks if password is at least 8 chars, has upper, lower, and number.
    And contains ONLY alphanumeric characters (no symbols).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.fullmatch(r"^[a-zA-Z0-9]+$", password):
        # This ensures no symbols, only letters and numbers
        return False, "Password must only contain letters and numbers (no symbols)."
    return True, ""


##
## UPDATED REGISTRATION CALLBACK
##
@app.callback(
    [Output('register-message', 'children'),
     Output('register-message', 'className')],
    Input('register-button', 'n_clicks'),
    [State('reg-name', 'value'),
     # --- 'reg-email' STATE REMOVED ---
     State('reg-username', 'value'),
     State('reg-password', 'value'),
     State('reg-password-confirm', 'value')],
    prevent_initial_call=True
)
def register_user(n_clicks, name, username, password, password_confirm): # <-- 'email' removed from parameters
    
    # 1. Check if all fields are filled
    if not all([name, username, password, password_confirm]): # <-- 'email' removed from check
        return "Please fill in all mandatory fields.", "message message-error"
        
    # 2. Check if passwords match
    if password != password_confirm:
        return "Passwords do not match.", "message message-error"
        
    # 3. Check password strength
    strong, message = is_password_strong(password)
    if not strong:
        return message, "message message-error"

    # --- Database logic ---
    con = get_db_connection()
    ph = '?' if isinstance(con, sqlite3.Connection) else '%s'
    
    try:
        cur = con.cursor() 
        
        # !! SECURITY WARNING !!
        # You should HASH your password before storing it.
        
        # --- SQL query updated to remove 'email' ---
        sql_insert_user = f"INSERT INTO users (name, username, password) VALUES ({ph}, {ph}, {ph})"
        cur.execute(sql_insert_user, (name, username, password)) # <-- 'email' removed from tuple
        
        # --- This user_stats query is fine as it only uses username ---
        sql_insert_stats = f"""
            INSERT INTO user_stats (
                username, debates_won, debates_lost, debates_drawn,
                avg_logicalconsistency, avg_evidenceandexamples,
                avg_clarityandconcision, avg_rebuttaleffectiveness,
                avg_overallpersuasiveness
            ) VALUES ({ph}, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
            """
        cur.execute(sql_insert_stats, (username,))
        
        con.commit() 
        message = f"Registration successful for {username}! You can now log in."
        classname = "message message-success"
        
    except (sqlite3.IntegrityError, psycopg2.IntegrityError) as e:
        con.rollback() 
        # --- Updated error message ---
        message = "Username already exists."
        classname = "message message-error"
    except Exception as e:
        con.rollback()
        print(f"Registration error: {e}")
        message = "An error occurred during registration. Please try again."
        classname = "message message-error"
    finally:
        con.close()
        
    return message, classname

##
## UPDATED LOGIN CALLBACK (to add error styling)
##
@app.callback(
    [Output('session-storage', 'data', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True),
     Output('login-message', 'children'),
     Output('login-message', 'className')], # <-- Added className output
    Input('login-button', 'n_clicks'),
    [State('login-username', 'value'),
     State('login-password', 'value'),
     State('session-storage', 'data')],
    prevent_initial_call=True
)
def login_user(n_clicks, username, password, session_data):
    if not username or not password:
        return no_update, no_update, "Please enter username and password.", "message message-error"
        
    con = get_db_connection()
    ph = '?' if isinstance(con, sqlite3.Connection) else '%s'

    try:
        cur = con.cursor()
        
        sql_select_user = f"SELECT password FROM users WHERE username = {ph}"
        cur.execute(sql_select_user, (username,))
        
        user_record = cur.fetchone()
        
        # !! SECURITY WARNING !!
        # You should be checking a HASHED password here, not plain text.
        # e.g., if user_record and check_password_hash(user_record['password'], password):
        
        if user_record and user_record['password'] == str(password):
            session_data = session_data or {}
            session_data['active_user'] = username
            # Go to home, no message, and default message class
            return session_data, '/home', "", "message" 
        else:
            return no_update, no_update, "Invalid username or password.", "message message-error"
            
    except Exception as e:
        print(f"Login error: {e}")
        return no_update, no_update, "An error occurred during login.", "message message-error"
    finally:
        con.close()


@app.callback(
    Output('home-welcome-message', 'children'),
    Input('session-storage', 'data')
)
def show_welcome(session_data):
    if session_data and session_data.get('active_user'):
        username = session_data.get('active_user')
        return f"Welcome, {username}!"
    return "Welcome!"

@app.callback(
    [Output('session-storage', 'data', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True)],
    Input('logout-button', 'n_clicks'),
    State('session-storage', 'data'),
    prevent_initial_call=True
)
def logout_user(n_clicks, session_data):
    if n_clicks > 0:
        session_data = session_data or {}
        session_data['active_user'] = None
        session_data['debate_state'] = None
        session_data['chat_history'] = None
        session_data['final_results'] = None
        return session_data, '/login'
    return no_update, no_update

# --- NAVIGATION CALLBACKS ---
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    [Input('practice-mode-button', 'n_clicks'),
     Input('judge-mode-button', 'n_clicks'),
     Input('history-button', 'n_clicks'),
     Input('settings-button', 'n_clicks'), # <-- NEW
     Input('user-manual-button', 'n_clicks')],
    prevent_initial_call=True
)
def navigate_from_home(practice_clicks, judge_clicks, history_clicks, settings_clicks, manual_clicks): # <-- NEW
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'practice-mode-button':
        return '/practice'
    elif button_id == 'judge-mode-button':
        return '/judge'
    elif button_id == 'history-button':
        return '/history'
    elif button_id == 'settings-button': # <-- NEW
        return '/settings'
    elif button_id == 'user-manual-button':  # <-- 3. ADD THE LOGIC TO NAVIGATE
        return '/manual'
    return no_update

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('debate-again-button', 'n_clicks'),
    prevent_initial_call=True
)
def navigate_from_dashboard(n_clicks):
    if n_clicks > 0:
        return '/practice' 
    return no_update

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('judge-again-button', 'n_clicks'), 
    prevent_initial_call=True
)
def navigate_judge_again(n_clicks):
    if n_clicks > 0:
        return '/judge' 
    return no_update

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('exit-practice-button', 'n_clicks'),
    prevent_initial_call=True
)
def navigate_from_practice_room(n_clicks):
    if n_clicks > 0:
        return '/home'
    return no_update

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('judge-exit-home-btn', 'n_clicks'),
    prevent_initial_call=True
)
def navigate_from_judge_mode(n_clicks):
    if n_clicks > 0:
        return '/home'
    return no_update

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('dashboard-exit-home-button', 'n_clicks'),
    prevent_initial_call=True
)
def navigate_dashboard_to_home(n_clicks):
    if n_clicks > 0:
        return '/home'
    return no_update

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('history-back-home-button', 'n_clicks'),
    prevent_initial_call=True
)
def navigate_history_to_home(n_clicks):
    if n_clicks > 0:
        return '/home'
    return no_update

# --- NEW: Navigation from settings page back to home ---
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('settings-back-home-button', 'n_clicks'),
    prevent_initial_call=True
)
def navigate_settings_to_home(n_clicks):
    if n_clicks > 0:
        return '/home'
    return no_update
# --- 4. ADD THIS ENTIRE NEW CALLBACK ---
# This code block goes right after the navigate_settings_to_home callback
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('manual-back-home-button', 'n_clicks'),  # <-- HERE IT IS
    prevent_initial_call=True
)
def navigate_manual_to_home(n_clicks):
    if n_clicks > 0:
        return '/home'
    return no_update
# --- END OF NEW CALLBACK ---

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('view-results-button', 'n_clicks'),
    prevent_initial_call=True
)
def navigate_to_results(n_clicks):
    if n_clicks > 0:
        return '/practice-results'
    return no_update

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('judge-end-debate-btn', 'n_clicks'),
    prevent_initial_call=True
)
def navigate_judge_to_results(n_clicks):
    if n_clicks > 0:
        return '/judge-results'
    return no_update

# --- *** NEW: SETTINGS PAGE CALLBACK *** ---
@app.callback(
    [Output('session-storage', 'data', allow_duplicate=True),
     Output('save-keys-message', 'children')],
    Input('save-keys-btn', 'n_clicks'),
    [State('google-key-input', 'value'),
     State('azure-key-input', 'value'),
     State('azure-region-input', 'value'),
     State('session-storage', 'data')],
    prevent_initial_call=True
)
def save_api_keys_to_session(n_clicks, google_key, azure_key, azure_region, session_data):
    if not all([google_key, azure_key, azure_region]):
        return no_update, html.P("Please fill in all three fields.", style={'color': 'red'})

    session_data = session_data or {}
    session_data['google_key'] = google_key
    session_data['azure_key'] = azure_key
    session_data['azure_region'] = azure_region
    
    print("--- API Keys saved to session storage. ---")
    
    return session_data, html.P("Keys saved successfully for this session!", style={'color': 'green'})


# --- NEW CALLBACK: SHOWS API KEY WARNING ON HOME PAGE ---
# --- NEW CALLBACK: SHOWS DYNAMIC API KEY WARNING ON HOME PAGE ---
# --- This callback checks for keys and fixes the "flicker" problem ---
@app.callback(
    Output('api-key-warning-container', 'children'),
    [Input('url', 'pathname'),
     Input('session-storage', 'data')]
)
def show_api_key_warning(pathname, session_data):
    # Only run this check when the user is on the home page
    if pathname == '/home':
        session_data = session_data or {}
        google_key = session_data.get('google_key')
        azure_key = session_data.get('azure_key')

        # If keys are missing, show the styled warning message
        if not google_key or not azure_key:
            return html.Div([
                html.P("⚠️ API Keys Missing!", 
                       style={'fontWeight': 'bold', 'color': 'var(--text-primary)', 'margin': '0 0 5px 0'}),
                html.P("The app will not work until you add your keys in Settings.", 
                       style={'color': 'var(--text-secondary)', 'margin': '0 0 15px 0'}),
                dcc.Link(
                    # This button uses your existing CSS, but the .api-warning-box class will resize it
                    html.Button("Go to Settings Now", className="btn btn-primary"), 
                    href="/settings", 
                    style={'textDecoration': 'none'}
                )
            ], className='api-warning-box') # We will style this class in CSS
        
        # If on /home AND keys are present, return an empty list to clear the warning
        return []
    
    # --- THE FLICKER FIX ---
    # If we are NOT on the home page, do not send any update.
    # This stops the callback from clearing its own output during the page-load flicker.
    return no_update

# --- *** MODIFIED: SPEECH-TO-TEXT CALLBACK *** ---
# --- Now takes keys from session-storage ---
def transcribe_audio_from_base64(base64_audio_data, azure_key, azure_region):
    print("\n\n*** PYTHON: 'handle_audio_transcript' (Azure) CALLBACK TRIGGERED! ***\n\n")
    
    if not azure_key or not azure_region:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("--- PYTHON ERROR: Azure Speech Key/Region is missing from session. ---")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return None

    if not base64_audio_data:
        print("--- PYTHON WARNING: Callback triggered with no audio data. ---")
        return None

    try:
        print("--- PYTHON: Decoding audio data... ---")
        audio_content = base64.b64decode(base64_audio_data)
        wav_file_bytes = io.BytesIO(audio_content)
        raw_audio_data = b""
        sample_rate = 0
        bits_per_sample = 0
        channels = 0

        try:
            with wave.open(wav_file_bytes, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                bits_per_sample = wav_file.getsampwidth() * 8 
                sample_rate = wav_file.getframerate()
                raw_audio_data = wav_file.readframes(wav_file.getnframes())
            
            print(f"--- PYTHON: WAV file parsed. Rate: {sample_rate}, Bits: {bits_per_sample}, Channels: {channels} ---")

        except Exception as e:
            print(f"--- PYTHON ERROR: Failed to parse WAV file. Error: {e} ---")
            return None

        # --- *** MODIFIED: Use keys from session *** ---
        speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
        speech_config.speech_recognition_language = "en-IN" 
        speech_config.enable_dictation()

        stream_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=sample_rate,
            bits_per_sample=bits_per_sample,
            channels=channels
        )
        stream = speechsdk.audio.PushAudioInputStream(stream_format=stream_format)
        stream.write(raw_audio_data) 
        stream.close() 
        
        audio_config = speechsdk.audio.AudioConfig(stream=stream)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        
        all_results = []
        done = threading.Event()

        def recognized_cb(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print(f"--- AZURE: Recognized fragment: {evt.result.text} ---")
                all_results.append(evt.result.text)
            elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                print("--- AZURE: NoMatch fragment ---")

        def session_stopped_cb(evt):
            print("--- AZURE: Session Stopped ---")
            done.set()

        def canceled_cb(evt):
            print(f"--- AZURE: CANCELED: {evt.reason} ---")
            if evt.reason == speechsdk.CancellationReason.Error:
                print(f"--- AZURE CANCELLATION DETAILS: {evt.error_details} ---")
            done.set()

        speech_recognizer.recognized.connect(recognized_cb)
        speech_recognizer.session_stopped.connect(session_stopped_cb)
        speech_recognizer.canceled.connect(canceled_cb)

        print("--- PYTHON: Starting CONTINUOUS recognition... ---")
        speech_recognizer.start_continuous_recognition()
        done.wait(timeout=180.0) 
        speech_recognizer.stop_continuous_recognition()
        print("--- PYTHON: Continuous recognition finished. ---")

        full_transcript = " ".join(all_results)
        
        if full_transcript:
            print(f"--- PYTHON SUCCESS (Continuous): {full_transcript} ---")
            return full_transcript
        else:
            print("--- PYTHON ERROR: No speech recognized (Continuous). ---")
            return None
            
    except Exception as e:
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"!!! A CRITICAL ERROR OCCURRED: {e} !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return None

# --- *** MODIFIED: STT Callback now triggers popup on error *** ---
@app.callback(
    [Output('user-input-textarea', 'value', allow_duplicate=True),
     Output('stt-loading-output', 'children'),
     Output('api-key-error-popup', 'displayed', allow_duplicate=True),
     Output('api-key-error-popup', 'message', allow_duplicate=True)],
    Input('stt-output-store', 'data'), 
    [State('user-input-textarea', 'value'),
     State('session-storage', 'data')],
    prevent_initial_call=True
)
def handle_audio_transcript(base64_audio_data, current_text, session_data):
    
    session_data = session_data or {}
    azure_key = session_data.get('azure_key')
    azure_region = session_data.get('azure_region')

    if not azure_key or not azure_region:
        print("STT Error: No Azure keys found in session. Go to Settings.")
        error_msg = "ERROR: Azure Speech keys are not set. Please go to the Settings page."
        # Return 4 values: (textarea, loading, popup_displayed, popup_message)
        return no_update, None, True, error_msg 

    transcript = transcribe_audio_from_base64(base64_audio_data, azure_key, azure_region)
    
    print(f"--- PYTHON CALLBACK RECEIVED: {transcript} ---")
    
    if transcript:
        if current_text:
            # Success: (textarea, loading, popup_displayed, popup_message)
            return f"{current_text} {transcript}", None, no_update, no_update
        # Success: (textarea, loading, popup_displayed, popup_message)
        return transcript, None, no_update, no_update
    
    # --- Transcription failed (e.g., invalid key or no speech) ---
    else:
        print("STT Error: Transcription returned None.")
        fail_msg = "Transcription failed. (No speech detected, or Azure keys are invalid)"
        # Failure: (textarea, loading, popup_displayed, popup_message)
        return no_update, None, True, fail_msg 
# --- *** END OF STT CALLBACK MODIFICATION *** ---


# --- *** CLIENT-SIDE CALLBACKS TO CLEAR TEXT AREA *** ---
app.clientside_callback(
    """
    function(n_clicks) {
        return "";
    }
    """,
    Output('user-input-textarea', 'value', allow_duplicate=True),
    [Input('send-argument-button', 'n_clicks')],
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(n_clicks) {
        return "";
    }
    """,
    Output('user-input-textarea', 'value', allow_duplicate=True),
    [Input('judge-send-argument-btn', 'n_clicks')],
    prevent_initial_call=True
)
# --- *** END OF CLIENT-SIDE CALLBACKS *** ---


# --- PRACTICE MODE CALLBACKS (AI vs Human) ---
# --- *** MODIFIED: Now checks for API key BEFORE starting debate *** ---
@app.callback(
    [Output('debate-setup-div', 'style'),
     Output('debate-interface-div', 'style'),
     Output('debate-topic-display', 'children'),
     Output('chat-window', 'children'),
     Output('session-storage', 'data', allow_duplicate=True),
     
     Output('view-results-button', 'style', allow_duplicate=True),
     Output('send-argument-button', 'disabled', allow_duplicate=True),
     Output('user-input-textarea', 'disabled', allow_duplicate=True),
     
     # --- NEW POPUP OUTPUTS (add these) ---
     Output('api-key-error-popup', 'displayed', allow_duplicate=True),
     Output('api-key-error-popup', 'message', allow_duplicate=True)
    ],
    Input('start-debate-button', 'n_clicks'),
    [State('debate-topic-input', 'value'),
     State('debate-stance-radio', 'value'),
     State('debate-turns-input', 'value'),
     State('session-storage', 'data')],
    prevent_initial_call=True
)
def start_practice_debate(n_clicks, topic, stance, turns, session_data):
    session_data = session_data or {}
    
    # --- Original logic continues below ---
    results_button_style = {'display': 'none', 'marginTop': '10px'}
    send_button_disabled = False
    textarea_disabled = False

    if not all([topic, stance, turns]):
        # Return 10 values: 8 no_updates, 2 popup no_updates
        return (no_update, no_update, no_update, no_update, no_update, 
                no_update, no_update, no_update,
                no_update, no_update) # <-- hide popup

    debate_state = {
        'mode': 'practice', 
        'topic': topic,
        'user_stance': stance,
        'opponent_stance': 'Against' if stance == 'For' else 'For',
        'total_turns': int(turns),
        'current_turn': 0
    }
    session_data['debate_state'] = debate_state
    session_data['chat_history'] = [] 
    session_data['final_results'] = None
    initial_message = html.Div(f"Debate started on: '{topic}'. You are arguing '{stance}'. Waiting for your first argument.",
                               style={'fontStyle': 'italic', 'color': 'grey', 'textAlign': 'center'})
    
    # Return 10 values:
    # - 8 original success values
    # - 2 "no_update" for the popup (to hide it if it was open)
    return ({'display': 'none'}, {'display': 'block'},
            f"Topic: {topic}", [initial_message], session_data,
            results_button_style, send_button_disabled, textarea_disabled,
            no_update, no_update) # <-- Hide popup on success

# --- *** MODIFIED: Practice turn now triggers popup on error *** ---
@app.callback(
    [Output('chat-window', 'children', allow_duplicate=True),
     Output('session-storage', 'data', allow_duplicate=True),
     Output('loading-output', 'children'),
     Output('url', 'pathname', allow_duplicate=True),
     
     Output('view-results-button', 'style', allow_duplicate=True),
     Output('send-argument-button', 'disabled', allow_duplicate=True),
     Output('user-input-textarea', 'disabled', allow_duplicate=True),
     Output('timer-store', 'data', allow_duplicate=True),
     # --- NEW POPUP OUTPUTS ---
     Output('api-key-error-popup', 'displayed', allow_duplicate=True),
     Output('api-key-error-popup', 'message', allow_duplicate=True)], 
    Input('send-argument-button', 'n_clicks'),
    [State('user-input-textarea', 'value'),
     State('session-storage', 'data'),
     State('chat-window', 'children'),
     State('timer-store', 'data')], 
    prevent_initial_call=True
)
def handle_practice_turn(n_clicks, user_input, session_data, current_chat, timer_data):
    import google.generativeai as genai 

    current_chat = current_chat if current_chat is not None else []
    
    results_button_style = {'display': 'none', 'marginTop': '10px'}
    send_button_disabled = False
    textarea_disabled = False
    
    # --- Get key from session ---
    session_data = session_data or {}
    google_key = session_data.get('google_key')
    
    # --- MODIFIED ERROR HANDLING ---
    if not google_key:
        error_msg = "ERROR: Google API Key not set. Please go to the Settings page."
        # Return 10 values
        return (no_update, no_update, None, no_update, 
                no_update, no_update, no_update, None, 
                True, error_msg)
    
    try:
        genai.configure(api_key=google_key)
    except Exception as e:
        error_msg = f"ERROR: Invalid Google API Key provided. Please check Settings."
        print(f"Google Key Error: {e}")
        # Return 10 values
        return (no_update, no_update, None, no_update, 
                no_update, no_update, no_update, None, 
                True, error_msg)
    
    if not user_input or 'debate_state' not in session_data:
        # Return 10 values
        return (no_update, no_update, None, no_update, 
                no_update, no_update, no_update, None, 
                no_update, no_update)

    debate_state = session_data['debate_state']
    chat_history = session_data.get('chat_history', []) 

    # 1. Add user message
    user_message = f"User ({debate_state['user_stance']}): {user_input}"
    current_chat.append(html.P(user_message, style={'textAlign': 'right'}))
    
    timer_string = timer_data or "" 
    chat_history.append({'role': 'user', 'parts': [user_input], 'time': timer_string})

    # 2. Increment turn
    debate_state['current_turn'] += 1
    session_data['debate_state'] = debate_state

    # 3. Check for end of debate
    if debate_state['current_turn'] >= debate_state['total_turns']:
        
        opponent_system_prompt = DEBATE_OPPONENT_PROMPT.format(
            topic=debate_state['topic'],
            user_stance=debate_state['user_stance'], 
            opponent_stance=debate_state['opponent_stance']
        )
        dynamic_chat_model = genai.GenerativeModel(
            'gemini-2.0-flash',
            system_instruction=opponent_system_prompt
        )
        
        # --- START OF FIX (ValueError: time) ---
        dirty_previous_history = chat_history[:-1] 
        clean_previous_history = [
            {'role': msg['role'], 'parts': msg['parts']} 
            for msg in dirty_previous_history
        ]
        chat_session = dynamic_chat_model.start_chat(history=clean_previous_history)
        # --- END OF FIX ---
        
        try:
            response = chat_session.send_message(user_input) 
            ai_response_text = response.text
        except Exception as e:
            ai_response_text = f"An error occurred while generating the AI's final response: {e}"
            print(f"API Error (Final Turn): {e}")
            # Check if it's an API key error
            if "API key" in str(e):
                error_msg = "ERROR: Google API Key is invalid or expired. Please check Settings."
                return (no_update, no_update, None, no_update, 
                        no_update, no_update, no_update, None, 
                        True, error_msg)

        # 4. Add Final AI Response
        ai_message = f"AI ({debate_state['opponent_stance']}): {ai_response_text}"
        current_chat.append(html.P(ai_message, style={'textAlign': 'left'}))
        chat_history.append({'role': 'model', 'parts': [ai_response_text]}) 
        
        print("--- Calling get_judgment with COMPLETE history ---")
        try:
            judgment = get_judgment(debate_state, chat_history, google_key)
        except Exception as e:
            print(f"--- handle_turn CAUGHT AN ERROR: {e} ---")
            judgment = {'error': f'Judge API/Parsing failed: {e}', 'raw_text': 'N/A'}

        # 5. Save final results
        session_data['final_results'] = judgment
        session_data['debate_state_before_completion'] = debate_state
        session_data['debate_state'] = None 
        session_data['chat_history'] = chat_history

        try:
            save_debate_to_db(
                session_data['active_user'], 
                session_data['debate_state_before_completion'], 
                chat_history, 
                judgment
            )
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to save practice debate to DB: {e}")

        # 6. Safely try to update stats
        try:
            print("--- Calling update_user_stats ---")
            update_user_stats(session_data['active_user'], judgment)
        except Exception as e:
            print(f"CRITICAL ERROR in post-debate processing (stats/save): {e}")
        
        # 7. Show results button
        results_button_style = {'display': 'block', 'marginTop': '10px'} 
        send_button_disabled = True
        textarea_disabled = True
        
        # Return 10 values
        return (current_chat, session_data, None, no_update, 
                results_button_style, send_button_disabled, textarea_disabled, None,
                no_update, no_update)

    # --- NORMAL TURN LOGIC (AI Responds) ---
    
    # 4. Get AI response
    opponent_system_prompt = DEBATE_OPPONENT_PROMPT.format(
        topic=debate_state['topic'],
        user_stance=debate_state['user_stance'], 
        opponent_stance=debate_state['opponent_stance']
    )
    dynamic_chat_model = genai.GenerativeModel(
        'gemini-2.0-flash', 
        system_instruction=opponent_system_prompt
    )
    
    # --- START OF FIX (ValueError: time) ---
    dirty_previous_history = chat_history[:-1] 
    clean_previous_history = [
        {'role': msg['role'], 'parts': msg['parts']} 
        for msg in dirty_previous_history
    ]
    chat_session = dynamic_chat_model.start_chat(history=clean_previous_history)
    # --- END OF FIX ---
    
    try:
        response = chat_session.send_message(user_input) 
        ai_response_text = response.text
    except Exception as e:
        ai_response_text = f"An error occurred while generating the AI response: {e}"
        print(f"API Error: {e}")
        # Check if it's an API key error
        if "API key" in str(e):
            error_msg = "ERROR: Google API Key is invalid or expired. Please check Settings."
            return (no_update, no_update, None, no_update, 
                    no_update, no_update, no_update, None, 
                    True, error_msg)


    # 5. Add AI response
    ai_message = f"AI ({debate_state['opponent_stance']}): {ai_response_text}"
    current_chat.append(html.P(ai_message, style={'textAlign': 'left'}))
    chat_history.append({'role': 'model', 'parts': [ai_response_text]})
    session_data['chat_history'] = chat_history 
    
    # Return 10 values
    return (current_chat, session_data, None, no_update, 
            results_button_style, send_button_disabled, textarea_disabled, None,
            no_update, no_update)


# --- *** NEW: JUDGE MODE ("Hot-Seat") CALLBACKS *** ---

# Callback 1: Auto-fill Player B's stance
@app.callback(
    Output('player-b-stance-display', 'value'),
    Input('player-a-stance-radio', 'value')
)
def judge_auto_set_stance(player_a_stance):
    if player_a_stance == 'For':
        return 'Against'
    elif player_a_stance == 'Against':
        return 'For'
    return no_update

# Callback 2: Start the Judged Debate
# --- *** MODIFIED: Now checks for API key BEFORE starting debate *** ---
@app.callback(
    [Output('judge-setup-div', 'style'),
     Output('judge-interface-div', 'style'),
     Output('judge-topic-display', 'children'),
     Output('judge-chat-window', 'children'),
     Output('judge-turn-display', 'children'),
     Output('session-storage', 'data', allow_duplicate=True),
     
     # --- NEW POPUP OUTPUTS (add these) ---
     Output('api-key-error-popup', 'displayed', allow_duplicate=True),
     Output('api-key-error-popup', 'message', allow_duplicate=True)
    ],
    Input('start-judge-debate-btn', 'n_clicks'),
    [State('judge-topic-input', 'value'),
     State('judge-turns-input', 'value'),
     State('player-a-name-input', 'value'),
     State('player-a-stance-radio', 'value'),
     State('player-b-name-input', 'value'),
     State('player-b-stance-display', 'value'),
     State('session-storage', 'data')],
    prevent_initial_call=True
)
def start_judged_debate(n_clicks, topic, turns, p_a_name, p_a_stance, p_b_name, p_b_stance, session_data):
    
    session_data = session_data or {}
    
    # --- NEW: Get key from session ---
    google_key = session_data.get('google_key')
    
    # --- NEW: API Key Check ---
    if not google_key:
        error_msg = "ERROR: API Keys not set. Please go to the Settings page."
        # Return 8 values: 
        # - no_update for the first 6
        # - True, error_msg for the popup
        return (no_update, no_update, no_update, no_update, no_update, no_update, 
                True, error_msg)

    # --- Original logic continues below ---
    
    if not all([topic, turns, p_a_name, p_a_stance, p_b_name, p_b_stance]):
        # Return 8 values: 6 no_updates, 2 popup no_updates
        return (no_update, no_update, no_update, no_update, no_update, no_update,
                no_update, no_update) # <-- hide popup

    debate_state = {
        'mode': 'judge', 
        'topic': topic,
        'user_stance': p_a_stance,     # Player A's stance
        'opponent_stance': p_b_stance,   # Player B's stance
        'player_A_name': p_a_name,
        'player_B_name': p_b_name,
        'total_turns': int(turns) * 2,   # Total turns for *both* players
        'current_turn_count': 0,
        'current_player_role': 'user'    # 'user' = Player A, 'model' = Player B
    }
    
    session_data['debate_state'] = debate_state
    session_data['chat_history'] = [] 
    session_data['final_results'] = None
    
    initial_message = html.Div(f"Debate started on: '{topic}'.",
                               style={'fontStyle': 'italic', 'color': 'grey', 'textAlign': 'center'})
    
    turn_display = f"It is {p_a_name}'s turn ({p_a_stance})"
    
    # Return 8 values:
    # - 6 original success values
    # - 2 "no_update" for the popup (to hide it if it was open)
    return ({'display': 'none'}, {'display': 'block'},
            f"Topic: {topic}", [initial_message],
            turn_display, session_data,
            no_update, no_update) # <-- Hide popup on success

# --- *** MODIFIED: Judged turn now triggers popup on error *** ---
@app.callback(
    [Output('judge-chat-window', 'children', allow_duplicate=True),
     Output('session-storage', 'data', allow_duplicate=True),
     Output('judge-turn-display', 'children', allow_duplicate=True),
     Output('judge-loading-output', 'children'),
     Output('timer-store', 'data', allow_duplicate=True), 
     Output('judge-send-argument-btn', 'disabled', allow_duplicate=True),
     Output('user-input-textarea', 'disabled', allow_duplicate=True),
     Output('judge-end-debate-btn', 'style', allow_duplicate=True),
     # --- NEW POPUP OUTPUTS ---
     Output('api-key-error-popup', 'displayed', allow_duplicate=True),
     Output('api-key-error-popup', 'message', allow_duplicate=True)],
    Input('judge-send-argument-btn', 'n_clicks'),
    [State('user-input-textarea', 'value'),
     State('session-storage', 'data'),
     State('judge-chat-window', 'children'),
     State('timer-store', 'data')],
    prevent_initial_call=True
)
def handle_judged_turn(n_clicks, user_input, session_data, current_chat, timer_data):
    current_chat = current_chat if current_chat is not None else []
    
    send_button_disabled = False
    textarea_disabled = False
    end_button_style = {'display': 'none', 'marginTop': '10px'}

    if not user_input or not session_data or 'debate_state' not in session_data:
        # Return 10 values
        return (no_update, no_update, no_update, None, None, 
                no_update, no_update, no_update,
                no_update, no_update)

    debate_state = session_data['debate_state']
    chat_history = session_data.get('chat_history', []) 

    # 1. Get current player info
    current_role = debate_state['current_player_role']
    
    if current_role == 'user': # Player A's turn
        player_name = debate_state['player_A_name']
        player_stance = debate_state['user_stance']
        alignment = 'right'
    else: # Player B's turn
        player_name = debate_state['player_B_name']
        player_stance = debate_state['opponent_stance']
        alignment = 'left'

    # 2. Add message to chat
    timer_string = timer_data or ""
    message_display = f"{player_name} ({player_stance}){f' ({timer_string})' if timer_string else ''}: {user_input}"
    current_chat.append(html.P(message_display, style={'textAlign': alignment}))
    
    chat_history.append({
        'role': current_role, 
        'parts': [user_input], 
        'time': timer_string,
        'player_name': player_name 
    })

    # 3. Increment turn
    debate_state['current_turn_count'] += 1
    
    # 4. Check for end of debate
    if debate_state['current_turn_count'] >= debate_state['total_turns']:
        print("--- Judged debate complete. Calling get_judgment ---")
        
        # --- MODIFIED ERROR HANDLING ---
        google_key = session_data.get('google_key')
        if not google_key:
            error_msg = "ERROR: Google Key not set. Cannot get judgment. Please go to Settings."
            # Return 10 values
            return (no_update, no_update, no_update, None, None, 
                    True, True, no_update, 
                    True, error_msg)

        try:
            # Check for invalid key before proceeding
            genai.configure(api_key=google_key) 
            judgment = get_judgment(debate_state, chat_history, google_key)
        except Exception as e:
            print(f"--- handle_judged_turn CAUGHT AN ERROR: {e} ---")
            # Check if it's an API key error
            if "API key" in str(e):
                error_msg = "ERROR: Google API Key is invalid or expired. Please check Settings."
                return (no_update, no_update, no_update, None, None, 
                        True, True, no_update, 
                        True, error_msg)
            judgment = {'error': f'Judge API/Parsing failed: {e}', 'raw_text': 'N/A'}

        session_data['final_results'] = judgment
        session_data['debate_state_before_completion'] = debate_state 
        session_data['debate_state'] = None 
        session_data['chat_history'] = chat_history

        try:
            save_debate_to_db(
                session_data['active_user'], 
                session_data['debate_state_before_completion'], 
                chat_history, 
                judgment
            )
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to save judged debate to DB: {e}")

        send_button_disabled = True
        textarea_disabled = True
        end_button_style = {'display': 'block', 'marginTop': '10px'}
        turn_display = f"Debate Finished! Click 'End Debate' to see scores."

    else:
        # Not the end, switch turns
        if current_role == 'user':
            debate_state['current_player_role'] = 'model' # Switch to Player B
            next_player_name = debate_state['player_B_name']
            next_player_stance = debate_state['opponent_stance']
        else:
            debate_state['current_player_role'] = 'user' # Switch to Player A
            next_player_name = debate_state['player_A_name']
            next_player_stance = debate_state['user_stance']
        
        turn_display = f"It is {next_player_name}'s turn ({next_player_stance})"

    session_data['debate_state'] = debate_state
    session_data['chat_history'] = chat_history 

    # Return 10 values
    return (current_chat, session_data, turn_display, None, None, 
            send_button_disabled, textarea_disabled, end_button_style,
            no_update, no_update)


# --- *** END OF JUDGE MODE CALLBACKS *** ---


# --- JUDGMENT & SCORING CALLBACKS (Shared) ---

def get_judgment(debate_state, chat_history, google_key):
    import google.generativeai as genai
    
    if not google_key:
        return {"error": "Judge AI key not configured in session."}
        
    try:
        genai.configure(api_key=google_key)
    except Exception as e:
         return {"error": f"Invalid Google API Key: {e}"}
    
    print("--- V11.2: get_judgment HAS BEEN ENTERED ---")
    transcript = ""
    judge_prompt = "" 
    
    try:
        for entry in chat_history:
            role = "User" if entry['role'] == 'user' else "AI"
            
            if entry['role'] == 'user':
                stance = debate_state['user_stance']
            else:
                stance = debate_state['opponent_stance']
                
            transcript += f"{role} ({stance}): {entry['parts'][0]}\n\n"
        
        print("--- V11.2: get_judgment HAS BUILT GENERIC TRANSCRIPT ---")

        judge_prompt = DEBATE_JUDGE_PROMPT.format(
            topic=debate_state['topic'],
            user_stance=debate_state['user_stance'],
            ai_stance=debate_state['opponent_stance'],
            transcript=transcript
        )
    except Exception as e:
        print(f"--- V11.2: ERROR DURING STRING FORMATTING: {e} ---")
        return {"error": f"Judge prompt formatting failed: {e}", "raw_text": "N/A"}

    raw_text = "" 
    print("--- V11.2: get_judgment IS CALLING THE API ---") 
    try:
        forced_config = genai.types.GenerationConfig(
            response_mime_type="application/json" 
        )
        local_json_model = genai.GenerativeModel(
            'gemini-2.0-flash',
            generation_config=forced_config 
        )
        
        try:
            response = local_json_model.generate_content(judge_prompt)
            raw_text = response.text 
            
        except Exception as api_error:
            print(f"Google API call failed or response was invalid: {api_error}")
            try:
                raw_text = str(api_error)
            except:
                raw_text = "Could not get raw response."
            return {"error": f"Judge API/Parsing failed: {api_error}", "raw_text": raw_text}

        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        
        if not json_match:
            print(f"JSON parsing failed: No JSON object found in raw text.")
            print(f"Raw AI Output: {raw_text}")
            return {"error": "Failed to parse judgment: No JSON object found.", "raw_text": raw_text}

        json_text = json_match.group(0) 
        
        try:
            judgment = json.loads(json_text)
            return judgment # Success!
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed even after extraction: {e}")
            print(f"Extracted Text: {json_text}")
            return {"error": f"Failed to parse judgment: {e}", "raw_text": raw_text}

    except Exception as e:
        print(f"CRITICAL: Unhandled error in get_judgment API call: {e}")
        return {"error": f"Unhandled judge error: {e}", "raw_text": raw_text}


# This is only called for PRACTICE mode
def update_user_stats(username, judgment):
    print("--- Calling NEW 'safe' update_user_stats function ---")
    
    if not judgment or 'scores' not in judgment or 'reasoning' not in judgment:
        print(f"Skipping stats update for {username} due to malformed judgment.")
        return

    con = get_db_connection()
    ph = '?' if isinstance(con, sqlite3.Connection) else '%s'
    
    try:
        sql_read_stats = f"SELECT * FROM user_stats WHERE username = {ph}"
        stats_df = pd.read_sql_query(
            sql_read_stats,
            con,
            params=(username,)
        )
        
        if stats_df.empty:
            print(f"User {username} not found in stats table.")
            return

        user_stats = stats_df.iloc[0].to_dict()
        winner = judgment['reasoning'].get('overallWinner', 'Draw')
        
        if winner == 'User':
            user_stats['debates_won'] += 1
        elif winner == 'AI':
            user_stats['debates_lost'] += 1
        else:
            user_stats['debates_drawn'] += 1

        user_scores = judgment['scores'].get('User', {})
        total_debates = user_stats['debates_won'] + user_stats['debates_lost'] + user_stats['debates_drawn']

        # --- *** START OF FIX *** ---
        # The 'skill' (camelCase) is for the JSON dict 'user_scores'
        # The 'stat_col_db' (lowercase) is for the DB dict 'user_stats'
        for skill in ['logicalConsistency', 'evidenceAndExamples', 'clarityAndConcision',
                      'rebuttalEffectiveness', 'overallPersuasiveness']:
            
            # DB key is lowercase, e.g., "avg_logicalconsistency"
            stat_col_db = f'avg_{skill.lower()}' 

            # Read current avg from DB dict using lowercase key
            current_avg = user_stats[stat_col_db] 
            
            # Get new score from JSON dict using camelCase key
            new_score = user_scores.get(skill, current_avg) 
            
            try:
                new_score = float(new_score)
            except (ValueError, TypeError):
                new_score = current_avg 
            
            if total_debates > 0:
                new_avg = ((current_avg * (total_debates - 1)) + new_score) / total_debates
                # Write new avg to DB dict using lowercase key
                user_stats[stat_col_db] = new_avg
        
        cur = con.cursor()
        
        sql_update_stats = f"""
            UPDATE user_stats SET
                debates_won = {ph}, debates_lost = {ph}, debates_drawn = {ph},
                avg_logicalconsistency = {ph}, avg_evidenceandexamples = {ph},
                avg_clarityandconcision = {ph}, avg_rebuttaleffectiveness = {ph},
                avg_overallpersuasiveness = {ph}
            WHERE username = {ph}
            """
        
        cur.execute(
            sql_update_stats,
            (
                user_stats['debates_won'], user_stats['debates_lost'], user_stats['debates_drawn'],
                user_stats['avg_logicalconsistency'], user_stats['avg_evidenceandexamples'],
                user_stats['avg_clarityandconcision'], user_stats['avg_rebuttaleffectiveness'],
                user_stats['avg_overallpersuasiveness'],
                username
            )
        )
        # --- *** END OF FIX *** ---
        con.commit()
        print(f"Stats updated for {username} in the database.")
    except Exception as e:
        con.rollback()
        print(f"Error updating stats for {username}: {e}")
    finally:
        con.close()

# --- *** DASHBOARD CALLBACK 1 (PRACTICE) *** ---
@app.callback(
    Output('practice-dashboard-content', 'children'),
    [Input('url', 'pathname')],
    [State('session-storage', 'data')]
)
def render_practice_dashboard(pathname, session_data):
    if pathname != '/practice-results' or not session_data or 'active_user' not in session_data:
        return no_update

    username = session_data['active_user']
    final_results = session_data.get('final_results')
    saved_state = session_data.get('debate_state_before_completion', {})

    def safe_get(dct, keys, default=None):
        for key in keys:
            try:
                dct = dct[key]
            except (KeyError, TypeError, IndexError):
                return default
        return dct

    con = get_db_connection()
    ph = '?' if isinstance(con, sqlite3.Connection) else '%s'
    
    try:
        cur = con.cursor()
        sql_select_stats = f"SELECT * FROM user_stats WHERE username = {ph}"
        cur.execute(sql_select_stats, (username,))
        user_stats_row = cur.fetchone()
        if user_stats_row is None:
            user_stats = { 'debates_won': 0, 'debates_lost': 0, 'debates_drawn': 0,
                           'avg_logicalconsistency': 0, 'avg_evidenceandexamples': 0,
                           'avg_clarityandconcision': 0, 'avg_rebuttaleffectiveness': 0,
                           'avg_overallpersuasiveness': 0 }
        else:
            user_stats = user_stats_row
    except Exception as e:
        print(f"Error reading dashboard stats: {e}")
        return html.P("Error loading user statistics.")
    finally:
        con.close()

    gauge_colors = { "gradient": True, "colorStops": [
            {"offset": 0, "color": "#533483"},
            {"offset": 0.5, "color": "#16213e"},
            {"offset": 1, "color": "#e94560"}
    ]}
    
    # --- ALL-TIME STATS LAYOUT (for the logged-in user) ---
    layout = [
        html.H4(f"Your All-Time Performance ({username})"),
        html.Div([
            # --- *** START OF FIX *** ---
            # Keys must be lowercase to match the database
            daq.Gauge(label="Logical Consistency", value=user_stats['avg_logicalconsistency'], max=10, min=0, color=gauge_colors),
            daq.Gauge(label="Evidence & Examples", value=user_stats['avg_evidenceandexamples'], max=10, min=0, color=gauge_colors),
            daq.Gauge(label="Clarity & Concision", value=user_stats['avg_clarityandconcision'], max=10, min=0, color=gauge_colors),
            daq.Gauge(label="Rebuttal Effectiveness", value=user_stats['avg_rebuttaleffectiveness'], max=10, min=0, color=gauge_colors),
            daq.Gauge(label="Overall Persuasiveness", value=user_stats['avg_overallpersuasiveness'], max=10, min=0, color=gauge_colors),
            # --- *** END OF FIX *** ---
        ], className='gauge-grid'),
        html.P(f"Record (W-L-D): {user_stats['debates_won']}-{user_stats['debates_lost']}-{user_stats['debates_drawn']}",
               style={'textAlign': 'center', 'fontWeight': 'bold', 'marginTop': '20px', 'fontSize': '1.2rem'}),
        html.Hr(),
    ]

    # --- POST-DEBATE BREAKDOWN ---
    if final_results:
        if "error" in final_results:
            layout.append(html.Div([
                html.H4("Post-Debate Breakdown", style={'color': 'red'}),
                html.P(f"Details: {final_results['error']}"),
                html.Code(f"Raw AI Output: {final_results.get('raw_text', 'N/A')}", style={'whiteSpace': 'pre-wrap'})
            ]))
        else:
            chat_history = session_data.get('chat_history', [])
            scores = safe_get(final_results, ['scores'], {})
            reasoning = safe_get(final_results, ['reasoning'], {})

            # --- Practice Mode Logic ---
            user_stance = saved_state.get('user_stance', 'User')
            ai_stance = saved_state.get('opponent_stance', 'AI')
            
            winner = reasoning.get('overallWinner', 'N/A')
            winner_status = 'Won' if winner == 'User' else 'Lost' if winner == 'AI' else 'Drew' if winner == 'Draw' else 'N/A'
            outcome_title = f"Outcome: You {winner_status}"
            
            user_header = "Your Score"
            ai_header = "AI's Score"
            
            user_display = f"YOU ({user_stance})"
            ai_display = f"AI ({ai_stance})"
            
            feedback_text = reasoning.get('constructiveFeedbackUser', 'N/A')
            feedback_title = "Feedback for You:"
            
            # --- START: CHAT TRANSCRIPT RENDERING LOGIC ---
            chat_divs = []
            for entry in chat_history:
                role = entry.get('role', 'system')
                text = entry['parts'][0]
                time_string = entry.get('time')
                time_display = f" ({time_string})" if time_string else ""
                
                if role == 'user':
                    message_content = f"{user_display}{time_display}: {text}"
                    style = {'textAlign': 'right', 'color': '#111827', 'padding': '5px 0'} 
                elif role == 'model':
                    message_content = f"{ai_display}{time_display}: {text}"
                    style = {'textAlign': 'left', 'color': '#374151', 'padding': '5px 0'} 
                else:
                    message_content = f"System: {text}"
                    style = {'textAlign': 'center', 'fontStyle': 'italic', 'color': '#6b7280', 'padding': '5px 0'}

                chat_divs.append(html.P(message_content, style=style))
            # --- END: CHAT TRANSCRIPT RENDERING LOGIC ---

            # --- EXTENDED LAYOUT WITH BREAKDOWN AND TRANSCRIPT ---
            layout.extend([
                html.H4("Post-Debate Breakdown"), 
                html.H3(outcome_title, style={'textAlign': 'center', 'marginTop': '10px'}),
                
                html.Table([
                    html.Tr([html.Th("Metric"), html.Th(user_header), html.Th(ai_header)]),
                    html.Tr([html.Td("Logical Consistency"), html.Td(safe_get(scores, ['User', 'logicalConsistency'])), html.Td(safe_get(scores, ['AI', 'logicalConsistency']))]),
                    html.Tr([html.Td("Evidence & Examples"), html.Td(safe_get(scores, ['User', 'evidenceAndExamples'])), html.Td(safe_get(scores, ['AI', 'evidenceAndExamples']))]),
                    html.Tr([html.Td("Clarity & Concision"), html.Td(safe_get(scores, ['User', 'clarityAndConcision'])), html.Td(safe_get(scores, ['AI', 'clarityAndConcision']))]),
                    html.Tr([html.Td("Rebuttal Effectiveness"), html.Td(safe_get(scores, ['User', 'rebuttalEffectiveness'])), html.Td(safe_get(scores, ['AI', 'rebuttalEffectiveness']))]),
                    html.Tr([html.Td("Overall Persuasiveness"), html.Td(safe_get(scores, ['User', 'overallPersuasiveness'])), html.Td(safe_get(scores, ['AI', 'overallPersuasiveness']))]),
                ], className='dashboard-table'),

                html.Details([
                    html.Summary("Detailed Reasoning"),
                    html.P(f"Strongest ({user_header.split(' ')[0]}): {reasoning.get('strongestArgumentUser', 'N/A')}"),
                    html.P(f"Strongest ({ai_header.split(' ')[0]}): {reasoning.get('strongestArgumentAI', 'N/A')}"),
                    html.P(f"Weakest ({user_header.split(' ')[0]}): {reasoning.get('weakestArgumentUser', 'N/A')}"),
                    html.P(f"Weakest ({ai_header.split(' ')[0]}): {reasoning.get('weakestArgumentAI', 'N/A')}"),
                    html.P(f"Rebuttal Analysis: {reasoning.get('rebuttalAnalysis', 'N/A')}"),
                    html.P(
                        f"{feedback_title} {feedback_text}", 
                        style={'fontWeight': 'bold', 'marginTop': '10px'}
                    )
                ]),
                
                html.Hr(),
                html.H4("Full Debate Transcript Review"),
                html.Details(
                    className='transcript-details-review', 
                    open=False, 
                    children=[
                        html.Summary("Click to review the full conversation"),
                        html.Div(chat_divs,
                                 style={
                                     'backgroundColor': 'white', 
                                     'border': '1px solid #ccc',
                                     'borderRadius': '8px',
                                     'padding': '15px',
                                     'maxHeight': '400px',
                                     'overflowY': 'auto',
                                     'marginTop': '10px'
                                 }
                        )
                    ]
                )
            ])
    else:
        layout.append(html.P("Complete a debate to see the results here.", style={'textAlign': 'center', 'fontStyle': 'italic'}))

    layout.append(html.Hr(style={'marginTop': '30px'}))
    layout.append(
        html.Div([
            html.Button('Debate Again (Practice)', id='debate-again-button', n_clicks=0, className='btn btn-secondary'),
            html.Button('Exit to Home', id='dashboard-exit-home-button', n_clicks=0, className='btn btn-secondary', style={'marginTop': '10px'})
        ], style={'textAlign': 'center', 'marginTop': '20px'}) 
    )
    
    return layout


# --- *** MODIFIED: DASHBOARD CALLBACK 2 (JUDGE) *** ---
@app.callback(
    Output('judge-dashboard-content', 'children'),
    Input('url', 'pathname'),
    State('session-storage', 'data')
)
def render_judge_dashboard(pathname, session_data):
    if pathname != '/judge-results' or not session_data or 'active_user' not in session_data:
        return no_update

    final_results = session_data.get('final_results')
    saved_state = session_data.get('debate_state_before_completion', {})
    
    layout = [] # Start with an empty layout

    def safe_get(dct, keys, default=None):
        for key in keys:
            try:
                dct = dct[key]
            except (KeyError, TypeError, IndexError):
                return default
        return dct

    # --- POST-DEBATE BREAKDOWN ---
    if final_results:
        if "error" in final_results:
            layout.append(html.Div([
                html.H4("Post-Debate Breakdown", style={'color': 'red'}),
                html.P(f"Details: {final_results['error']}"),
                html.Code(f"Raw AI Output: {final_results.get('raw_text', 'N/A')}", style={'whiteSpace': 'pre-wrap'})
            ]))
        else:
            chat_history = session_data.get('chat_history', [])
            scores = safe_get(final_results, ['scores'], {})
            reasoning = safe_get(final_results, ['reasoning'], {})

            # --- Judge Mode Logic ---
            player_A_name = saved_state.get('player_A_name', 'Player A')
            player_B_name = saved_state.get('player_B_name', 'Player B')
            user_stance = saved_state.get('user_stance', 'For')
            ai_stance = saved_state.get('opponent_stance', 'Against')
            
            winner = reasoning.get('overallWinner', 'Draw')
            winner_name = player_A_name if winner == 'User' else player_B_name if winner == 'AI' else 'Draw'
            outcome_title = f"Outcome: {winner_name} Wins!" if winner != 'Draw' else "Outcome: Draw"

            user_header = f"{player_A_name}'s Score"
            ai_header = f"{player_B_name}'s Score"
            
            user_display = f"{player_A_name} ({user_stance})"
            ai_display = f"{player_B_name} ({ai_stance})"
            
            feedback_A_text = reasoning.get('constructiveFeedbackUser', 'N/A')
            feedback_A_title = f"Feedback for {player_A_name}:"
            feedback_B_text = reasoning.get('constructiveFeedbackAI', 'N/A')
            feedback_B_title = f"Feedback for {player_B_name}:"
            
            # --- START: CHAT TRANSCRIPT RENDERING LOGIC ---
            chat_divs = []
            for entry in chat_history:
                role = entry.get('role', 'system')
                text = entry['parts'][0]
                time_string = entry.get('time')
                time_display = f" ({time_string})" if time_string else ""
                
                if role == 'user': # Player A
                    message_content = f"{user_display}{time_display}: {text}"
                    style = {'textAlign': 'right', 'color': '#111827', 'padding': '5px 0'} 
                elif role == 'model': # Player B
                    message_content = f"{ai_display}{time_display}: {text}"
                    style = {'textAlign': 'left', 'color': '#374151', 'padding': '5px 0'} 
                else:
                    message_content = f"System: {text}"
                    style = {'textAlign': 'center', 'fontStyle': 'italic', 'color': '#6b7280', 'padding': '5px 0'}

                chat_divs.append(html.P(message_content, style=style))
            # --- END: CHAT TRANSCRIPT RENDERING LOGIC ---

            # --- EXTENDED LAYOUT WITH BREAKDOWN AND TRANSCRIPT ---
            layout.extend([
                html.H4("Post-Debate Breakdown"), 
                html.H3(outcome_title, style={'textAlign': 'center', 'marginTop': '10px'}),
                
                html.Table([
                    html.Tr([html.Th("Metric"), html.Th(user_header), html.Th(ai_header)]),
                    html.Tr([html.Td("Logical Consistency"), html.Td(safe_get(scores, ['User', 'logicalConsistency'])), html.Td(safe_get(scores, ['AI', 'logicalConsistency']))]),
                    html.Tr([html.Td("Evidence & Examples"), html.Td(safe_get(scores, ['User', 'evidenceAndExamples'])), html.Td(safe_get(scores, ['AI', 'evidenceAndExamples']))]),
                    html.Tr([html.Td("Clarity & Concision"), html.Td(safe_get(scores, ['User', 'clarityAndConcision'])), html.Td(safe_get(scores, ['AI', 'clarityAndConcision']))]),
                    html.Tr([html.Td("Rebuttal Effectiveness"), html.Td(safe_get(scores, ['User', 'rebuttalEffectiveness'])), html.Td(safe_get(scores, ['AI', 'rebuttalEffectiveness']))]),
                    html.Tr([html.Td("Overall Persuasiveness"), html.Td(safe_get(scores, ['User', 'overallPersuasiveness'])), html.Td(safe_get(scores, ['AI', 'overallPersuasiveness']))]),
                ], className='dashboard-table'),

                html.Details([
                    html.Summary("Detailed Reasoning"),
                    html.P(f"Strongest ({player_A_name}): {reasoning.get('strongestArgumentUser', 'N/A')}"),
                    html.P(f"Strongest ({player_B_name}): {reasoning.get('strongestArgumentAI', 'N/A')}"),
                    html.P(f"Weakest ({player_A_name}): {reasoning.get('weakestArgumentUser', 'N/A')}"),
                    html.P(f"Weakest ({player_B_name}): {reasoning.get('weakestArgumentAI', 'N/A')}"),
                    html.P(f"Rebuttal Analysis: {reasoning.get('rebuttalAnalysis', 'N/A')}"),
                    
                    html.P(
                        f"{feedback_A_title} {feedback_A_text}", 
                        style={'fontWeight': 'bold', 'marginTop': '10px'}
                    ),
                    html.P(
                        f"{feedback_B_title} {feedback_B_text}", 
                        style={'fontWeight': 'bold', 'marginTop': '10px'}
                    )
                ]),
                
                html.Hr(),
                html.H4("Full Debate Transcript Review"),
                html.Details(
                    className='transcript-details-review', 
                    open=False, 
                    children=[
                        html.Summary("Click to review the full conversation"),
                        html.Div(chat_divs,
                                 style={
                                     'backgroundColor': 'white', 
                                     'border': '1px solid #ccc',
                                     'borderRadius': '8px',
                                     'padding': '15px',
                                     'maxHeight': '400px',
                                     'overflowY': 'auto',
                                     'marginTop': '10px'
                                 }
                        )
                    ]
                )
            ])
    else:
        layout.append(html.P("Complete a debate to see the results here.", style={'textAlign': 'center', 'fontStyle': 'italic'}))

    layout.append(html.Hr(style={'marginTop': '30px'}))
    
    layout.append(
        html.Div([
            html.Button('Debate Again (Judge Mode)', id='judge-again-button', n_clicks=0, className='btn btn-primary'),
            html.Button('Exit to Home', id='dashboard-exit-home-button', n_clicks=0, className='btn btn-secondary', style={'marginTop': '10px'})
        ], style={'textAlign': 'center', 'marginTop': '20px'}) 
    )
    
    return layout

# --- *** NEW: HISTORY PAGE CALLBACKS *** ---

# Callback 1: Load the list of past debates into the dropdown
@app.callback(
    Output('history-dropdown', 'options'),
    Input('url', 'pathname'),
    State('session-storage', 'data')
)
def load_history_dropdown(pathname, session_data):
    if pathname != '/history' or not session_data:
        return []

    username = session_data.get('active_user')
    if not username:
        return []

    options = []
    con = get_db_connection()
    ph = '?' if isinstance(con, sqlite3.Connection) else '%s'
    sql_select = f"SELECT id, debate_topic, debate_mode, timestamp FROM debate_history WHERE username = {ph} ORDER BY timestamp DESC"
    
    try:
        cur = con.cursor()
        cur.execute(sql_select, (username,))
        history = cur.fetchall()
        
        for item in history:
            
            # --- START OF TIMEZONE FIX ---
            ts_obj = pd.to_datetime(item['timestamp'])
            
            if ts_obj.tzinfo is None:
                # It's a naive timestamp (from SQLite), localize it to UTC
                ts_obj = ts_obj.tz_localize('UTC')
            
            # Now it's timezone-aware, so convert to IST
            ts = ts_obj.tz_convert('Asia/Kolkata').strftime('%Y-%m-%d %I:%M %p')
            # --- END OF TIMEZONE FIX ---
            
            mode = "Practice Mode" if item['debate_mode'] == 'practice' else "Judge Mode"
            topic = item['debate_topic']
            
            label = f"{ts} - {mode} - {topic}"
            value = item['id']
            options.append({'label': label, 'value': value})
            
    except Exception as e:
        print(f"Error loading debate history: {e}")
    finally:
        con.close()
        
    if not options:
        return [{'label': 'No debates found in your history.', 'value': '', 'disabled': True}]
        
    return options

# Callback 2: Load a selected debate from history into session and redirect
@app.callback(
    [Output('session-storage', 'data', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True),
     Output('history-content-container', 'children')],
    Input('history-dropdown', 'value'),
    State('session-storage', 'data'),
    prevent_initial_call=True
)
def load_selected_history_to_session(selected_debate_id, session_data):
    if not selected_debate_id:
        return no_update, no_update, no_update

    if not session_data:
        return no_update, '/login', "Session expired. Please log in." # Should not happen

    username = session_data.get('active_user')
    
    con = get_db_connection()
    ph = '?' if isinstance(con, sqlite3.Connection) else '%s'
    sql_select = f"SELECT * FROM debate_history WHERE id = {ph} AND username = {ph}"

    try:
        cur = con.cursor()
        cur.execute(sql_select, (selected_debate_id, username))
        debate_record = cur.fetchone()
        
        if debate_record:
            # Load the JSON strings from the DB
            debate_state = json.loads(debate_record['debate_state'])
            chat_history = json.loads(debate_record['chat_history'])
            final_results = json.loads(debate_record['final_results'])
            debate_mode = debate_record['debate_mode']
            
            # --- CRITICAL: Overwrite the session with this old data ---
            session_data['debate_state_before_completion'] = debate_state
            session_data['chat_history'] = chat_history
            session_data['final_results'] = final_results
            session_data['debate_state'] = None # Ensure no live debate is active
            
            # Determine where to redirect
            if debate_mode == 'practice':
                redirect_url = '/practice-results'
            else:
                redirect_url = '/judge-results'
                
            return session_data, redirect_url, None
            
        else:
            return no_update, no_update, html.P("Error: Could not find that debate.", style={'color': 'red'})

    except Exception as e:
        print(f"Error loading selected debate: {e}")
        return no_update, no_update, html.P(f"An error occurred: {e}", style={'color': 'red'})
    finally:
        con.close()