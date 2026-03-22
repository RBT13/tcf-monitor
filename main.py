import time
import requests
from playwright.sync_api import sync_playwright

# ================= 配置 =================
URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = 5068415693

CHECK_INTERVAL = 60

# ================= Telegram =================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        }, timeout=10)

        print("📲 Telegram response:", r.text)

    except Exception as e:
        print("❌ Telegram error:", e)


# ================= Playwright =================
def get_page():
    print("📡 Step 1: entering get_page")

    try:
        with sync_playwright() as p:
            print("📡 Step 2: launching chromium")

            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            print("📡 Step 3: browser launched")

            page = browser.new_page()

            print("📡 Step 4: going to URL")

            page.goto(URL, timeout=60000)

            print("📡 Step 5: waiting page load")

            page.wait_for_timeout(5000)

            html = page.content()

            browser.close()

            print("📡 Step 6: page fetched OK")

            return html

    except Exception as e:
        print("❌ get_page error:", e)
        return ""


# ================= 判断 =================
def has_slots(html):
    if not html:
        return False

    return "No sessions currently available" not in html


# ================= 主程序 =================
def main():
    print("🔥 container started")
    print("🔥 python main.py running")
    print("🚀 TCF monitor started")

    last_state = None

    while True:
        try:
            print("🔁 loop started")

            html = get_page()
            available = has_slots(html)

            print("📊 status:", "可能有考位" if available else "暂无")

            if last_state is None:
                last_state = available

            elif available and not last_state:
                print("🎉 CHANGE detected!")

                send_telegram(
                    "🎉 TCF Canada 可能有新考位！\n\n" + URL
                )

            last_state = available

        except Exception as e:
            print("❌ loop error:", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()