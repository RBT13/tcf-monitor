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
base_interval = 240   # ⭐ 4 min start
min_interval = 180    # 3 min
max_interval = 360    # 6 min

last_notify = 0


# ================= TELEGRAM =================
def send(msg):
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass


# ================= BROWSER SESSION =================
def create_browser():
    p = sync_playwright().start()

    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    context = browser.new_context()
    page = context.new_page()

    return p, browser, context, page


def init_page(page):
    print("🌐 loading main page...")
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)


# ================= BROWSER-BASED API CALL =================
def fetch_api(page, url):
    try:
        result = page.evaluate(
            """async (url) => {
                try {
                    const res = await fetch(url, {
                        method: 'GET',
                        credentials: 'include',
                        headers: {
                            'accept': 'application/json, text/plain, */*'
                        }
                    });
                    const text = await res.text();
                    return { status: res.status, text };
                } catch (e) {
                    return { status: 0, text: '' };
                }
            }""",
            url
        )

        print("🔎 status:", result["status"])

        if result["status"] != 200:
            return None

        if not result["text"] or len(result["text"]) < 10:
            return None

        return result["text"]

    except Exception as e:
        print("❌ fetch error:", e)
        return None


# ================= PARSE =================
def parse_json(text):
    try:
        import json
        data = json.loads(text)
        items = data.get("items", [])
        total = data.get("totalItems", 0)
        return max(len(items), int(total))
    except:
        return 0


# ================= CHECK =================
def check_all(page):
    total = 0

    for url in API_URLS:
        text = fetch_api(page, url)
        count = parse_json(text)

        print("🔎 count:", count)
        total += count

    return total


# ================= ADAPTIVE INTERVAL =================
def get_interval(last, current):
    global base_interval

    jitter = random.randint(-30, 30)

    # change detection
    changed = (last is not None and current != last)

    if changed:
        base_interval = max(min_interval, base_interval - 10)
    else:
        base_interval = min(max_interval, base_interval + 10)

    return max(min_interval, min(max_interval, base_interval + jitter))


# ================= MAIN =================
def main():
    global last_notify

    print("🚀 Browser-native monitor started (anti-202 stable mode)")

    send("🚀 TCF Monitor 启动（Browser-native 稳定版）")

    p, browser, context, page = create_browser()
    init_page(page)

    last = None

    try:
        while True:
            current = check_all(page)

            print("📊 TOTAL:", current)

            now = time.time()

            # ================= notify =================
            if last is not None and current > last:
                if now - last_notify > 180:
                    send(
                        "🎉 TCF Canada 出现更新！\n\n"
                        f"之前: {last}\n现在: {current}"
                    )
                    last_notify = now

            last = current

            # ================= interval =================
            interval = get_interval(last, current)

            print(f"⏱ next check in {interval:.1f}s")
            time.sleep(interval)

    except Exception as e:
        print("❌ fatal error:", e)

    finally:
        browser.close()
        p.stop()


if __name__ == "__main__":
    main()