import requests
from bs4 import BeautifulSoup
import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'Referer': 'https://www.google.com/',
}

def get_time_range():
    now = datetime.now()
    end_dt = now.replace(hour=7, minute=0, second=0, microsecond=0)
    start_dt = (now - timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    return start_dt, end_dt

def parse_article_time(time_tag):
    datetime_attr = time_tag.get('datetime', '')
    if datetime_attr:
        try:
            dt_str = datetime_attr[:19]
            return datetime.fromisoformat(dt_str)
        except:
            pass

    text = time_tag.get_text(strip=True)
    now = datetime.now()

    # 例：4/18(土) 14:10
    m = re.match(r'(\d+)/(\d+)[^\ ]* (\d+):(\d+)', text)
    if m:
        try:
            month, day, hour, minute = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            return datetime(now.year, month, day, hour, minute)
        except:
            pass

    if '分前' in text:
        try:
            minutes = int(''.join(filter(str.isdigit, text)))
            return now - timedelta(minutes=minutes)
        except:
            pass
    elif '時間前' in text:
        try:
            hours = int(''.join(filter(str.isdigit, text)))
            return now - timedelta(hours=hours)
        except:
            pass
    elif '昨日' in text:
        return (now - timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    return None

def _find_time_from_link(link):
    for ancestor in link.parents:
        if ancestor.name in ['body', 'html']:
            break
        time_tag = ancestor.find('time')
        if time_tag:
            return parse_article_time(time_tag)
    return None

_VIEW_COUNT_RE = re.compile(r'([\d,]+(?:\.\d+)?万?)\s*件')

def _parse_view_count(raw):
    raw = raw.replace(',', '')
    if '万' in raw:
        try:
            return int(float(raw.replace('万', '')) * 10000)
        except:
            return 0
    try:
        return int(raw)
    except:
        return 0

def _find_view_count_from_link(link):
    for ancestor in link.parents:
        if ancestor.name in ['body', 'html']:
            break
        for text_node in ancestor.find_all(string=_VIEW_COUNT_RE):
            m = _VIEW_COUNT_RE.search(text_node)
            if m:
                return _parse_view_count(m.group(1))
    return 0

def scrape_yahoo_news(keyword):
    url = f'https://news.yahoo.co.jp/search?p={keyword}&ei=UTF-8'
    articles = []
    start_dt, end_dt = get_time_range()

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
                    article_time = _find_time_from_link(link)
                    if article_time and not (start_dt <= article_time <= end_dt):
                        continue
                    full_url = href if href.startswith('http') else f'https://news.yahoo.co.jp{href}'
                    view_count = _find_view_count_from_link(link)
                    articles.append({'title': title, 'url': full_url, 'source': 'Yahoo ニュース', 'view_count': view_count})
                    seen.add(href)
    except Exception as e:
        print(f'[scraper] Yahoo: {keyword} の取得中にエラー: {e}')
    return articles

def scrape_google_news(keyword):
    url = f'https://news.google.com/rss/search?q={keyword}&hl=ja&gl=JP&ceid=JP:ja'
    articles = []
    start_dt, end_dt = get_time_range()

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        for item in root.findall('.//item'):
            title_el = item.find('title')
            link_el = item.find('link')
            pub_date_el = item.find('pubDate')

            title = title_el.text if title_el is not None else ''
            link = link_el.text if link_el is not None else ''
            if not title or not link:
                continue

            article_time = None
            if pub_date_el is not None and pub_date_el.text:
                try:
                    dt = parsedate_to_datetime(pub_date_el.text)
                    # GMTからJSTに変換（+9時間）
                    article_time = datetime.utcfromtimestamp(dt.timestamp()) + timedelta(hours=9)
                except:
                    pass

            if article_time and not (start_dt <= article_time <= end_dt):
                continue

            articles.append({'title': title, 'url': link, 'source': 'Google ニュース'})
    except Exception as e:
        print(f'[scraper] Google: {keyword} の取得中にエラー: {e}')
    return articles

def parse_nhk_title_time(title):
    # 例：「記事タイトル4月18日午後2時09分」→ datetime と 本文タイトル を返す
    m = re.search(r'(\d+)月(\d+)日(午前|午後)(\d+)時(\d+)?分?$', title)
    if m:
        now = datetime.now()
        month, day = int(m.group(1)), int(m.group(2))
        hour = int(m.group(4))
        minute = int(m.group(5)) if m.group(5) else 0
        if m.group(3) == '午後' and hour != 12:
            hour += 12
        elif m.group(3) == '午前' and hour == 12:
            hour = 0
        try:
            article_time = datetime(now.year, month, day, hour, minute)
            clean_title = title[:m.start()].strip()
            return article_time, clean_title
        except:
            pass
    return None, title

def scrape_nhk_news(keyword):
    url = f'https://www3.nhk.or.jp/news/search/?word={keyword}'
    articles = []
    start_dt, end_dt = get_time_range()

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        seen = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/newsweb/na/' in href:
                raw_title = link.get_text(strip=True)
                if len(raw_title) > 10 and href not in seen:
                    article_time, title = parse_nhk_title_time(raw_title)
                    if article_time and not (start_dt <= article_time <= end_dt):
                        continue
                    full_url = href if href.startswith('http') else f'https://news.web.nhk{href}'
                    articles.append({'title': title, 'url': full_url, 'source': 'NHK ニュース'})
                    seen.add(href)
    except Exception as e:
        print(f'[scraper] NHK: {keyword} の取得中にエラー: {e}')
    return articles

def scrape_nikkei_news(keyword):
    url = f'https://www.nikkei.com/search?keyword={keyword}'
    articles = []
    start_dt, end_dt = get_time_range()

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        seen = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/article/' in href or '/news/' in href:
                title = link.get_text(strip=True)
                if len(title) > 10 and href not in seen:
                    article_time = _find_time_from_link(link)
                    if article_time and not (start_dt <= article_time <= end_dt):
                        continue
                    full_url = href if href.startswith('http') else f'https://www.nikkei.com{href}'
                    articles.append({'title': title, 'url': full_url, 'source': '日経電子版'})
                    seen.add(href)
    except Exception as e:
        print(f'[scraper] 日経: {keyword} の取得中にエラー: {e}')
    return articles

def get_jnet21_time_range():
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    start_dt = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return start_dt, end_dt

JNET21_ALLOWED_REGIONS = {'全国', '大阪府'}

DC_COVERAGE = '{http://purl.org/dc/elements/1.1/}coverage'
RDF_LABEL   = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}label'

def _get_jnet21_regions(item):
    regions = set()
    for cov in item.findall(DC_COVERAGE):
        label_el = cov.find(RDF_LABEL)
        if label_el is not None and label_el.text:
            regions.add(label_el.text.strip())
    return regions

def _extract_jnet21_article_id(url):
    m = re.search(r'/articles/(\d+)', url)
    return int(m.group(1)) if m else 0

def collect_jnet21_articles(last_id=0):
    feeds = [
        'https://j-net21.smrj.go.jp/snavi/support/support.xml',
        'https://j-net21.smrj.go.jp/snavi/public/public.xml',
        'https://j-net21.smrj.go.jp/snavi/event/event.xml',
    ]
    DC_DATE = '{http://purl.org/dc/elements/1.1/}date'
    articles = []
    start_dt, end_dt = get_jnet21_time_range()
    seen = set()

    for feed_url in feeds:
        try:
            response = requests.get(feed_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)

            for item in root.findall('.//item'):
                title_el = item.find('title')
                link_el = item.find('link')
                date_el = item.find(DC_DATE)

                title = title_el.text if title_el is not None else ''
                link = link_el.text if link_el is not None else ''
                if not title or not link or link in seen:
                    continue

                regions = _get_jnet21_regions(item)
                if not regions & JNET21_ALLOWED_REGIONS:
                    continue

                full_url = link if link.startswith('http') else f'https://j-net21.smrj.go.jp/{link}'

                if _extract_jnet21_article_id(full_url) <= last_id:
                    continue

                article_time = None
                if date_el is not None and date_el.text:
                    try:
                        dt = datetime.fromisoformat(date_el.text)
                        article_time = datetime.utcfromtimestamp(dt.timestamp()) + timedelta(hours=9)
                    except Exception:
                        pass

                if article_time and not (start_dt <= article_time <= end_dt):
                    continue

                articles.append({'title': title, 'url': full_url, 'source': 'J-Net21'})
                seen.add(link)
        except Exception as e:
            print(f'[scraper] J-Net21: 取得中にエラー ({feed_url}): {e}')

    return articles


def _title_matches_keyword(title, keyword):
    # キーワードをスペースで分割し、いずれかの単語がタイトルに含まれれば一致とみなす
    words = keyword.split()
    title_lower = title.lower()
    return any(word.lower() in title_lower for word in words)

def collect_articles(keywords):
    all_articles = {}
    for keyword in keywords:
        articles = []
        articles += scrape_yahoo_news(keyword)
        time.sleep(1)
        articles += scrape_google_news(keyword)
        time.sleep(1)
        articles += scrape_nhk_news(keyword)
        time.sleep(1)
        articles += scrape_nikkei_news(keyword)
        time.sleep(1)

        # タイトルにキーワードが含まれない記事を除外
        filtered = [a for a in articles if _title_matches_keyword(a['title'], keyword)]
        all_articles[keyword] = filtered
    return all_articles
