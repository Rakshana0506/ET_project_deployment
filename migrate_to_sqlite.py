import pandas as pd
import sqlite3
import os

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'app_data.db')
USERS_CSV = os.path.join(BASE_DIR, 'users.csv')
STATS_CSV = os.path.join(BASE_DIR, 'user_stats.csv')
PLAYERS_CSV = os.path.join(BASE_DIR, 'players.csv') # Path for lobby feature 

# --- Define the new database schema ---
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    name TEXT,
    email TEXT,
    username TEXT PRIMARY KEY,
    password TEXT
);

CREATE TABLE IF NOT EXISTS user_stats (
    username TEXT PRIMARY KEY,
    debates_won INTEGER DEFAULT 0,
    debates_lost INTEGER DEFAULT 0,
    debates_drawn INTEGER DEFAULT 0,
    avg_logicalConsistency REAL DEFAULT 0.0,
    avg_evidenceAndExamples REAL DEFAULT 0.0,
    avg_clarityAndConcision REAL DEFAULT 0.0,
    avg_rebuttalEffectiveness REAL DEFAULT 0.0,
    avg_overallPersuasiveness REAL DEFAULT 0.0,
    FOREIGN KEY(username) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS players (
    username TEXT PRIMARY KEY,
    FOREIGN KEY(username) REFERENCES users(username)
);
"""

def migrate():
    print(f"Creating new database at {DB_FILE}...")
    # Connect to (and create) the database
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    # --- 1. Create the tables ---
    try:
        cur.executescript(SCHEMA_SQL)
        print("Database tables created successfully.")
    except sqlite3.Error as e:
        print(f"An error occurred while creating tables: {e}")
        con.close()
        return

    # --- 2. Migrate users.csv ---
    try:
        if os.path.exists(USERS_CSV):
            users_df = pd.read_csv(USERS_CSV) 
            users_df.to_sql('users', con, if_exists='append', index=False)
            print(f"Successfully migrated {len(users_df)} users from users.csv. ")
        else:
            print("users.csv not found, skipping.")
    except Exception as e:
        print(f"Error migrating users.csv: {e}")

    # --- 3. Migrate user_stats.csv (with cleanup) ---
    try:
        if os.path.exists(STATS_CSV):
            # These are the only columns your code actually uses
            required_cols = [
                'username', 'debates_won', 'debates_lost', 'debates_drawn',
                'avg_logicalConsistency', 'avg_evidenceAndExamples',
                'avg_clarityAndConcision', 'avg_rebuttalEffectiveness',
                'avg_overallPersuasiveness'
            ]
            
            # Read the messy CSV 
            stats_df_raw = pd.read_csv(STATS_CSV) 
            
            # Create a clean DataFrame with just the columns we need
            stats_df_clean = pd.DataFrame(columns=required_cols)
            
            # Copy over data for columns that exist
            for col in required_cols:
                if col in stats_df_raw.columns:
                    stats_df_clean[col] = stats_df_raw[col]
            
            # Clean up NaN/missing values from the CSV, filling with 0
            stats_df_clean = stats_df_clean.fillna(0)

            # Convert types to match database
            stats_df_clean['debates_won'] = pd.to_numeric(stats_df_clean['debates_won'], errors='coerce').fillna(0).astype(int)
            stats_df_clean['debates_lost'] = pd.to_numeric(stats_df_clean['debates_lost'], errors='coerce').fillna(0).astype(int)
            stats_df_clean['debates_drawn'] = pd.to_numeric(stats_df_clean['debates_drawn'], errors='coerce').fillna(0).astype(int)
            
            float_cols = [col for col in required_cols if col.startswith('avg_')]
            for col in float_cols:
                 stats_df_clean[col] = pd.to_numeric(stats_df_clean[col], errors='coerce').fillna(0.0).astype(float)

            stats_df_clean.to_sql('user_stats', con, if_exists='append', index=False)
            print(f"Successfully migrated and cleaned {len(stats_df_clean)} user stats. ")
        else:
            print("user_stats.csv not found, skipping.")
    except Exception as e:
        print(f"Error migrating user_stats.csv: {e}")

    # --- 4. Migrate players.csv ---
    try:
        if os.path.exists(PLAYERS_CSV):
            players_df = pd.read_csv(PLAYERS_CSV) 
            players_df.to_sql('players', con, if_exists='append', index=False)
            print(f"Successfully migrated {len(players_df)} players from players.csv. ")
        else:
            print("players.csv not found, skipping.")
            
    except Exception as e:
        print(f"Error migrating players.csv: {e}")

    # --- 5. Commit changes and close ---
    con.commit()
    con.close()
    print("\nMigration complete! Your 'app_data.db' file is ready.")
    print("You can now replace your callbacks.py file with the new database-enabled version.")

if __name__ == "__main__":
    migrate()