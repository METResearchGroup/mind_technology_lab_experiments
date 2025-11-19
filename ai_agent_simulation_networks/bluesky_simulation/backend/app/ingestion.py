import asyncio
from datetime import datetime
from app.bluesky_client import BlueskyClient
from app.db import get_db_connection, init_db
from app.models import BlueskyUser, BlueskyPost

TARGET_PROFILES = [
    "aoc.bsky.social",
    "did:plc:52g2kvtkicy7eg5u4s46nr52",
    "did:plc:zipphihu644mxj7qjafvwwun",
    "did:plc:upw5n2uwhzubjajdtqaufsek",
    "did:plc:xl3w4e5jxslqeaglaqit2ql3",
    "did:plc:2q2hs5o42jhbd23pp6lkiauh",
    "did:plc:7i3fhorekojhdjhkbln7q7gq",
    "did:plc:jg7zvku4khzmvyjwbzv4lnly",
    "did:plc:sbua2wxukvrbmpusje7zpp7s",
    "did:plc:y5xyloyy7s4a2bwfeimj7r3b"
]

def ingest_data():
    print("Initializing database...")
    init_db()
    
    print("Logging into Bluesky...")
    client = BlueskyClient()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for actor in TARGET_PROFILES:
        print(f"Processing {actor}...")
        
        # 1. Get Profile
        profile_data = client.get_profile(actor)
        if not profile_data:
            continue
            
        user = BlueskyUser(
            handle=profile_data['handle'],
            did=profile_data['did'],
            display_name=profile_data.get('display_name'),
            description=profile_data.get('description'),
            avatar_url=profile_data.get('avatar'),
            is_seed=True
        )
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (handle, did, display_name, description, avatar_url, is_seed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user.handle, user.did, user.display_name, user.description, user.avatar_url, user.is_seed, user.created_at))
        
        # 2. Get Posts
        posts_data = client.get_author_feed(actor, limit=50)
        for post_dict in posts_data:
            record = post_dict['record']
            # Handle different record structures if necessary, but usually 'text' and 'createdAt' are present
            text = record.get('text', '')
            created_at = record.get('created_at', '')
            
            # Check for reply
            reply_parent = None
            reply_root = None
            if 'reply' in record and record['reply']:
                 # This part depends on how the record is structured in the dict
                 # The 'record' field in the post view is the raw record.
                 # However, the 'reply' info is usually in the FeedViewPost wrapper, but here we are iterating post.dict() which is the ViewPost.
                 # ViewPost has 'record' which is the record data.
                 # Let's check if we can extract reply info safely.
                 pass

            post = BlueskyPost(
                uri=post_dict['uri'],
                cid=post_dict['cid'],
                author_handle=user.handle,
                text=text,
                created_at=created_at,
                is_seed=True
            )
            
            cursor.execute('''
                INSERT OR REPLACE INTO posts (uri, cid, author_handle, text, created_at, reply_parent, reply_root, is_seed, insert_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (post.uri, post.cid, post.author_handle, post.text, post.created_at, post.reply_parent, post.reply_root, post.is_seed, post.insert_timestamp))
            
        conn.commit()
        print(f"Finished processing {actor}")

    conn.close()
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest_data()
