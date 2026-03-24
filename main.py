import time
import random
import requests
import json
from playwright.sync_api import sync_playwright

# ================= 配置 =================
BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = "5068415693"   # ⚠️ 一定要是字符串


URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

# 正常情况下的检查间隔（3~5分钟随机，防止被封）
MIN_INTERVAL = 180
MAX_INTERVAL = 300

# Queue状态下检查频率（更快判断是否放行）
QUEUE_CHECK_INTERVAL = 8

# 防止重复通知（秒）
NOTIFY_COOLDOWN = 100

# 页面关键词（用于判断是否满位）
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


# ================= browser =================
def create_browser(p):
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )
    context = browser.new_context()
    return browser, context


# ================= ⭐ 稳定页面读取（关键修复） =================
def get_stable_text(page):
    """
    工业级稳定读取：
    - 等 DOM 稳定
    - 防止 loading 假状态
    """

    page.wait_for_timeout(3000)

    text1 = page.inner_text("body").lower()
    page.wait_for_timeout(2000)
    text2 = page.inner_text("body").lower()

    # 如果两次一致 → 说明页面稳定
    if text1 == text2:
        return text2

    # 不稳定 → 再等一次
    page.wait_for_timeout(2000)
    return page.inner_text("body").lower()


# ================= 状态判断 =================
def detect_state(text):
    """
    queue / blocked / full / open
    """

    # ===== queue =====
    if "queue-fair" in text or "virtual waiting room" in text:
        return "queue"

    # ===== blocked =====
    if "checking your browser" in text or "access denied" in text:
        return "blocked"

    # ===== 核心逻辑 =====
    occurrences = text.count(KEYWORD)

    if occurrences >= 2:
        return "full"
    elif occurrences == 0:
        return "open"
    else:
        return "unknown"


# ================= Queue等待 =================
def wait_queue(page):
    print("⏳ Queue模式（稳定等待，不刷新）")

    stable_exit = 0

    while True:
        text = page.inner_text("body").lower()

        if "queue-fair" in text or "virtual waiting room" in text:
            stable_exit = 0
            print("⏳ queue waiting...")
            time.sleep(QUEUE_CHECK_INTERVAL)
            continue

        stable_exit += 1
        print(f"🔎 queue exit confirm {stable_exit}/2")

        if stable_exit >= 2:
            print("🚀 确认离开 queue")
            return

        time.sleep(QUEUE_CHECK_INTERVAL)


# ================= 主程序 =================
def main():
    print("🔥 TCF Monitor v12 (Stable DOM + No loading bug)")

    send_telegram("🚀 TCF Monitor v12 启动（DOM稳定修复版）")

    last_state = None
    last_notify_time = 0

    with sync_playwright() as p:
        browser, context = create_browser(p)
        page = context.new_page()

        while True:
            try:
                print("\n💓 cycle start")

                # ================= 页面加载 =================
                page.goto(URL, wait_until="domcontentloaded", timeout=60000)

                # ⭐关键修复：稳定读取 DOM（解决你 loading 问题）
                text = get_stable_text(page)

                state = detect_state(text)

                # ================= queue =================
                if state == "queue":
                    wait_queue(page)
                    continue

                # ================= blocked =================
                if state == "blocked":
                    print("🚨 blocked")
                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                print("📊 state:", state)

                # ================= 初始化 =================
                if last_state is None:
                    last_state = state
                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                now = time.time()

                changed = state != last_state
                improved = last_state == "full" and state == "open"

                if changed and improved and (now - last_notify_time > NOTIFY_COOLDOWN):
                    send_telegram(
                        "🎉 TCF Canada 可能出现考位！\n\n"
                        f"{last_state} → {state}\n\n"
                        + URL
                    )
                    last_notify_time = now

                last_state = state

                sleep_time = random.randint(MIN_INTERVAL, MAX_INTERVAL)
                print(f"⏱ sleep {sleep_time}s")
                time.sleep(sleep_time)

            except Exception as e:
                print("❌ error:", e)
                time.sleep(30)


if __name__ == "__main__":
    main()