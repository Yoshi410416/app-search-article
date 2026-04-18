import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def scrape_yahoo_news(keyword):
    url = f'https://news.yahoo.co.jp/search?p={keyword}&ei=UTF-8'
    articles = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        seen = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/articles/' in href and href not in seen:
                title = link.get_text(strip=True)
                if len(title) > 10:
                    full_url = href if href.startswith('http') else f'https://news.yahoo.co.jp{href}'
                    articles.append({'title': title, 'url': full_url, 'source': 'Yahoo ニュース'})
                    seen.add(href)
    except Exception as e:
        print(f'[scraper] Yahoo: {keyword} の取得中にエラー: {e}')
    return articles

def scrape_mirasapo_plus(keyword):
    url = f'https://mirasapo-plus.go.jp/?s={quote(keyword)}'
    articles = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        seen = set()
        # 記事カード・検索結果の一般的なHTML構造に対応
        for article in soup.find_all(['article', 'li', 'div'], class_=lambda c: c and any(
            x in c for x in ['post', 'article', 'entry', 'result', 'item', 'card']
        )):
            link = article.find('a', href=True)
            if not link:
                continue
            href = link.get('href', '')
            title = link.get_text(strip=True)
            # タイトルが短すぎるもの・重複は除外
            if len(title) > 10 and href not in seen and 'mirasapo-plus.go.jp' in href:
                articles.append({'title': title, 'url': href, 'source': 'ミラサポplus'})
                seen.add(href)

        # 上記で取得できなかった場合、全リンクからフォールバック
        if not articles:
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                title = link.get_text(strip=True)
                if (
                    'mirasapo-plus.go.jp' in href
                    and href not in seen
                    and len(title) > 10
                    and href != url
                ):
                    articles.append({'title': title, 'url': href, 'source': 'ミラサポplus'})
                    seen.add(href)
    except Exception as e:
        print(f'[scraper] ミラサポplus: {keyword} の取得中にエラー: {e}')
    return articles

def collect_articles(keywords):
    all_articles = {}
    for keyword in keywords:
        yahoo = scrape_yahoo_news(keyword)
        time.sleep(1)
        mirasapo = scrape_mirasapo_plus(keyword)
        time.sleep(1)
        all_articles[keyword] = yahoo + mirasapo
    return all_articles
