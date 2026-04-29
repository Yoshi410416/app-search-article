import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_news_email(recipients, articles_by_keyword, jnet21_articles=None):
    api_key = os.environ.get('SENDGRID_API_KEY')
    mail_from = os.environ.get('MAIL_FROM')

    if not api_key or not mail_from:
        raise ValueError('SENDGRID_API_KEY と MAIL_FROM を環境変数に設定してください')

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
                body += f'・{article["title"]}{vc_str}\n{article["url"]}\n\n'
        else:
            body += '該当記事なし\n\n'

    if not has_articles:
        body = '本日は全てのキーワードで該当記事がありませんでした。\n\n'

    body += f'━━━━━━━━━━━━━━━━━━━━\n'
    body += f'■ J-Net21（大阪府）の補助金　新着情報（{yesterday}分）\n'
    body += f'━━━━━━━━━━━━━━━━━━━━\n'
    if jnet21_articles:
        for article in jnet21_articles:
            body += f'・{article["title"]}\n{article["url"]}\n\n'
    else:
        body += '前日の新着情報はありませんでした。\n\n'

    sg = SendGridAPIClient(api_key)
    for recipient in recipients:
        message = Mail(
            from_email=mail_from,
            to_emails=recipient,
            subject='【ニュース自動配信】本日のニュース',
            plain_text_content=body,
        )
        sg.send(message)

    print(f'[mailer] {len(recipients)}件のアドレスへ送信完了')
