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

        print("📲 Telegram:", r.text)

    except Exception as e:
        print("Telegram error:", e)


# ================= Playwright =================
def get_page():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            page = browser.new_page()
            page.goto(URL, timeout=60000)
            page.wait_for_timeout(5000)

            html = page.content()
            browser.close()

            return html

    except Exception as e:
        print("浏览器错误:", e)
        return ""


# ================= 判断 =================
def has_slots(html):
    if not html:
        return False

    # 最稳判断：只要不包含 no sessions 就算可能有
    return "No sessions currently available" not in html


# ================= 主程序 =================
def main():
    print("🚀 TCF monitor started")

    last_state = None

    while True:
        try:
            html = get_page()
            available = has_slots(html)

            print("状态:", "可能有考位" if available else "暂无", time.strftime("%H:%M:%S"))

            if last_state is None:
                last_state = available

            elif available and not last_state:
                print("🎉 检测到变化！发送通知")

                send_telegram(
                    "🎉 TCF Canada 可能开放新考位！\n\n" + URL
                )

            last_state = available

        except Exception as e:
            print("主循环错误:", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()