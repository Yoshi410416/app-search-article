import psycopg2
import psycopg2.extras
import os

def get_db():
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'), sslmode='require')
    return conn

def get_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def init_db():
    conn = get_db()
    c = get_cursor(conn)
    c.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id SERIAL PRIMARY KEY,
            keyword TEXT NOT NULL UNIQUE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS recipients (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL UNIQUE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            delivery_hour INTEGER NOT NULL DEFAULT 8,
            delivery_minute INTEGER NOT NULL DEFAULT 0
        )
    ''')
    c.execute('''
        INSERT INTO settings (id, delivery_hour, delivery_minute)
        VALUES (1, 8, 0)
        ON CONFLICT (id) DO NOTHING
    ''')
    conn.commit()
    conn.close()


def get_delivery_time():
    conn = get_db()
    c = get_cursor(conn)
    c.execute('SELECT delivery_hour, delivery_minute FROM settings WHERE id = 1')
    row = c.fetchone()
    conn.close()
    if row:
        return row['delivery_hour'], row['delivery_minute']
    return 8, 0


def set_delivery_time(hour, minute):
    conn = get_db()
    c = get_cursor(conn)
    c.execute(
        'UPDATE settings SET delivery_hour = %s, delivery_minute = %s WHERE id = 1',
        (hour, minute)
    )
    conn.commit()
    conn.close()
