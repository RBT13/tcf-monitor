import time
import random
import requests
import json
from playwright.sync_api import sync_playwright

# ================= 配置 =================
BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = "5068415693"   # ⚠️ 一定要是字符串



URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

API_URLS = [
    "https://www.alliance-francaise.ca/api/groupcourses?enddate=gte&limit=150&openspaces=1&orderby=course.startDate&othercategory=368&status=0",
    "https://www.alliance-francaise.ca/api/groupcourses?enddate=gte&limit=150&openspaces=1&orderby=course.startDate&othercategory=367&status=0"
]


CHECK_INTERVAL = 60
FAIL_LIMIT = 3
NOTIFY_COOLDOWN = 120


# ================= Telegram =================
def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass


# ================= 全局 session =================
session = requests.Session()
fail_count = 0
last_notify = 0


# ================= Playwright 获取 cookie =================
def refresh_session():
    global session

    print("♻️ refreshing browser session...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        context = browser.new_context()
        page = context.new_page()

        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        cookies = context.cookies()

        session = requests.Session()

        # 把 cookies 注入 requests session
        for c in cookies:
            session.cookies.set(c["name"], c["value"])

        browser.close()

    print("✅ session refreshed")


# ================= API 请求 =================
def fetch(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": URL,
        "Origin": "https://www.alliance-francaise.ca"
    }

    try:
        r = session.get(url, headers=headers, timeout=15)

        if r.status_code != 200:
            print("❌ status:", r.status_code)
            return None

        return r.json()

    except Exception as e:
        print("❌ fetch error:", e)
        return None


# ================= 解析 =================
def parse(data):
    if not data:
        return 0

    items = data.get("items", [])
    total = data.get("totalItems", 0)

    return max(len(items), int(total))


# ================= 主检查 =================
def check_all():
    total = 0

    for url in API_URLS:
        data = fetch(url)
        count = parse(data)

        print("🔎 count:", count)

        total += count

    return total


# ================= 主循环 =================
def main():
    global fail_count, last_notify

    print("🔥 FINAL stable monitor started")

    send("🚀 TCF Monitor 启动（终极稳定版）")

    refresh_session()

    last = None

    while True:
        try:
            current = check_all()
            now = time.time()

            print("📊 TOTAL:", current)

            # ================= 初始化 =================
            if last is None:
                last = current
                time.sleep(CHECK_INTERVAL)
                continue

            # ================= 正常变化检测 =================
            changed = current != last
            improved = current > last

            if changed and improved:
                if now - last_notify > NOTIFY_COOLDOWN:

                    print("🎉 SLOT DETECTED!")

                    send(
                        "🎉 TCF Canada 出现新考位！\n\n"
                        f"之前: {last}\n现在: {current}\n\n{URL}"
                    )

                    last_notify = now

                last = current

            # ================= 更新 =================
            last = current
            fail_count = 0

        except Exception as e:
            print("❌ loop error:", e)

            fail_count += 1

            # ===== 自动恢复 session =====
            if fail_count >= FAIL_LIMIT:
                print("♻️ rebuilding session...")
                refresh_session()
                fail_count = 0

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()