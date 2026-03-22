import time
import random
import requests
import os
from playwright.sync_api import sync_playwright

# ================= 配置 =================
URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyX"
CHAT_ID = 5068415693

CHECK_INTERVAL = 60


# ================= Telegram =================
def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Telegram env not set")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("❌ Telegram error:", e)


# ================= 检查页面 =================
def check_page(page):
    page.goto(URL, timeout=60000)
    page.wait_for_load_state("networkidle")

    text = page.inner_text("body")

    return "No sessions currently available" not in text


# ================= 主程序 =================
def main():
    print("🔥 TCF monitor started (Worker mode)")

    # ✅ 启动通知（确认云端真的在跑）
    send_telegram("🚀 TCF Monitor 已启动（Railway Worker 正常运行）")

    last_state = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        page = browser.new_page()

        # 伪装浏览器（防简单封禁）
        page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        })

        while True:
            try:
                print("🔁 checking...")

                available = check_page(page)

                print("📊 status:", "可能有考位" if available else "暂无")

                # 初始化状态
                if last_state is None:
                    last_state = available

                # 状态变化检测
                elif available and not last_state:
                    print("🎉 CHANGE detected!")

                    # ===== 二次确认 =====
                    time.sleep(5)
                    confirm = check_page(page)

                    if confirm:
                        send_telegram(
                            "🎉 TCF Canada 出现考位！\n\n" + URL
                        )
                        print("📲 notification sent")
                    else:
                        print("⚠️ false positive ignored")

                last_state = available

            except Exception as e:
                print("❌ loop error:", e)

                # 自动恢复 page
                try:
                    page.close()
                    page = browser.new_page()
                except:
                    pass

            # 随机延迟（防封）
            sleep_time = CHECK_INTERVAL + random.randint(0, 8)
            time.sleep(sleep_time)


if __name__ == "__main__":
    main()