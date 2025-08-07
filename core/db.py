import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor

load_dotenv()  # Load from .env file

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

async def register_user(telegram_id, referrer_id=None, bot_instance=None):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    if cur.fetchone() is None:
        if referrer_id:
            # Check if referrer exists
            cur.execute("SELECT * FROM users WHERE telegram_id = %s", (referrer_id,))
            if cur.fetchone():
                # Insert new user with 2 free gens
                cur.execute("""
                    INSERT INTO users (telegram_id, referrer_id, free_tokens)
                    VALUES (%s, %s, 2)
                """, (telegram_id, referrer_id))

                # Reward the referrer
                cur.execute("""
                    UPDATE users SET free_tokens = free_tokens + 1
                    WHERE telegram_id = %s
                """, (referrer_id,))
                
                if bot_instance:
                    try:
                        await bot_instance.send_message(
                            chat_id=referrer_id,
                            text="🎉 Someone used your referral link! You've earned 1 free token."
                        )
                    except Exception as e:
                        print(f"[WARN] Couldn't notify referrer {referrer_id}: {e}")
            else:
                # Referrer not found, just insert normal user
                cur.execute("INSERT INTO users (telegram_id, free_tokens) VALUES (%s, 2)", (telegram_id,))
        else:
            # No referrer, insert new user with 2 free gens
            cur.execute("INSERT INTO users (telegram_id, free_tokens) VALUES (%s, 2)", (telegram_id,))
        conn.commit()

    cur.close()
    conn.close()

def get_user_generations(telegram_id):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT free_tokens, vip_tokens FROM users WHERE telegram_id = %s", (telegram_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

def decrement_generation(telegram_id):
    conn = get_conn()
    cur = conn.cursor()

    # Fetch current balances first
    cur.execute("SELECT vip_tokens, free_tokens FROM users WHERE telegram_id = %s", (telegram_id,))
    result = cur.fetchone()
    if not result:
        conn.close()
        return None  # or raise error

    vip, free = result

    if vip > 0:
        cur.execute("""
            UPDATE users
            SET vip_tokens = vip_tokens - 1
            WHERE telegram_id = %s
        """, (telegram_id,))
        usage = "vip"
    elif free > 0:
        cur.execute("""
            UPDATE users
            SET free_tokens = free_tokens - 1
            WHERE telegram_id = %s
        """, (telegram_id,))
        usage = "free"
    else:
        usage = None  # Should never happen, because checked earlier

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Decremented {usage} generation for telegram_id={telegram_id}")
    return usage

def increment_vip_tokens(telegram_id: int, amount: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users SET vip_tokens = vip_tokens + %s
        WHERE telegram_id = %s
    """, (amount, telegram_id))
    conn.commit()
    cur.close()
    conn.close()

def get_referral_count(telegram_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE referrer_id = %s", (telegram_id,))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count