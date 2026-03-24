import time
import random
import requests
import json
from playwright.sync_api import sync_playwright

# ================= 配置 =================
BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = "5068415693"   # ⚠️ 一定要是字符串


URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

MIN_INTERVAL = 180   # 3 min
MAX_INTERVAL = 300   # 5 min

QUEUE_INTERVAL = 15
NOTIFY_COOLDOWN = 90

KEYWORD = "no sessions currently available"


def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass


def create_browser(p):
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )
    return browser, browser.new_context()


def check_page(context):
    page = None

    try:
        page = context.new_page()

        page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        text = page.inner_text("body").lower()

        # ================= QUEUE =================
        if "queue-fair" in text or "virtual waiting room" in text:
            page.close()
            return {"status": "queue"}

        # ================= BLOCKED =================
        if "checking your browser" in text or "access denied" in text:
            page.close()
            return {"status": "blocked"}

        # ================= LOADING CHECK =================
        # 页面太短 = 可能未加载完成
        if len(text) < 2000:
            page.close()
            return {"status": "loading"}

        # ================= CORE LOGIC =================
        occurrences = text.count(KEYWORD)

        page.close()

        return {
            "status": "ok",
            "occurrences": occurrences,
            "raw_len": len(text)
        }

    except Exception as e:
        try:
            if page:
                page.close()
        except:
            pass

        return {"status": "error"}


def main():
    print("🔥 TCF monitor started (v6 stable state machine)")

    send_telegram("🚀 TCF Monitor v6 启动（稳定状态机版本）")

    last_state = None
    last_notify_time = 0

    with sync_playwright() as p:
        browser, context = create_browser(p)

        while True:
            print("\n💓 alive ping")

            try:
                if not browser.is_connected():
                    browser, context = create_browser(p)

                result = check_page(context)

                status = result["status"]

                # ================= QUEUE =================
                if status == "queue":
                    print("⏳ queue waiting")
                    time.sleep(QUEUE_INTERVAL)
                    continue

                # ================= BLOCK =================
                if status == "blocked":
                    print("🚨 blocked")
                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                # ================= LOADING =================
                if status == "loading":
                    print("⏳ loading page, skip")
                    time.sleep(30)
                    continue

                if status == "error":
                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                occurrences = result["occurrences"]

                print("📊 occurrences:", occurrences, "len:", result["raw_len"])

                # ================= 状态定义（关键修复） =================

                if occurrences >= 2:
                    current_state = "FULLY_BLOCKED"
                elif occurrences == 0:
                    current_state = "POSSIBLE_OPEN"
                else:
                    current_state = "UNKNOWN"

                print("🧠 state:", current_state)

                # ================= init =================
                if last_state is None:
                    last_state = current_state
                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                now = time.time()
                changed = current_state != last_state

                # 👉 只在：FULLY_BLOCKED → POSSIBLE_OPEN 时通知
                improved = last_state == "FULLY_BLOCKED" and current_state == "POSSIBLE_OPEN"

                if changed and improved and (now - last_notify_time > NOTIFY_COOLDOWN):
                    send_telegram(
                        "🎉 TCF Canada 可能出现考位变化！\n\n"
                        f"状态变化: {last_state} → {current_state}\n"
                        f"匹配次数: {occurrences}\n\n"
                        + URL
                    )

                    last_notify_time = now

                last_state = current_state

            except Exception as e:
                print("❌ loop error:", e)

                try:
                    browser.close()
                except:
                    pass

                browser, context = create_browser(p)

            sleep_time = random.randint(MIN_INTERVAL, MAX_INTERVAL)
            print(f"⏱ sleeping {sleep_time}s")
            time.sleep(sleep_time)


if __name__ == "__main__":
    main()