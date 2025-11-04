import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database on Render
    or a local SQLite DB for development (if DATABASE_URL is not set).
    """
    DATABASE_URL = os.environ.get('DATABASE_URL')

    if DATABASE_URL:
        # --- PRODUCTION (Render) ---
        print("Connecting to PostgreSQL (Render)...")
        con = psycopg2.connect(DATABASE_URL)
        con.cursor_factory = DictCursor 
    else:
        # --- LOCAL (Development) ---
        print("WARNING: DATABASE_URL not set. Connecting to local app_data.db...")
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DB_FILE = os.path.join(BASE_DIR, 'app_data.db')
        con = sqlite3.connect(DB_FILE)
        con.row_factory = sqlite3.Row
    
    return con


def initialize_database():
    """
    Connects to the database and creates the necessary tables
    if they do not already exist.
    This script is safe to run multiple times.
    """
    
    try:
        con = get_db_connection()
        cur = con.cursor()
    except Exception as e:
        print(f"FATAL: Could not connect to the database: {e}", file=sys.stderr)
        sys.exit(1) 

    print("Connection successful. Creating tables if they do not exist...")

    if isinstance(con, psycopg2.extensions.connection):
        db_type = "postgres"
    else:
        db_type = "sqlite"

    
    if db_type == "postgres":
        users_pk = "id SERIAL PRIMARY KEY"
        stats_pk = "id SERIAL PRIMARY KEY"
        history_pk = "id SERIAL PRIMARY KEY" # <-- NEW
        float_type = "FLOAT"
        timestamp_type = "TIMESTAMP WITH TIME ZONE" # <-- NEW
        fkey_stats = "FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE"
        fkey_history = "FOREIGN KEY (username) REFERENCES users (username) ON DELETE SET NULL" # <-- NEW
    else: # sqlite
        users_pk = "id INTEGER PRIMARY KEY AUTOINCREMENT"
        stats_pk = "id INTEGER PRIMARY KEY AUTOINCREMENT"
        history_pk = "id INTEGER PRIMARY KEY AUTOINCREMENT" # <-- NEW
        float_type = "REAL"
        timestamp_type = "DATETIME" # <-- NEW
        fkey_stats = "FOREIGN KEY (username) REFERENCES users (username)"
        fkey_history = "FOREIGN KEY (username) REFERENCES users (username)" # <-- NEW


    sql_create_users_table = f"""
    CREATE TABLE IF NOT EXISTS users (
        {users_pk},
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );
    """
    
    sql_create_stats_table = f"""
    CREATE TABLE IF NOT EXISTS user_stats (
        {stats_pk},
        username TEXT UNIQUE NOT NULL,
        debates_won INTEGER DEFAULT 0,
        debates_lost INTEGER DEFAULT 0,
        debates_drawn INTEGER DEFAULT 0,
        avg_logicalConsistency {float_type} DEFAULT 0.0,
        avg_evidenceAndExamples {float_type} DEFAULT 0.0,
        avg_clarityAndConcision {float_type} DEFAULT 0.0,
        avg_rebuttalEffectiveness {float_type} DEFAULT 0.0,
        avg_overallPersuasiveness {float_type} DEFAULT 0.0,
        {fkey_stats}
    );
    """

    # --- *** NEW: DEBATE HISTORY TABLE *** ---
    # This table will store the transcript of every completed debate
    sql_create_history_table = f"""
    CREATE TABLE IF NOT EXISTS debate_history (
        {history_pk},
        username TEXT,
        debate_mode TEXT NOT NULL,
        debate_topic TEXT,
        debate_state TEXT,
        chat_history TEXT,
        final_results TEXT,
        timestamp {timestamp_type} DEFAULT CURRENT_TIMESTAMP,
        {fkey_history}
    );
    """
    # --- *** END NEW TABLE *** ---

    try:
        print(f"Using {db_type} syntax.")
        
        print("Creating/Checking 'users' table...")
        cur.execute(sql_create_users_table)
        
        print("Creating/Checking 'user_stats' table...")
        cur.execute(sql_create_stats_table)
        
        # --- NEW ---
        print("Creating/Checking 'debate_history' table...")
        cur.execute(sql_create_history_table)
        
        con.commit()
        print("\nAll tables created successfully (or already existed).")
        
    except Exception as e:
        print(f"An error occurred while creating tables: {e}", file=sys.stderr)
        con.rollback()
    finally:
        con.close()
        print("Database connection closed.")

# This makes the script executable by running 'python db_init.py'
if __name__ == "__main__":
    initialize_database()