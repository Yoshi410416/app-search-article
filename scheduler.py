from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

_scheduler = None

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
    global _scheduler
    from models import get_delivery_time
    hour, minute = get_delivery_time()
    tz = pytz.timezone('Asia/Tokyo')
    _scheduler = BackgroundScheduler(timezone=tz)
    _scheduler.add_job(run_daily_job, CronTrigger(hour=hour, minute=minute, timezone=tz), id='daily_job')
    _scheduler.start()
    print(f'[scheduler] スケジューラ起動（毎日 {hour:02d}:{minute:02d} に配信）')
    return _scheduler

def reschedule(hour, minute):
    global _scheduler
    if _scheduler:
        tz = pytz.timezone('Asia/Tokyo')
        _scheduler.reschedule_job('daily_job', trigger=CronTrigger(hour=hour, minute=minute, timezone=tz))
        print(f'[scheduler] 配信時間を {hour:02d}:{minute:02d} に変更')
