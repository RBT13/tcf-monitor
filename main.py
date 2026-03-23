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

# 防重复通知（10分钟冷却）
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


# ================= 安全 goto（关键修复） =================
def safe_goto(page, url):
    for i in range(3):
        try:
            page.goto(
                url,
                timeout=60000,
                wait_until="domcontentloaded"
            )
            return True
        except Exception as e:
            print(f"⚠️ goto retry {i+1}: {e}")
            time.sleep(3 + i * 2)
    return False


# ================= 检查页面 =================
def check_page(browser):
    page = None

    for attempt in range(2):  # 🔥 page级别重试
        try:
            page = browser.new_page()

            page.set_extra_http_headers({
                "User-Agent": random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) Chrome/118 Safari/537.36"
                ])
            })

            ok = safe_goto(page, URL)
            if not ok:
                raise Exception("goto failed")

            page.wait_for_timeout(4000)

            html = page.content()
            print("🔍 html length:", len(html))

            if len(html) < 500:
                raise Exception("empty page")

            text = page.inner_text("body")

            if "Registration" not in text:
                raise Exception("page not ready")

            # ================= 核心检测逻辑 =================
            nodes = page.locator("text=No sessions currently available")
            count = nodes.count()

            print("🔎 No sessions count:", count)

            page.close()
            return count

        except Exception as e:
            print(f"❌ attempt {attempt+1} failed:", e)

            try:
                if page:
                    page.close()
            except:
                pass

            time.sleep(2 + attempt * 3)

    print("🚨 check_page totally failed")
    return None


# ================= 主程序 =================
def main():
    print("🔥 TCF monitor started (Railway stable version)")
    send_telegram("🚀 TCF Monitor 已启动（Railway稳定修复版）")

    last_count = None
    last_notify_time = 0
    fail_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process"
            ]
        )

        while True:
            print("\n💓 alive ping")

            try:
                result = check_page(browser)

                # ================= 失败处理 =================
                if result is None:
                    fail_count += 1
                    print(f"⚠️ fetch failed ({fail_count})")

                    if fail_count >= FAIL_LIMIT:
                        print("♻️ restarting browser...")

                        try:
                            browser.close()
                        except:
                            pass

                        browser = p.chromium.launch(
                            headless=True,
                            args=[
                                "--no-sandbox",
                                "--disable-dev-shm-usage",
                                "--disable-gpu",
                                "--single-process"
                            ]
                        )

                        fail_count = 0

                    time.sleep(CHECK_INTERVAL)
                    continue

                fail_count = 0
                now = time.time()

                print("📊 status:", result)

                # ================= 初始化 =================
                if last_count is None:
                    last_count = result
                    time.sleep(CHECK_INTERVAL)
                    continue

                # ================= 状态变化判断 =================
                changed = result != last_count
                improved = result < last_count

                should_notify = (
                    changed and
                    improved and
                    (now - last_notify_time > NOTIFY_COOLDOWN)
                )

                if should_notify:
                    print("🎉 CHANGE detected!")

                    # 🔥 二次确认（防误报）
                    time.sleep(5)
                    confirm = check_page(browser)

                    if confirm is not None and confirm < last_count:
                        send_telegram(
                            "🎉 TCF Canada 可能出现新考位变化！\n\n"
                            f"之前: {last_count}\n现在: {confirm}\n\n{URL}"
                        )

                        last_count = confirm
                        last_notify_time = now
                    else:
                        print("⚠️ false positive ignored")

                last_count = result

            except Exception as e:
                print("❌ loop error:", e)

                # 🔥 loop级别恢复（关键修复 Railway crash）
                try:
                    browser.close()
                except:
                    pass

                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--single-process"
                    ]
                )

            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()