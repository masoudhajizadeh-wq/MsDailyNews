import os
import time
import hashlib
import threading
import requests
import feedparser

from flask import Flask
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

API = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

sent_news = set()

CHECK_EVERY_SECONDS = 600
NEWS_AGE_MINUTES = 60


FEEDS = {
    "🇮🇷 ایران": [
        ("YJC", "https://www.yjc.ir/fa/rss/allnews"),
        ("ISNA", "https://www.isna.ir/rss"),
        ("Mehr", "https://www.mehrnews.com/rss"),
        ("Khabaronline", "https://www.khabaronline.ir/rss"),
        ("Tabnak", "https://www.tabnak.ir/fa/rss/allnews"),
    ]
}


@app.route("/")
def home():
    return "MsDailyNews Bot is running!"


def send_message(text):
    try:
        r = requests.post(
            f"{API}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "disable_web_page_preview": False
            },
            timeout=20
        )

        print("Telegram:", r.status_code, r.text)

    except Exception as e:
        print("Telegram error:", e)


def get_news_time(entry):

    value = entry.get("published") or entry.get("updated")

    if not value:
        return None

    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except:
        pass

    return None


def make_id(title, link):

    return hashlib.sha256(
        f"{title}|{link}".encode()
    ).hexdigest()


def detect_category(title):

    text = title.lower()

    if any(x in text for x in [
        "فوتبال", "ورزش", "تیم ملی",
        "لیگ", "جام جهانی", "بازیکن",
        "مربی", "استقلال", "پرسپولیس"
    ]):
        return "⚽ ورزشی"

    if any(x in text for x in [
        "دلار", "بورس", "اقتصاد",
        "بانک", "ارز", "طلا",
        "سکه", "بازار", "قیمت"
    ]):
        return "💰 اقتصادی"

    if any(x in text for x in [
        "فناوری", "هوش مصنوعی",
        "اینترنت", "تکنولوژی",
        "گوگل", "اپل"
    ]):
        return "💻 فناوری"

    if any(x in text for x in [
        "آمریکا", "روسیه", "چین",
        "اسرائیل", "اوکراین",
        "اروپا", "غزه"
    ]):
        return "🌍 جهان"

    if any(x in text for x in [
        "دولت", "مجلس", "وزیر",
        "رئیس جمهور", "انتخابات",
        "سیاست", "نماینده"
    ]):
        return "🏛 سیاسی"

    return "🇮🇷 ایران"


def collect_news():

    now = datetime.now(timezone.utc)

    minimum_time = now - timedelta(
        minutes=NEWS_AGE_MINUTES
    )

    news = []

    for category, sources in FEEDS.items():

        for source_name, feed_url in sources:

            try:

                print("Reading:", source_name)

                feed = feedparser.parse(feed_url)

                for entry in feed.entries:

                    title = entry.get(
                        "title", ""
                    ).strip()

                    link = entry.get(
                        "link", ""
                    ).strip()

                    if not title or not link:
                        continue

                    published = get_news_time(entry)

                    if not published:
                        continue

                    if published < minimum_time:
                        continue

                    if published > now:
                        continue

                    news_id = make_id(
                        title,
                        link
                    )

                    if news_id in sent_news:
                        continue

                    news.append({
                        "id": news_id,
                        "title": title,
                        "link": link,
                        "source": source_name,
                        "published": published
                    })

            except Exception as e:

                print(
                    f"RSS error {source_name}: {e}"
                )

    news.sort(
        key=lambda x: x["published"],
        reverse=True
    )

    return news


def publish_news():

    news = collect_news()

    print(
        f"New news found: {len(news)}"
    )

    news = news[:10]

    for item in news:

        category = detect_category(
            item["title"]
        )

        message = (
            f"{category}\n\n"
            f"📰 {item['title']}\n\n"
            f"🔗 منبع: {item['source']}\n"
            f"{item['link']}"
        )

        send_message(message)

        sent_news.add(
            item["id"]
        )

        time.sleep(2)


def news_worker():

    print("News worker started.")

    send_message(
        "✅ MsDailyNews فعال شد.\n\n"
        "اخبار یک ساعت اخیر در حال بررسی است."
    )

    while True:

        try:

            publish_news()

        except Exception as e:

            print(
                "Worker error:",
                e
            )

        print(
            f"Waiting {CHECK_EVERY_SECONDS} seconds..."
        )

        time.sleep(
            CHECK_EVERY_SECONDS
        )


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    worker = threading.Thread(
        target=news_worker,
        daemon=True
    )

    worker.start()

    app.run(
        host="0.0.0.0",
        port=port
    )
