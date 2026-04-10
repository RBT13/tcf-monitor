import time
import random
import requests
import json
from playwright.sync_api import sync_playwright

# ================= 配置 =================
BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = "5068415693"   # ⚠️ 一定要是字符串


URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

# 页面刷新间隔（防封）
MIN_INTERVAL = 180
MAX_INTERVAL = 300

CHECK_INTERVAL = 5   # 页面内短检查

NOTIFY_COOLDOWN = 120


# ================= Telegram =================
def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)


# ================= 主程序 =================
def main():
    print("🔥 TCF Monitor（No-session检测版）")

    send_telegram("🚀 TCF Monitor 启动")

    last_notify_time = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        context = browser.new_context()
        page = context.new_page()

        while True:
            try:
                print("\n💓 新一轮访问页面")

                page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(8000)

                # ================= 等待进入真实页面 =================
                while True:

                    if page.locator("text=Virtual Waiting Room").count() > 0:
                        print("⏳ queue中...")
                        time.sleep(5)
                        continue

                    if page.locator("text=Registrations").count() > 0:
                        print("✅ 已进入页面")
                        break

                    print("⏳ 等待页面加载...")
                    time.sleep(5)

                # ================= 检测 No session =================
                nosession_list = []
                page.wait_for_timeout(3000)

                for _ in range(3):

                    nosession_count = page.locator("text=Register").count()

                    nosession_list.append(nosession_count)

                    print("📊 当前 No-session 数:", nosession_count)

                    time.sleep(CHECK_INTERVAL)

                nosession_count = max(set(nosession_list), key=nosession_list.count)

                print("📊 稳定 No-session 数:", nosession_count)

                now = time.time()

                # ================= 有考位 =================
                if nosession_count < 2:

                    if now - last_notify_time > NOTIFY_COOLDOWN:

                        print("🎉 检测到考位!")

                        send_telegram(
                            "🎉 TCF Canada 有新的考试位置!\n\n"
                            f"{URL}"
                        )

                        last_notify_time = now

                    sleep_time = random.randint(30, 60)

                # ================= 没位置 =================
                else:
                    print("😴 没有考位，准备离开页面")

                    sleep_time = random.randint(MIN_INTERVAL, MAX_INTERVAL)

                    try:
                        page.close()
                        print("🛑 已关闭当前页面")
                    except:
                        pass

                print(f"⏱ 下次访问间隔: {sleep_time}s")
                time.sleep(sleep_time)

                page = context.new_page()
                print("🆕 新页面已创建")

            except Exception as e:
                print("❌ 错误:", e)
                time.sleep(30)


if __name__ == "__main__":
    main()