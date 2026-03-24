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

KEYWORD = "No sessions currently available"


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
    print("🔥 TCF Monitor v20（最终行为优化版）")

    send_telegram("🚀 TCF Monitor v20 启动")

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

                    if page.locator("text=Registration").count() > 0:
                        print("✅ 已进入页面")
                        break

                    print("⏳ 等待页面加载...")
                    time.sleep(5)

                # ================= 短时间确认（避免误判） =================
                occurrences_list = []

                for _ in range(3):   # 连续检测3次
                    occurrences = page.locator(f"text={KEYWORD}").count()
                    occurrences_list.append(occurrences)

                    print("📊 当前 occurrences:", occurrences)
                    time.sleep(CHECK_INTERVAL)

                # 取“最稳定值”
                occurrences = max(set(occurrences_list), key=occurrences_list.count)

                print("📊 稳定结果:", occurrences)

                now = time.time()

                # ================= 有位置 =================
                if occurrences == 1:
                    if now - last_notify_time > NOTIFY_COOLDOWN:
                        print("🎉 检测到考位！")

                        send_telegram(
                            "🎉 TCF Canada 可能出现考位！\n\n"
                            f"当前匹配数: {occurrences}\n\n"
                            + URL
                        )

                        last_notify_time = now

                    # 👉 有位置时可以短间隔再查一次（更激进）
                    sleep_time = random.randint(5, 15)

                # ================= 没位置 =================
                else:
                    print("😴 没有考位，准备离开页面")

                    sleep_time = random.randint(MIN_INTERVAL, MAX_INTERVAL)
                    # ⭐ 关键：关闭页面（真正离开）
                    try:
                        page.close()
                        print("🛑 已关闭当前页面")
                    except:
                        pass

                print(f"⏱ 下次访问间隔: {sleep_time}s")
                time.sleep(sleep_time)

                # ⭐ 关键：重新创建页面（全新环境）
                page = context.new_page()
                print("🆕 新页面已创建")

            except Exception as e:
                print("❌ 错误:", e)
                time.sleep(30)


if __name__ == "__main__":
    main()