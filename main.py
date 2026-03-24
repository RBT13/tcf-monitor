import time
import random
import requests
from playwright.sync_api import sync_playwright

# ================= 配置 =================
URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = "5068415693"   # ⚠️ 一定要是字符串

CHECK_INTERVAL = 60
FAIL_LIMIT = 3

# 防重复通知（1.5分钟冷却）
NOTIFY_COOLDOWN = 90


# ================= Telegram =================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
        print("📲 Telegram response:", r.text)
    except Exception as e:
        print("❌ Telegram error:", e)


# ================= browser 重建 =================
def create_browser(p):
    print("♻️ launching browser...")

    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--single-process"
        ]
    )

    context = browser.new_context()
    return browser, context


# ================= 检查页面 =================
def check_page(context):
    page = None

    for attempt in range(2):
        try:
            page = context.new_page()

            page.set_extra_http_headers({
                "User-Agent": random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) Chrome/118 Safari/537.36"
                ])
            })

            page.goto(URL, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            html = page.content()
            print("🔍 html length:", len(html))

            text = page.inner_text("body")

            # ================= NEW: 更严格 BLOCKED 判断 =================
            strong_block = (
                "Checking your browser" in text or
                "Access denied" in text or
                "queue" in text.lower()
            )

            weak_block = len(html) < 8000

            if strong_block:
                print("🚨 STRONG BLOCK detected")
                page.close()
                return {"status": "blocked"}

            if weak_block:
                print("⚠️ weak block detected")
                page.close()
                return {"status": "weak_block"}

            if len(html) < 500:
                raise Exception("page too small")

            if "Registration" not in text:
                print("⚠️ Registration not found")
                page.close()
                return {"status": "not_ready"}

            count = page.locator("text=No sessions currently available").count()

            print("🔎 No sessions count:", count)

            page.close()
            return {"status": "ok", "count": count}

        except Exception as e:
            print(f"❌ attempt {attempt+1} failed:", e)

            try:
                if page:
                    page.close()
            except:
                pass

            time.sleep(2 + attempt * 2)

    print("🚨 check_page totally failed")
    return {"status": "error"}


# ================= 主程序 =================
def main():
    print("🔥 TCF monitor started (Railway production stable v2)")

    send_telegram("🚀 TCF Monitor 已启动（Railway稳定v2）")

    last_count = None
    last_notify_time = 0
    fail_count = 0

    weak_block_count = 0  # ✅ 新增

    with sync_playwright() as p:

        browser, context = create_browser(p)

        while True:
            print("\n💓 alive ping")

            try:
                # ================= browser health check =================
                if not browser.is_connected():
                    print("⚠️ browser dead -> restarting")
                    browser, context = create_browser(p)

                result = check_page(context)

                # ================= BLOCKED（强）=================
                if result["status"] == "blocked":
                    now = time.time()

                    if now - last_notify_time > NOTIFY_COOLDOWN:
                        send_telegram(
                            "🚨 TCF Canada 页面被拦截（强信号）！\n\n"
                            f"{URL}"
                        )
                        last_notify_time = now

                    time.sleep(CHECK_INTERVAL)
                    continue

                # ================= BLOCKED（弱，需要连续）=================
                if result["status"] == "weak_block":
                    weak_block_count += 1
                    print(f"⚠️ weak block count: {weak_block_count}")

                    if weak_block_count >= 2:
                        now = time.time()

                        if now - last_notify_time > NOTIFY_COOLDOWN:
                            send_telegram(
                                "⚠️ TCF Canada 页面异常（连续加载异常）\n\n"
                                f"{URL}"
                            )
                            last_notify_time = now

                        weak_block_count = 0

                    time.sleep(CHECK_INTERVAL)
                    continue
                else:
                    weak_block_count = 0

                # ================= fail =================
                if result["status"] != "ok":
                    fail_count += 1
                    print(f"⚠️ fetch failed ({fail_count})")

                    if fail_count >= FAIL_LIMIT:
                        print("♻️ hard restart browser")

                        try:
                            browser.close()
                        except:
                            pass

                        browser, context = create_browser(p)
                        fail_count = 0

                    time.sleep(CHECK_INTERVAL)
                    continue

                fail_count = 0
                now = time.time()

                current_count = result["count"]

                print("📊 status:", current_count)

                # ================= init =================
                if last_count is None:
                    last_count = current_count
                    time.sleep(CHECK_INTERVAL)
                    continue

                # ================= detect =================
                changed = current_count != last_count
                improved = current_count < last_count

                should_notify = (
                    changed and
                    improved and
                    (now - last_notify_time > NOTIFY_COOLDOWN)
                )

                if should_notify:
                    print("🎉 CHANGE detected!")

                    time.sleep(5)

                    confirm = check_page(context)

                    if (
                        confirm["status"] == "ok" and
                        confirm["count"] < last_count
                    ):
                        send_telegram(
                            "🎉 TCF Canada 可能出现考位变化！\n\n"
                            f"之前: {last_count}\n现在: {confirm['count']}\n\n{URL}"
                        )

                        last_count = confirm["count"]
                        last_notify_time = now
                    else:
                        print("⚠️ false positive ignored")

                last_count = current_count

            except Exception as e:
                print("❌ loop crash:", e)

                try:
                    browser.close()
                except:
                    pass

                browser, context = create_browser(p)

            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()