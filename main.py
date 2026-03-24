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


# ================= ADAPTIVE STATE =================
base_interval = 180  # ⭐ 3 minutes start baseline
min_interval = 180   # ⭐ 3 min minimum
max_interval = 300   # ⭐ 5 min maximum

fail_streak = 0
success_streak = 0
last_notify = 0

session = requests.Session()

# ================= TELEGRAM =================
def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass


# ================= SESSION REFRESH =================
def refresh_session():
    global session

    print("♻️ refreshing session...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        context = browser.new_context()
        page = context.new_page()

        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        session = requests.Session()

        for c in context.cookies():
            session.cookies.set(c["name"], c["value"])

        browser.close()

    print("✅ session refreshed")


# ================= FETCH =================
def fetch(url):
    headers = {
        "User-Agent": "Mozilla/5.0 Chrome/120",
        "Accept": "application/json, text/plain, */*",
        "Referer": URL,
        "Origin": "https://www.alliance-francaise.ca"
    }

    try:
        r = session.get(url, headers=headers, timeout=15)

        print("🔎 status:", r.status_code)

        # ================= THROTTLE =================
        if r.status_code == 202:
            return "pending"

        if r.status_code != 200:
            return None

        if not r.text or len(r.text) < 10:
            return None

        return r.json()

    except Exception as e:
        print("❌ fetch error:", e)
        return None


# ================= PARSE =================
def parse(data):
    if data == "pending":
        return -1

    if not data:
        return 0

    items = data.get("items", [])
    total = data.get("totalItems", 0)

    return max(len(items), int(total))


# ================= CHECK =================
def check_all():
    total = 0
    pending = False

    for url in API_URLS:
        data = fetch(url)
        count = parse(data)

        if count == -1:
            pending = True
            continue

        print("🔎 count:", count)
        total += count

    return total, pending


# ================= ADAPTIVE CONTROL (SAFE MODE) =================
def adjust_interval(success, pending):
    global base_interval

    jitter = random.randint(-20, 20)

    # 🚨 202 / throttle → 强降速
    if pending:
        base_interval = min(max_interval, base_interval + 40)
        return min(max_interval, base_interval + jitter + 30)

    # ❌ error → 降速
    if not success:
        base_interval = min(max_interval, base_interval + 30)
        return min(max_interval, base_interval + jitter + 20)

    # 🟢 success → 轻微加速但不突破安全线
    base_interval = max(min_interval, base_interval - 5)

    # ⭐ 强制安全下限（关键：防止太激进）
    if base_interval < 180:
        base_interval = 180

    return base_interval + jitter


# ================= MAIN =================
def main():
    global fail_streak, success_streak, last_notify

    print("🔥 Stable adaptive monitor started (3–5 min safe mode)")

    send("🚀 TCF Monitor 启动（稳定防封 3–5min 模式）")

    refresh_session()

    last = None

    while True:
        try:
            current, pending = check_all()

            print("📊 TOTAL:", current, "| pending:", pending)

            # ================= pending handling =================
            if pending:
                print("⏳ throttled → cooling down")
                fail_streak += 1
            else:
                fail_streak = 0

            # ================= first run =================
            if last is None:
                last = current

            changed = current != last
            improved = current > last

            now = time.time()

            # ================= notify =================
            if changed and improved:
                success_streak += 1

                if now - last_notify > 180:
                    send(
                        "🎉 TCF Canada 更新检测\n\n"
                        f"之前: {last}\n现在: {current}"
                    )
                    last_notify = now
            else:
                success_streak = max(0, success_streak - 1)

            # ================= session refresh =================
            if fail_streak >= 5:
                refresh_session()
                fail_streak = 0

            last = current

            # ================= interval =================
            interval = adjust_interval(
                success=(current >= 0),
                pending=pending
            )

            print(f"⏱ next check in {interval:.1f}s")

        except Exception as e:
            print("❌ loop error:", e)
            fail_streak += 1

            if fail_streak >= 3:
                refresh_session()
                fail_streak = 0

            interval = random.randint(180, 300)

        time.sleep(interval)


if __name__ == "__main__":
    main()