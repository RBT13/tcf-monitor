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

QUEUE_CHECK_INTERVAL = 15  # 排队时更频繁检查

NOTIFY_COOLDOWN = 90


# ================= Telegram =================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print("❌ Telegram error:", e)


# ================= browser =================
def create_browser(p):
    print("♻️ launching browser...")

    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--single-process"
        ]
    )

    context = browser.new_context()
    return browser, context


# ================= 页面检测 =================
def check_page(context):
    page = None

    try:
        page = context.new_page()

        page.set_extra_http_headers({
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) Chrome/118 Safari/537.36"
            ])
        })

        page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        text = page.inner_text("body").lower()

        # ================= Queue 判断 =================
        if "queue-fair" in text or "virtual waiting room" in text:
            queue_info = None

            # 尝试抓队列人数（不影响主逻辑）
            try:
                queue_info = page.inner_text("body")
            except:
                pass

            page.close()

            return {
                "status": "queue",
                "info": queue_info
            }

        # ================= blocked =================
        if "checking your browser" in text or "access denied" in text:
            page.close()
            return {"status": "blocked"}

        # ================= 核心检测 =================
        keyword = "no sessions currently available"
        occurrences = text.count(keyword)

        page.close()

        return {
            "status": "ok",
            "occurrences": occurrences
        }

    except Exception as e:
        print("❌ check error:", e)

        try:
            if page:
                page.close()
        except:
            pass

        return {"status": "error"}


# ================= 主循环 =================
def main():
    print("🔥 TCF monitor started (Queue-aware v5)")

    send_telegram("🚀 TCF Monitor 已启动（Queue-aware v5）")

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

                # ================= QUEUE =================
                if result["status"] == "queue":
                    print("⏳ In Queue-Fair waiting room...")

                    send_telegram("⏳ 正在排队（Queue-Fair waiting room）自动等待中...")

                    time.sleep(QUEUE_CHECK_INTERVAL)
                    continue

                # ================= BLOCKED =================
                if result["status"] == "blocked":
                    print("🚨 blocked")

                    now = time.time()
                    if now - last_notify_time > NOTIFY_COOLDOWN:
                        send_telegram("🚨 页面被拦截（Cloudflare / Access denied）\n" + URL)
                        last_notify_time = now

                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                if result["status"] == "error":
                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                occurrences = result["occurrences"]

                current_state = occurrences >= 2

                print("📊 occurrences:", occurrences, "| stable:", current_state)

                # ================= init =================
                if last_state is None:
                    last_state = current_state
                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                changed = current_state != last_state
                improved = last_state is True and current_state is False

                now = time.time()

                if changed and improved and (now - last_notify_time > NOTIFY_COOLDOWN):
                    send_telegram(
                        "🎉 TCF Canada 可能出现考位！\n\n"
                        f"匹配次数: {occurrences}\n\n"
                        + URL
                    )
                    last_notify_time = now

                last_state = current_state

            except Exception as e:
                print("❌ loop crash:", e)

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