import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_news_email(recipients, articles_by_keyword):
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD')

    if not gmail_user or not gmail_password:
        raise ValueError('GMAIL_USER と GMAIL_APP_PASSWORD を .env に設定してください')

    body = '本日のニュース配信をお届けします。\n\n'
    has_articles = False

    for keyword, articles in articles_by_keyword.items():
        body += f'━━━━━━━━━━━━━━━━━━━━\n'
        body += f'■ キーワード：{keyword}\n'
        body += f'━━━━━━━━━━━━━━━━━━━━\n'
        if articles:
            has_articles = True
            for article in articles:
                body += f'・{article["title"]}\n  {article["url"]}\n\n'
        else:
            body += '該当記事なし\n\n'

    if not has_articles:
        body = '本日は全てのキーワードで該当記事がありませんでした。\n'

    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = '【ニュース自動配信】本日のニュース'
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(gmail_user, gmail_password)
        smtp.sendmail(gmail_user, recipients, msg.as_string())

    print(f'[mailer] {len(recipients)}件のアドレスへ送信完了')
