def run_daily_job():
    from models import get_db, get_cursor
    from scraper import collect_articles, collect_jnet21_articles
    from mailer import send_news_email
    conn = get_db()
    c = get_cursor(conn)
    c.execute('SELECT keyword FROM keywords')
    keywords = [row['keyword'] for row in c.fetchall()]
    c.execute('SELECT email FROM recipients')
    recipients = [row['email'] for row in c.fetchall()]
    conn.close()

    if not recipients:
        print('[scheduler] 配信先メールアドレスが未登録のためスキップ')
        return

    articles = collect_articles(keywords)

    from models import get_jnet21_last_id, set_jnet21_last_id
    from scraper import _extract_jnet21_article_id
    last_id = get_jnet21_last_id()
    jnet21_articles = collect_jnet21_articles(last_id=last_id)
    if jnet21_articles:
        new_max_id = max(_extract_jnet21_article_id(a['url']) for a in jnet21_articles)
        set_jnet21_last_id(new_max_id)

    send_news_email(recipients, articles, jnet21_articles)
    print('[scheduler] 配信完了')
