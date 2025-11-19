#!/usr/bin/env python3
"""
Quick test script to verify the simulation backend is working correctly.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("backend/simulation.db")

def test_database():
    print("Testing database...")
    
    if not DB_PATH.exists():
        print("❌ Database not found. Run ingestion first.")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check users
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_seed = 1")
    user_count = cursor.fetchone()[0]
    print(f"✓ Found {user_count} seed users")
    
    # Check posts
    cursor.execute("SELECT COUNT(*) FROM posts WHERE is_seed = 1")
    post_count = cursor.fetchone()[0]
    print(f"✓ Found {post_count} seed posts")
    
    # Check agents
    cursor.execute("SELECT COUNT(*) FROM agent_profiles")
    agent_count = cursor.fetchone()[0]
    print(f"✓ Found {agent_count} agent profiles")
    
    # Check bios
    cursor.execute("SELECT COUNT(*) FROM agent_bios")
    bio_count = cursor.fetchone()[0]
    print(f"✓ Found {bio_count} agent bios")
    
    # Check simulation state
    cursor.execute("SELECT current_turn, total_rounds FROM simulation_state WHERE id = 1")
    state = cursor.fetchone()
    if state:
        print(f"✓ Simulation state: Turn {state[0]}/{state[1]}")
    
    conn.close()
    
    if user_count > 0 and agent_count > 0:
        print("\n✅ Database looks good!")
        return True
    else:
        print("\n⚠️  Database needs data. Run ingestion and agent generation.")
        return False

if __name__ == "__main__":
    test_database()
