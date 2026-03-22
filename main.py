import time
import random
import requests
from playwright.sync_api import sync_playwright

# ================= 配置 =================
URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = "5068415693"   # ⚠️ 一定要是字符串

CHECK_INTERVAL = 60


# ================= Telegram =================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print("📲 Telegram sent")
    except Exception as e:
        print("Telegram error:", e)


# ================= 抓页面 =================
def get_page():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"
            )

            page = context.new_page()
            page.goto(URL, timeout=60000)
            page.wait_for_timeout(5000)

            content = page.content()
            browser.close()

            # ❌ 被封检测
            if "403 - Forbidden" in content:
                print("❌ 403 blocked")
                return None

            return content

    except Exception as e:
        print("Playwright error:", e)
        return None


# ================= 判断逻辑 =================
def has_slots(html):
    if not html:
        return False

    if "No sessions currently available" in html:
        return False

    # 更保守：必须出现明确 booking 词才算
    keywords = ["Book", "Register", "Available"]

    return any(k in html for k in keywords)


# ================= 主循环 =================
def main():
    print("🚀 TCF Monitor started (stable version)")

    last_state = None

    while True:
        html = get_page()

        current = has_slots(html)

        print("🔁 status:", current, time.strftime("%H:%M:%S"))

        # 初始化状态
        if last_state is None:
            last_state = current

        # ❗ 从 False → True 才通知
        elif current and not last_state:
            print("🎉 SLOT FOUND!")
            send_telegram(f"🎉 TCF Canada 可能开放报名了！\n\n{URL}")

        last_state = current

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()