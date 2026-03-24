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


# ================= Telegram 通知函数 =================
def send_telegram(msg):
    """发送 Telegram 消息"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("❌ Telegram error:", e)


# ================= 创建浏览器 =================
def create_browser(p):
    """初始化 Playwright 浏览器"""
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ]
    )
    context = browser.new_context()
    return browser, context


# ================= 判断页面状态 =================
def check_page(page):
    """
    判断当前页面状态：
    return:
        queue   -> 排队中
        blocked -> 被拦截
        loading -> 页面未加载完成
        full    -> 没有考位（显示 no sessions）
        open    -> 可能有考位（关键词消失）
    """

    text = page.inner_text("body").lower()

    # ========== Queue 排队页面 ==========
    if "queue-fair" in text or "virtual waiting room" in text:
        return "queue"

    # ========== 被 Cloudflare / 安全拦截 ==========
    if "checking your browser" in text or "access denied" in text:
        return "blocked"

    # ========== 页面未加载完整 ==========
    if len(text) < 2000:
        return "loading"

    # ========== 核心判断逻辑 ==========
    occurrences = text.count(KEYWORD)

    # 如果关键词出现多次 => 基本说明“没位置”
    if occurrences >= 2:
        return "full"
    elif occurrences == 0:
        return "open"
    else:
        return "unknown"


# ================= Queue 等待逻辑（关键） =================
def wait_in_queue(page):
    """
    Queue-Fair 等待逻辑：
    ❗重点：不刷新页面，不重新进入，只等待自动跳转
    """

    print("⏳ 进入排队模式（静默等待，不通知 Telegram）")

    while True:
        try:
            text = page.inner_text("body").lower()

            # 如果已经离开 queue 页面 -> 说明排队结束
            if "queue-fair" not in text and "virtual waiting room" not in text:
                print("🚀 已离开 Queue-Fair，进入目标页面")
                return

            # 仍在排队
            print("⏳ 排队中...等待系统放行")

            time.sleep(QUEUE_CHECK_INTERVAL)

        except Exception as e:
            print("⚠️ queue check error:", e)
            time.sleep(QUEUE_CHECK_INTERVAL)


# ================= 主程序 =================
def main():
    print("🔥 TCF Monitor v8 启动（Queue静默 + 状态监控版）")

    send_telegram("🚀 TCF Monitor 已启动（v8 Queue静默模式）")

    last_state = None
    last_notify_time = 0

    with sync_playwright() as p:
        browser, context = create_browser(p)
        page = context.new_page()

        while True:
            print("\n💓 心跳检测...")

            try:
                # ================= 打开页面 =================
                page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)

                status = check_page(page)

                # ================= QUEUE 模式 =================
                if status == "queue":
                    # ❗不发 Telegram，不打扰用户
                    wait_in_queue(page)
                    continue

                # ================= BLOCKED =================
                if status == "blocked":
                    print("🚨 被拦截")
                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                # ================= LOADING =================
                if status == "loading":
                    print("⏳ 页面未加载完成")
                    time.sleep(20)
                    continue

                # ================= 状态处理 =================
                current_state = status
                print("📊 当前状态:", current_state)

                # 第一次初始化状态
                if last_state is None:
                    last_state = current_state
                    time.sleep(random.randint(MIN_INTERVAL, MAX_INTERVAL))
                    continue

                now = time.time()

                # 是否发生变化
                changed = current_state != last_state

                # 只在 “满位 → 开放” 时通知
                improved = last_state == "full" and current_state == "open"

                if changed and improved and (now - last_notify_time > NOTIFY_COOLDOWN):
                    send_telegram(
                        "🎉 TCF Canada 可能出现考位！\n\n"
                        f"状态变化: {last_state} → {current_state}\n\n"
                        f"链接: {URL}"
                    )

                    last_notify_time = now

                last_state = current_state

            except Exception as e:
                print("❌ 主循环异常:", e)
                time.sleep(30)


if __name__ == "__main__":
    main()