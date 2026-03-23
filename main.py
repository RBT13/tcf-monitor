import time
import random
import requests
from playwright.sync_api import sync_playwright

# ================= 配置 =================
URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = "5068415693"   # ⚠️ 一定要是字符串

CHECK_INTERVAL = 60

# ================= Telegram =================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
        print("📲 Telegram:", r.text)
    except Exception as e:
        print("❌ Telegram error:", e)


# ================= 页面检查（核心升级） =================
def check_page(browser):
    try:
        page = browser.new_page()

        page.set_extra_http_headers({
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) Chrome/118 Safari/537.36"
            ])
        })

        page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        html = page.content()
        if len(html) < 500:
            return None

        text = page.inner_text("body")

        if "Registration" not in text:
            return None

        # ================= 核心升级点 =================
        nodes = page.locator("text=No sessions currently available")
        count = nodes.count()

        print("🔎 No sessions count:", count)

        page.close()

        return count

    except Exception as e:
        print("❌ check failed:", e)
        try:
            page.close()
        except:
            pass
        return None


# ================= 主程序 =================
def main():
    print("🔥 TCF monitor V2 started")
    send_telegram("🚀 TCF Monitor V2 已启动（DOM变化检测版）")

    last_count = None
    last_notify_time = 0
    fail_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        while True:
            print("\n💓 alive ping")

            result = check_page(browser)

            # ================= 失败处理 =================
            if result is None:
                fail_count += 1
                print(f"⚠️ fetch failed ({fail_count})")

                if fail_count >= FAIL_LIMIT:
                    time.sleep(300)
                    fail_count = 0
                else:
                    time.sleep(CHECK_INTERVAL)
                continue

            fail_count = 0
            now = time.time()

            print("📊 current count:", result)

            # ================= 初始化状态 =================
            if last_count is None:
                last_count = result
                print("🧭 init baseline:", last_count)
                time.sleep(CHECK_INTERVAL)
                continue

            # ================= 变化检测（核心） =================
            changed = result != last_count

            # 变化方向判断
            improvement = result < last_count

            print("📈 changed:", changed, "| improvement:", improvement)

            should_notify = (
                changed and
                improvement and
                (now - last_notify_time > NOTIFY_COOLDOWN)
            )

            if should_notify:
                print("🎉 CHANGE detected!")

                # 二次确认（防误报）
                time.sleep(5)
                confirm = check_page(browser)

                if confirm is not None and confirm < last_count:
                    send_telegram(
                        f"🎉 TCF 可能出现新考位变化！\n\n"
                        f"之前: {last_count}\n现在: {confirm}\n\n{URL}"
                    )

                    last_count = confirm
                    last_notify_time = now
                else:
                    print("⚠️ false positive ignored")

            # ================= 更新状态 =================
            last_count = result

            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()