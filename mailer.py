import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_news_email(recipients, articles_by_keyword, jnet21_articles=None):
    gmail_user = os.environ.get('MAIL_USER')
    gmail_password = os.environ.get('MAIL_PASSWORD')

    if not gmail_user or not gmail_password:
        raise ValueError('MAIL_USER と MAIL_PASSWORD を .env に設定してください')

    from datetime import datetime, timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y年%m月%d日')

    body = '本日のニュース配信をお届けします。\n\n'
    has_articles = False

    for keyword, articles in articles_by_keyword.items():
        body += f'━━━━━━━━━━━━━━━━━━━━\n'
        body += f'■ キーワード：{keyword}\n'
        body += f'━━━━━━━━━━━━━━━━━━━━\n'
        if articles:
            has_articles = True
            sorted_articles = sorted(articles, key=lambda x: x.get('view_count', 0), reverse=True)
            for article in sorted_articles:
                vc = article.get('view_count', 0)
                if vc >= 10000:
                    vc_str = f' [{vc / 10000:.1f}万件]'
                elif vc > 0:
                    vc_str = f' [{vc}件]'
                else:
                    vc_str = ''
                body += f'・{article["title"]}{vc_str}\n  {article["url"]}\n\n'
        else:
            body += '該当記事なし\n\n'

    if not has_articles:
        body = '本日は全てのキーワードで該当記事がありませんでした。\n\n'

    body += f'━━━━━━━━━━━━━━━━━━━━\n'
    body += f'■ J-Net21 新着情報（{yesterday}分）\n'
    body += f'━━━━━━━━━━━━━━━━━━━━\n'
    if jnet21_articles:
        for article in jnet21_articles:
            body += f'・{article["title"]}\n  {article["url"]}\n\n'
    else:
        body += '前日の新着情報はありませんでした。\n\n'

    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = '【ニュース自動配信】本日のニュース'
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.starttls()
        smtp.login(gmail_user, gmail_password)
        smtp.sendmail(gmail_user, recipients, msg.as_string())

    print(f'[mailer] {len(recipients)}件のアドレスへ送信完了')
