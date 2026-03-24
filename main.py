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
QUEUE_WAIT = 8

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


# ================= 浏览器 =================
def create_browser(p):
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    return browser, browser.new_context()


# ================= ⭐ 真正 queue 检测（可见元素） =================
def in_queue(page):
    try:
        queue_visible = page.locator("text=Queue-Fair").first.is_visible(timeout=2000)
    except:
        queue_visible = False

    try:
        waiting_visible = page.locator("text=Virtual Waiting Room").first.is_visible(timeout=2000)
    except:
        waiting_visible = False

    return queue_visible or waiting_visible


# ================= ⭐ 主内容检测 =================
def get_state(page):
    """
    返回：
    queue / open / full / unknown
    """

    # ===== queue（必须可见层）=====
    if in_queue(page):
        return "queue"

    text = page.inner_text("body").lower()

    # ===== blocked =====
    if "checking your browser" in text or "access denied" in text:
        return "blocked"

    # ===== 核心 =====
    if KEYWORD in text:
        return "full"

    if "registration" in text or "sessions" in text:
        return "open"

    return "unknown"


# ================= ⭐ 防 bounce 状态机 =================
def stable_state(page, get_fn, required=3):
    """
    必须连续 N 次状态一致才允许切换
    """

    last = None
    count = 0

    for _ in range(required):
        state = get_fn(page)

        if state == last:
            count += 1
        else:
            count = 1
            last = state

        time.sleep(2)

    return last


# ================= Queue等待（稳定版） =================
def wait_queue(page):
    print("⏳ 进入 Queue（稳定等待）")

    stable_exit = 0

    while True:
        if in_queue(page):
            stable_exit = 0
            print("⏳ queue waiting...")
            time.sleep(QUEUE_WAIT)
            continue

        stable_exit += 1
        print(f"🔎 queue exit confirm {stable_exit}/3")

        if stable_exit >= 3:
            print("🚀 确认稳定离开 queue")
            return

        time.sleep(QUEUE_WAIT)


# ================= 主程序 =================
def main():
    print("🔥 TCF Monitor v13 (Anti-bounce + Visible Queue Fix)")

    send_telegram("🚀 TCF Monitor v13 启动（最终稳定版）")

    last_state = None
    last_notify = 0

    with sync_playwright() as p:
        browser, context = create_browser(p)
        page = context.new_page()

        while True:
            try:
                print("\n💓 cycle start")

                page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)

                # ⭐ 核心：稳定状态检测（防 bounce）
                state = stable_state(page, get_state)

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

                if changed and improved and (now - last_notify > NOTIFY_COOLDOWN):
                    send_telegram(
                        "🎉 TCF Canada 可能有新考位！\n\n"
                        f"{last_state} → {state}\n\n"
                        + URL
                    )
                    last_notify = now

                last_state = state

                sleep_time = random.randint(MIN_INTERVAL, MAX_INTERVAL)
                print(f"⏱ sleep {sleep_time}s")
                time.sleep(sleep_time)

            except Exception as e:
                print("❌ error:", e)
                time.sleep(30)


if __name__ == "__main__":
    main()