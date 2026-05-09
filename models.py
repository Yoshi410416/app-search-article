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
            jnet21_last_article_id INTEGER NOT NULL DEFAULT 0
        )
    ''')
    c.execute('''
        INSERT INTO settings (id, jnet21_last_article_id)
        VALUES (1, 0)
        ON CONFLICT (id) DO NOTHING
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sent_articles (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def get_jnet21_last_id():
    conn = get_db()
    c = get_cursor(conn)
    c.execute('SELECT jnet21_last_article_id FROM settings WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row['jnet21_last_article_id'] if row else 0


def set_jnet21_last_id(article_id):
    conn = get_db()
    c = get_cursor(conn)
    c.execute(
        'UPDATE settings SET jnet21_last_article_id = %s WHERE id = 1',
        (article_id,)
    )
    conn.commit()
    conn.close()


def get_sent_urls():
    conn = get_db()
    c = get_cursor(conn)
    c.execute('SELECT url FROM sent_articles')
    urls = {row['url'] for row in c.fetchall()}
    conn.close()
    return urls


def record_sent_articles(articles_by_keyword):
    conn = get_db()
    c = get_cursor(conn)
    for articles in articles_by_keyword.values():
        for article in articles:
            c.execute(
                'INSERT INTO sent_articles (url) VALUES (%s) ON CONFLICT (url) DO NOTHING',
                (article['url'],)
            )
    conn.commit()
    conn.close()


def cleanup_old_sent_articles(days=30):
    conn = get_db()
    c = get_cursor(conn)
    c.execute(
        'DELETE FROM sent_articles WHERE sent_at < NOW() - INTERVAL \'%s days\'',
        (days,)
    )
    conn.commit()
    conn.close()
