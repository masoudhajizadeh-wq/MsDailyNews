import os
import time
import hashlib
import threading
import requests
import feedparser

from flask import Flask
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime


# =========================================================
# Telegram
# =========================================================

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

API = f"https://api.telegram.org/bot{TOKEN}"


# =========================================================
# Flask
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "MsDailyNews Bot is running!"


# =========================================================
# Settings
# =========================================================

sent_news = set()

CHECK_EVERY_SECONDS = 600
NEWS_AGE_MINUTES = 60


# =========================================================
# RSS SOURCES
# =========================================================

FEEDS = {

    # -----------------------------------------------------
    # 🇮🇷 منابع ایران
    # -----------------------------------------------------

    "🇮🇷 ایران": [

        ("YJC",
         "https://www.yjc.ir/fa/rss/allnews"),

        ("ISNA",
         "https://www.isna.ir/rss"),

        ("Mehr",
         "https://www.mehrnews.com/rss"),

        ("Khabaronline",
         "https://www.khabaronline.ir/rss"),

        ("Tabnak",
         "https://www.tabnak.ir/fa/rss/allnews"),
    ],


    # -----------------------------------------------------
    # 🌍 منابع خارجی
    # -----------------------------------------------------

    "🌍 جهان": [

        ("Al Jazeera",
         "https://www.aljazeera.com/xml/rss/all.xml"),

        ("Fox News",
         "https://moxie.foxnews.com/google-publisher/latest.xml"),

        ("Fox World",
         "https://moxie.foxnews.com/google-publisher/world.xml"),

        ("Fox Politics",
         "https://moxie.foxnews.com/google-publisher/politics.xml"),

        ("DW",
         "https://rss.dw.com/xml/rss-en-all"),

        ("CNN",
         "http://rss.cnn.com/rss/edition.rss"),

        ("Sky News",
         "https://feeds.skynews.com/feeds/rss/world.xml"),
    ],


    # -----------------------------------------------------
    # ⚽ ورزش
    # -----------------------------------------------------

    "⚽ ورزش": [

        ("Fox Sports",
         "https://moxie.foxnews.com/google-publisher/sports.xml"),
    ],


    # -----------------------------------------------------
    # 💻 فناوری
    # -----------------------------------------------------

    "💻 فناوری": [

        ("Fox Tech",
         "https://moxie.foxnews.com/google-publisher/tech.xml"),
    ]
}


# =========================================================
# SEND TELEGRAM MESSAGE
# =========================================================

def send_message(text):

    try:

        response = requests.post(

            f"{API}/sendMessage",

            data={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },

            timeout=20
        )

        print(
            "Telegram:",
            response.status_code,
            response.text
        )

    except Exception as e:

        print(
            "Telegram error:",
            e
        )


# =========================================================
# GET NEWS TIME
# =========================================================

def get_news_time(entry):

    value = (
        entry.get("published")
        or entry.get("updated")
    )

    if value:

        try:

            return parsedate_to_datetime(
                value
            ).astimezone(timezone.utc)

        except Exception:
            pass


    for key in [
        "published_parsed",
        "updated_parsed"
    ]:

        parsed = entry.get(key)

        if parsed:

            try:

                from calendar import timegm

                return datetime.fromtimestamp(
                    timegm(parsed),
                    timezone.utc
                )

            except Exception:
                pass


    return None


# =========================================================
# CREATE NEWS ID
# =========================================================

def make_id(title, link):

    return hashlib.sha256(
        f"{title}|{link}".encode()
    ).hexdigest()


# =========================================================
# DETECT CATEGORY
# =========================================================

def detect_category(title):

    text = title.lower()


    # ورزش
    if any(x in text for x in [

        "فوتبال",
        "ورزش",
        "تیم ملی",
        "لیگ",
        "جام جهانی",
        "بازیکن",
        "مربی",
        "استقلال",
        "پرسپولیس",

        "football",
        "sport",
        "soccer",
        "nba",
        "nfl"

    ]):

        return "⚽ ورزشی"


    # اقتصاد
    if any(x in text for x in [

        "دلار",
        "بورس",
        "اقتصاد",
        "بانک",
        "ارز",
        "طلا",
        "سکه",
        "بازار",
        "قیمت",

        "economy",
        "economic",
        "market",
        "stock",
        "stocks",
        "dollar"

    ]):

        return "💰 اقتصادی"


    # فناوری
    if any(x in text for x in [

        "فناوری",
        "هوش مصنوعی",
        "اینترنت",
        "تکنولوژی",
        "گوگل",
        "اپل",

        "technology",
        "tech",
        "artificial intelligence",
        "ai",
        "google",
        "apple"

    ]):

        return "💻 فناوری"


    # جهان
    if any(x in text for x in [

        "آمریکا",
        "روسیه",
        "چین",
        "اسرائیل",
        "اوکراین",
        "اروپا",
        "غزه",
        "امریکا",

        "usa",
        "america",
        "russia",
        "china",
        "israel",
        "ukraine",
        "europe",
        "gaza",
        "iran"

    ]):

        return "🌍 جهان"


    # سیاست
    if any(x in text for x in [

        "دولت",
        "مجلس",
        "وزیر",
        "رئیس جمهور",
        "انتخابات",
        "سیاست",
        "نماینده",

        "government",
        "president",
        "election",
        "politics",
        "political",
        "minister"

    ]):

        return "🏛 سیاسی"


    return "🇮🇷 ایران"


# =========================================================
# COLLECT NEWS
# =========================================================

def collect_news():

    now = datetime.now(
        timezone.utc
    )

    minimum_time = (
        now -
        timedelta(
            minutes=NEWS_AGE_MINUTES
        )
    )

    news = []


    for category, sources in FEEDS.items():

        for source_name, feed_url in sources:

            try:

                print(
                    "Reading:",
                    source_name
                )

                feed = feedparser.parse(
                    feed_url
                )


                if getattr(
                    feed,
                    "bozo",
                    False
                ):

                    print(
                        "RSS warning:",
                        source_name,
                        getattr(
                            feed,
                            "bozo_exception",
                            ""
                        )
                    )


                for entry in feed.entries:

                    title = entry.get(
                        "title",
                        ""
                    ).strip()

                    link = entry.get(
                        "link",
                        ""
                    ).strip()


                    if not title or not link:
                        continue


                    published = get_news_time(
                        entry
                    )


                    if not published:
                        continue


                    # فقط یک ساعت اخیر
                    if published < minimum_time:
                        continue


                    # حذف تاریخ آینده
                    if published > now:
                        continue


                    news_id = make_id(
                        title,
                        link
                    )


                    # خبر قبلاً ارسال شده
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
                    f"RSS error "
                    f"{source_name}: {e}"
                )


    # جدیدترین خبرها اول
    news.sort(
        key=lambda x: x["published"],
        reverse=True
    )


    # حذف خبرهای تکراری بر اساس عنوان
    unique_news = []

    seen_titles = set()


    for item in news:

        normalized_title = (
            item["title"]
            .strip()
            .lower()
        )


        if normalized_title in seen_titles:
            continue


        seen_titles.add(
            normalized_title
        )

        unique_news.append(
            item
        )


    return unique_news


# =========================================================
# PUBLISH NEWS
# =========================================================

def publish_news():

    news = collect_news()


    print(
        f"New news found: {len(news)}"
    )


    # حداکثر 10 خبر در هر نوبت
    news = news[:10]


    for item in news:

        category = detect_category(
            item["title"]
        )


        # نام منبع خودش لینک خبر است
        message = (

            f"{category}\n\n"

            f"📰 {item['title']}\n\n"

            f'🔗 منبع: '
            f'<a href="{item["link"]}">'
            f'{item["source"]}'
            f'</a>'

        )


        send_message(
            message
        )


        sent_news.add(
            item["id"]
        )


        time.sleep(2)


# =========================================================
# NEWS WORKER
# =========================================================

def news_worker():

    print(
        "News worker started."
    )


    send_message(

        "✅ MsDailyNews فعال شد.\n\n"
        "بررسی اخبار یک ساعت اخیر آغاز شد."

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
            f"Waiting "
            f"{CHECK_EVERY_SECONDS} "
            f"seconds..."
        )


        time.sleep(
            CHECK_EVERY_SECONDS
        )


# =========================================================
# START
# =========================================================

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
