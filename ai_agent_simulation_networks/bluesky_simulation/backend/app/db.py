import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("simulation.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        handle TEXT PRIMARY KEY,
        did TEXT,
        display_name TEXT,
        description TEXT,
        avatar_url TEXT,
        is_seed BOOLEAN,
        created_at TIMESTAMP
    )
    ''')
    
    # Posts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS posts (
        uri TEXT PRIMARY KEY,
        cid TEXT,
        author_handle TEXT,
        text TEXT,
        created_at TEXT,
        reply_parent TEXT,
        reply_root TEXT,
        is_seed BOOLEAN,
        insert_timestamp TIMESTAMP,
        turn INTEGER,
        FOREIGN KEY(author_handle) REFERENCES users(handle)
    )
    ''')
    
    # Agent Profiles table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agent_profiles (
        handle TEXT PRIMARY KEY,
        original_handle TEXT,
        FOREIGN KEY(original_handle) REFERENCES users(handle)
    )
    ''')
    
    # Agent Bios table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agent_bios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_handle TEXT,
        bio_json TEXT,
        FOREIGN KEY(agent_handle) REFERENCES agent_profiles(handle)
    )
    ''')
    
    # Agent Likes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agent_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_handle TEXT,
        liked_post_uri TEXT,
        liked_post_author TEXT,
        liked_post_text TEXT,
        reason TEXT,
        turn INTEGER,
        timestamp TIMESTAMP,
        FOREIGN KEY(agent_handle) REFERENCES agent_profiles(handle)
    )
    ''')
    
    # Simulation State table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS simulation_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        current_turn INTEGER DEFAULT 0,
        is_running BOOLEAN DEFAULT 0,
        total_rounds INTEGER DEFAULT 10,
        session_id TEXT
    )
    ''')
    cursor.execute("PRAGMA table_info(simulation_state)")
    simulation_state_columns = [row[1] for row in cursor.fetchall()]
    if "session_id" not in simulation_state_columns:
        cursor.execute("ALTER TABLE simulation_state ADD COLUMN session_id TEXT")
    
    # Initialize simulation state if not exists
    cursor.execute('INSERT OR IGNORE INTO simulation_state (id, current_turn, is_running, total_rounds, session_id) VALUES (1, 0, 0, 10, "")')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
