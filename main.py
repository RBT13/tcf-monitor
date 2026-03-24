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


# ================= STATE =================
base_interval = 240   # 4 min
min_interval = 180    # 3 min
max_interval = 420    # 7 min

session = requests.Session()
last_notify = 0


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
def refresh_requests_session():
    global session

    print("♻️ refreshing requests session...")

    try:
        session = requests.Session()
    except:
        pass


# ================= PLAYWRIGHT BOOT =================
def create_browser():
    p = sync_playwright().start()

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    context = browser.new_context()

    page = context.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    return p, browser, context, page


# ================= PRIMARY (BROWSER REQUEST) =================
def fetch_primary(context, url):
    try:
        resp = context.request.get(url)

        if resp.status != 200:
            print("🔎 primary status:", resp.status)
            return None

        text = resp.text()

        if not text or len(text) < 10:
            return None

        return text

    except Exception as e:
        print("❌ primary error:", e)
        return None


# ================= FALLBACK (REQUESTS) =================
def fetch_fallback(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 Chrome/120",
            "Accept": "application/json, text/plain, */*",
            "Referer": URL
        }

        r = session.get(url, headers=headers, timeout=15)

        print("🔎 fallback status:", r.status_code)

        if r.status_code != 200:
            return None

        if not r.text or len(r.text) < 10:
            return None

        return r.text

    except Exception as e:
        print("❌ fallback error:", e)
        return None


# ================= PARSE =================
def parse(text):
    try:
        import json
        data = json.loads(text)

        items = data.get("items", [])
        total = data.get("totalItems", 0)

        return max(len(items), int(total))

    except:
        return 0


# ================= DUAL CHECK =================
def check_all(context):
    total = 0
    used_fallback = False

    for url in API_URLS:

        # 🥇 PRIMARY
        text = fetch_primary(context, url)

        # 🥈 FALLBACK
        if text is None:
            used_fallback = True
            text = fetch_fallback(url)

        count = parse(text)

        print("🔎 count:", count)
        total += count

    return total, used_fallback


# ================= ADAPTIVE INTERVAL =================
def get_interval(last, current, fallback_used):
    global base_interval

    jitter = random.randint(-40, 40)

    changed = (last is not None and current != last)

    # ⚠️ fallback used → increase safety delay
    if fallback_used:
        base_interval += 30

    # change behavior
    if changed:
        base_interval = max(min_interval, base_interval - 10)
    else:
        base_interval = min(max_interval, base_interval + 10)

    # clamp
    base_interval = max(min_interval, min(max_interval, base_interval))

    return base_interval + jitter


# ================= MAIN =================
def main():
    global last_notify

    print("🚀 Dual-protection monitor started")

    send("🚀 TCF Monitor 启动（双保险稳定版）")

    refresh_requests_session()

    p, browser, context, page = create_browser()

    last = None

    try:
        while True:

            current, fallback_used = check_all(context)

            print("📊 TOTAL:", current, "| fallback:", fallback_used)

            now = time.time()

            # ================= notify =================
            if last is not None and current > last:
                if now - last_notify > 180:
                    send(
                        "🎉 TCF Canada 更新！\n\n"
                        f"之前: {last}\n现在: {current}"
                    )
                    last_notify = now

            last = current

            # ================= interval =================
            interval = get_interval(last, current, fallback_used)

            interval = max(min_interval, min(max_interval, interval))

            print(f"⏱ next check in {interval:.1f}s")
            time.sleep(interval)

    except Exception as e:
        print("❌ fatal error:", e)

    finally:
        try:
            browser.close()
            p.stop()
        except:
            pass


if __name__ == "__main__":
    main()