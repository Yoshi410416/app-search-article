def run_daily_job():
    from models import get_db, get_cursor, get_sent_urls, record_sent_articles, cleanup_old_sent_articles
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

    sent_urls = get_sent_urls()
    filtered_articles = {}
    for keyword, arts in articles.items():
        new_arts = [a for a in arts if a['url'] not in sent_urls]
        skipped = len(arts) - len(new_arts)
        if skipped > 0:
            print(f'[scheduler] 「{keyword}」: {skipped}件を送信済みとして除外')
        filtered_articles[keyword] = new_arts

    from models import get_jnet21_last_id, set_jnet21_last_id
    from scraper import _extract_jnet21_article_id
    last_id = get_jnet21_last_id()
    jnet21_articles = collect_jnet21_articles(last_id=last_id)
    if jnet21_articles:
        new_max_id = max(_extract_jnet21_article_id(a['url']) for a in jnet21_articles)
        set_jnet21_last_id(new_max_id)

    send_news_email(recipients, filtered_articles, jnet21_articles)
    record_sent_articles(filtered_articles)
    cleanup_old_sent_articles(days=30)
    print('[scheduler] 配信完了')
