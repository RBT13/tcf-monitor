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
    """发送 Telegram 消息"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)


# ================= 浏览器初始化 =================
def create_browser(p):
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )
    context = browser.new_context()
    return browser, context


# ================= 状态判断 =================
def detect_state(page):
    """
    返回状态：
    queue / blocked / loading / full / open
    """

    text = page.inner_text("body").lower()

    # ===== Queue =====
    if "queue-fair" in text or "virtual waiting room" in text:
        return "queue"

    # ===== Block =====
    if "checking your browser" in text or "access denied" in text:
        return "blocked"

    # ===== Loading =====
    if len(text) < 2500:
        return "loading"

    # ===== 核心判断 =====
    occurrences = text.count(KEYWORD)

    if occurrences >= 2:
        return "full"
    elif occurrences == 0:
        return "open"
    else:
        return "unknown"


# ================= ⭐ Queue稳定等待（关键修复） =================
def wait_queue(page):
    """
    🚨 工业级 queue handler（修复误退出问题）

    核心思想：
    ❗不能只看一次 DOM
    ❗必须“连续确认已离开 queue”
    """

    print("⏳ 进入 Queue 稳定等待模式（双重确认）")

    exit_confirm_counter = 0  # ⭐关键：连续脱离计数

    while True:
        try:
            text = page.inner_text("body").lower()

            in_queue = ("queue-fair" in text or "virtual waiting room" in text)

            # ================= 仍在 queue =================
            if in_queue:
                exit_confirm_counter = 0
                print("⏳ queue waiting...")
                time.sleep(QUEUE_CHECK_INTERVAL)
                continue

            # ================= 可能已离开 queue =================
            exit_confirm_counter += 1
            print(f"🔎 queue exit check {exit_confirm_counter}/2")

            # ⭐必须连续2次确认离开 queue 才算真正退出
            if exit_confirm_counter >= 2:
                print("🚀 已确认离开 Queue（稳定退出）")
                return

            time.sleep(QUEUE_CHECK_INTERVAL)

        except Exception as e:
            print("queue error:", e)
            time.sleep(QUEUE_CHECK_INTERVAL)


# ================= 主程序 =================
def main():
    print("🔥 TCF Monitor v11 (Industrial Stable Queue Fix)")

    send_telegram("🚀 TCF Monitor v11 启动（Queue稳定修复版）")

    last_state = None
    last_notify_time = 0

    with sync_playwright() as p:
        browser, context = create_browser(p)
        page = context.new_page()

        while True:
            try:
                print("\n💓 cycle start")

                # ================= 页面加载 =================
                try:
                    page.goto(URL, wait_until="networkidle", timeout=60000)
                except:
                    page.goto(URL, wait_until="domcontentloaded", timeout=60000)

                page.wait_for_timeout(4000)

                state = detect_state(page)

                # ================= QUEUE =================
                if state == "queue":
                    wait_queue(page)
                    continue

                # ================= BLOCK =================
                if state == "blocked":
                    print("🚨 blocked")
                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                # ================= LOADING =================
                if state == "loading":
                    print("⏳ loading")
                    time.sleep(20)
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

                # ================= 只在确定变化时通知 =================
                if changed and improved and (now - last_notify_time > NOTIFY_COOLDOWN):
                    send_telegram(
                        "🎉 TCF Canada 可能出现考位！\n\n"
                        f"状态变化：{last_state} → {state}\n\n"
                        + URL
                    )
                    last_notify_time = now

                last_state = state

                # ================= 随机延迟 =================
                sleep_time = random.randint(MIN_INTERVAL, MAX_INTERVAL)
                print(f"⏱ sleep {sleep_time}s")
                time.sleep(sleep_time)

            except Exception as e:
                print("❌ error:", e)
                time.sleep(30)


if __name__ == "__main__":
    main()