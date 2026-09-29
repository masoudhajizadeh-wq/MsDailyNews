import os
import time
import hashlib
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

API = f"https://api.telegram.org/bot{TOKEN}"

FEEDS = {
    "🇮🇷 ایران": [
        ("YJC", "https://www.yjc.ir/fa/rss/allnews"),
        ("ISNA", "https://www.isna.ir/rss"),
        ("Mehr", "https://www.mehrnews.com/rss"),
        ("Khabaronline", "https://www.khabaronline.ir/rss"),
        ("Tabnak", "https://www.tabnak.ir/fa/rss/allnews"),
        ("Tasnim", "https://www.tasnimnews.com/fa/rss/feed/0/8/0/%D9%85%D9%87%D9%85%D8%AA%D8%B1%DB%8C%D9%86-%D8%A7%D8%AE%D8%A8%D8%A7%D8%B1-%D8%AA%D8%B3%D9%86%DB%8C%D9%85"),
    ],
}

CHECK_EVERY_SECONDS = 600
NEWS_AGE_MINUTES = 60

sent_news = set()


def send_message(text):
    response = requests.post(
        f"{API}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=20,
    )

    print("Telegram:", response.status_code, response.text)


def get_news_time(entry):
    value = entry.get("published") or entry.get("updated")

    if not value:
        return None

    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        pass

    try:
        value2 = entry.get("published_parsed") or entry.get("updated_parsed")

        if value2:
            return datetime(
                value2.tm_year,
                value2.tm_mon,
                value2.tm_mday,
                value2.tm_hour,
                value2.tm_min,
                value2.tm_sec,
                tzinfo=timezone.utc,
            )
    except Exception:
        pass

    return None


def make_id(title, link):
    return hashlib.sha256(
        f"{title}|{link}".encode("utf-8")
    ).hexdigest()


def detect_category(title):
    text = title.lower()

    if any(x in text for x in [
        "فوتبال", "ورزش", "تیم ملی", "لیگ", "جام جهانی",
        "بازیکن", "مربی", "استقلال", "پرسپولیس"
    ]):
        return "⚽ ورزشی"

    if any(x in text for x in [
        "دلار", "بورس", "اقتصاد", "بانک", "ارز",
        "طلا", "سکه", "بازار", "قیمت"
    ]):
        return "💰 اقتصادی"

    if any(x in text for x in [
        "فناوری", "هوش مصنوعی", "اینترنت", "تکنولوژی",
        "مایکروسافت", "گوگل", "اپل"
    ]):
        return "💻 فناوری"

    if any(x in text for x in [
        "جهان", "آمریکا", "روسیه", "چین", "اسرائیل",
        "اوکراین", "اروپا", "غزه"
    ]):
        return "🌍 جهان"

    if any(x in text for x in [
        "دولت", "مجلس", "وزیر", "رئیس جمهور",
        "انتخابات", "سیاست", "نماینده"
    ]):
        return "🏛 سیاسی"

    return "🇮🇷 ایران"


def collect_news():
    now = datetime.now(timezone.utc)
    minimum_time = now - timedelta(minutes=NEWS_AGE_MINUTES)

    news = []

    for category, sources in FEEDS.items():
        for source_name, feed_url in sources:

            try:
                print("Reading:", source_name)

                feed = feedparser.parse(feed_url)

                for entry in feed.entries:

                    title = entry.get("title", "").strip()
                    link = entry.get("link", "").strip()

                    if not title or not link:
                        continue

                    published = get_news_time(entry)

                    if not published:
                        continue

                    if published < minimum_time or published > now:
                        continue

                    news_id = make_id(title, link)

                    if news_id in sent_news:
                        continue

                    news.append({
                        "id": news_id,
                        "title": title,
                        "link": link,
                        "source": source_name,
                        "published": published,
                        "category": detect_category(title),
                    })

            except Exception as e:
                print(f"RSS error {source_name}: {e}")

    news.sort(
        key=lambda x: x["published"],
        reverse=True
    )

    return news


def publish_news():
    news = collect_news()

    print(f"New news found: {len(news)}")

    # فعلاً حداکثر 10 خبر در هر نوبت
    news = news[:10]

    for item in news:

        text = (
            f"{item['category']}\n\n"
            f"📰 {item['title']}\n\n"
            f"🔗 منبع: {item['source']}\n"
            f"{item['link']}"
        )

        send_message(text)

        sent_news.add(item["id"])

        time.sleep(2)


print("MsDailyNews Bot started.")

send_message(
    "✅ MsDailyNews فعال شد.\n\n"
    "بررسی اخبار یک ساعت اخیر آغاز شد."
)

while True:

    try:
        publish_news()

    except Exception as e:
        print("Main error:", e)

    print(
        f"Waiting {CHECK_EVERY_SECONDS} seconds..."
    )

    time.sleep(CHECK_EVERY_SECONDS)
