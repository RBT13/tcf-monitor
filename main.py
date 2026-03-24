import time
import random
import requests
import json
from playwright.sync_api import sync_playwright

# ================= 配置 =================
BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = "5068415693"   # ⚠️ 一定要是字符串

URLS = [
    "https://www.alliance-francaise.ca/api/groupcourses?enddate=gte&limit=150&openspaces=1&orderby=course.startDate&othercategory=368&status=0",
    "https://www.alliance-francaise.ca/api/groupcourses?enddate=gte&limit=150&openspaces=1&orderby=course.startDate&othercategory=367&status=0"
]

CHECK_INTERVAL = 60
NOTIFY_COOLDOWN = 120  # 防刷屏


# ================= Telegram =================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
        print("📲 Telegram:", r.text)
    except Exception as e:
        print("❌ Telegram error:", e)


# ================= 拉 API =================
def fetch(url):
    try:
        r = requests.get(url, timeout=15)
        return r.json()
    except Exception as e:
        print("❌ fetch error:", url, e)
        return None


# ================= 检查单个 API =================
def check_api(data):
    if not data:
        return 0

    items = data.get("items", [])
    total = data.get("totalItems", 0)

    return max(len(items), int(total))


# ================= 主逻辑 =================
def check_all():
    total = 0

    for url in URLS:
        data = fetch(url)
        count = check_api(data)

        print("🔎 count:", count, "|", url)

        total += count

    return total


# ================= 主程序 =================
def main():
    print("🔥 TCF API monitor started (production v1)")

    send_telegram("🚀 TCF Monitor 已启动（API生产版）")

    last_total = None
    last_notify = 0

    while True:
        try:
            current_total = check_all()

            print("📊 TOTAL:", current_total)

            now = time.time()

            # ========== 初始化 ==========
            if last_total is None:
                last_total = current_total
                time.sleep(CHECK_INTERVAL)
                continue

            # ========== 有变化 ==========
            changed = current_total != last_total
            improved = current_total > last_total

            if changed and improved:
                if now - last_notify > NOTIFY_COOLDOWN:

                    print("🎉 NEW SLOTS DETECTED!")

                    send_telegram(
                        "🎉 TCF Canada 出现新考位！\n\n"
                        f"之前: {last_total}\n现在: {current_total}\n\n"
                        "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"
                    )

                    last_notify = now

                last_total = current_total

            # ========== 更新 ==========
            last_total = current_total

        except Exception as e:
            print("❌ loop error:", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()