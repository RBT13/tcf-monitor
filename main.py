import time
import random
import requests
import json
from playwright.sync_api import sync_playwright

# ================= 配置 =================
BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = "5068415693"   # ⚠️ 一定要是字符串


URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

# 初始访问间隔（进入页面前）
MIN_INTERVAL = 180
MAX_INTERVAL = 300

# 页面内轮询间隔（进入页面后）
CHECK_INTERVAL = 7

# 防重复通知
NOTIFY_COOLDOWN = 120

KEYWORD = "no sessions currently available"


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
    print("🔥 TCF Monitor v14（极简稳定版）")

    send_telegram("🚀 TCF Monitor v14 启动（极简监控模式）")

    last_occurrences = None
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
                print("\n💓 新一轮进入页面")

                # ================= 只在这里访问一次页面 =================
                page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)

                # ================= 页面内持续检测 =================
                while True:
                    try:
                        text = page.inner_text("body").lower()

                        occurrences = text.count(KEYWORD)

                        print("📊 当前 occurrences:", occurrences)

                        # ===== 忽略异常页面（queue / loading）=====
                        if occurrences == 0:
                            print("⏳ 未检测到关键字（可能在queue或加载中）")
                            time.sleep(CHECK_INTERVAL)
                            continue

                        # ===== 初始化 =====
                        if last_occurrences is None:
                            last_occurrences = occurrences
                            time.sleep(CHECK_INTERVAL)
                            continue

                        now = time.time()

                        # ===== 核心逻辑 =====
                        # 从 2 → 1 才通知
                        if (
                            last_occurrences == 2 and
                            occurrences == 1 and
                            now - last_notify_time > NOTIFY_COOLDOWN
                        ):
                            print("🎉 检测到可能有考位！")

                            send_telegram(
                                "🎉 TCF Canada 可能出现考位！\n\n"
                                f"当前匹配数: {occurrences}\n\n"
                                + URL
                            )

                            last_notify_time = now

                        last_occurrences = occurrences

                        time.sleep(CHECK_INTERVAL)

                    except Exception as e:
                        print("⚠️ 页面检测异常:", e)
                        break  # 跳出内层循环，重新加载页面

                # ================= 防封：外层休眠 =================
                sleep_time = random.randint(MIN_INTERVAL, MAX_INTERVAL)
                print(f"⏱ 外层休眠 {sleep_time}s")
                time.sleep(sleep_time)

            except Exception as e:
                print("❌ 主循环异常:", e)
                time.sleep(30)


if __name__ == "__main__":
    main()