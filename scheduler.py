from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

def run_daily_job():
    from models import get_db
    from scraper import collect_articles
    from mailer import send_news_email

    db = get_db()
    keywords = [row['keyword'] for row in db.execute('SELECT keyword FROM keywords').fetchall()]
    recipients = [row['email'] for row in db.execute('SELECT email FROM recipients').fetchall()]
    db.close()

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
