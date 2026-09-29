import os
import time
import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

API = f"https://api.telegram.org/bot{TOKEN}"


def send_message(chat_id, text):
    requests.post(
        f"{API}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text
        },
        timeout=20
    )


def get_updates(offset=None):
    params = {
        "timeout": 30
    }

    if offset is not None:
        params["offset"] = offset

    response = requests.get(
        f"{API}/getUpdates",
        params=params,
        timeout=40
    )

    return response.json()


print("MsDailyNews Bot started...")

offset = None

while True:
    try:
        data = get_updates(offset)

        if not data.get("ok"):
            print("Telegram error:", data)
            time.sleep(5)
            continue

        for update in data.get("result", []):
            offset = update["update_id"] + 1

            # پیام خصوصی
            if "message" in update:
                message = update["message"]
                chat = message["chat"]

                chat_id = chat["id"]
                text = message.get("text", "")

                print("Private chat:", chat_id)

                if text == "/start":
                    send_message(
                        chat_id,
                        f"سلام 👋\n\nChat ID شما:\n{chat_id}"
                    )

            # پیام داخل کانال
            if "channel_post" in update:
                post = update["channel_post"]
                chat = post["chat"]

                chat_id = chat["id"]
                title = chat.get("title", "")

                print(f"CHANNEL FOUND: {title} -> {chat_id}")

                send_message(
                    chat_id,
                    f"✅ بات فعال است.\n\n"
                    f"نام کانال: {title}\n"
                    f"Chat ID: {chat_id}"
                )

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
