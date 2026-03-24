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

# ================= Telegram通知 =================
def send_telegram(msg):
    """发送Telegram消息"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)


# ================= 创建浏览器 =================
def create_browser(p):
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )
    context = browser.new_context()
    return browser, context


# ================= 页面状态检测 =================
def detect_state(page):
    """
    返回状态：
    queue   -> 排队中
    blocked -> 被封
    loading -> 未加载完整
    full    -> 没考位
    open    -> 可能有考位
    """

    text = page.inner_text("body").lower()

    # ===== Queue =====
    if "queue-fair" in text or "virtual waiting room" in text:
        return "queue"

    # ===== Block =====
    if "checking your browser" in text or "access denied" in text:
        return "blocked"

    # ===== 关键修复：loading 判断（更严格）=====
    # 不再只看长度，而是看“关键内容是否存在”
    if KEYWORD not in text and len(text) < 3000:
        return "loading"

    # ===== 核心判断 =====
    occurrences = text.count(KEYWORD)

    if occurrences >= 2:
        return "full"
    elif occurrences == 0:
        return "open"
    else:
        return "unknown"


# ================= Queue等待（不刷新页面） =================
def wait_queue(page):
    """
    Queue-Fair 等待逻辑：
    ❗不 reload
    ❗不 goto
    ❗只等待系统自动放行
    """

    print("⏳ 进入 Queue 等待模式（静默）")

    while True:
        try:
            text = page.inner_text("body").lower()

            # 离开 queue
            if "queue-fair" not in text and "virtual waiting room" not in text:
                print("🚀 已离开 Queue")
                return

            print("⏳ queue waiting...")

            time.sleep(QUEUE_CHECK_INTERVAL)

        except Exception as e:
            print("queue error:", e)
            time.sleep(QUEUE_CHECK_INTERVAL)


# ================= 主程序 =================
def main():
    print("🔥 TCF Monitor v10 (Loading Fix + Stable Industrial Edition)")

    send_telegram("🚀 TCF Monitor v10 启动（loading修复+工业稳定版）")

    last_state = None
    last_notify_time = 0

    with sync_playwright() as p:
        browser, context = create_browser(p)
        page = context.new_page()

        while True:
            try:
                print("\n💓 cycle start")

                # ================= 页面加载（关键修复） =================
                try:
                    page.goto(URL, wait_until="networkidle", timeout=60000)
                except:
                    # fallback 防止 networkidle 卡死
                    page.goto(URL, wait_until="domcontentloaded", timeout=60000)

                page.wait_for_timeout(5000)

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
                    print("⏳ loading... retry later")
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

                # ================= 随机延迟（防封） =================
                sleep_time = random.randint(MIN_INTERVAL, MAX_INTERVAL)
                print(f"⏱ sleep {sleep_time}s")
                time.sleep(sleep_time)

            except Exception as e:
                print("❌ error:", e)
                time.sleep(30)


if __name__ == "__main__":
    main()