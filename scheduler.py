from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

def run_daily_job():
    from models import get_db, get_cursor
    from scraper import collect_articles
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
    send_news_email(recipients, articles)
    print('[scheduler] 配信完了')

def start_scheduler():
    tz = pytz.timezone('Asia/Tokyo')
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(run_daily_job, CronTrigger(hour=8, minute=0, timezone=tz))
    scheduler.start()
    print('[scheduler] スケジューラ起動（毎朝8時に配信）')
    return scheduler
