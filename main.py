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
        print("📲 Telegram response:", r.text)
    except Exception as e:
        print("❌ Telegram error:", e)


# ================= 检查页面 =================
def check_page(browser):
    for attempt in range(3):
        try:
            page = browser.new_page()

            # 🔥 随机UA（防封）
            page.set_extra_http_headers({
                "User-Agent": random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118 Safari/537.36"
                ])
            })

            page.goto(
                URL,
                timeout=60000,
                wait_until="domcontentloaded"
            )

            page.wait_for_timeout(3000)

            html = page.content()
            print("🔍 html length:", len(html))

            # ❗ 空页面判断（被封/失败）
            if len(html) < 100:
                raise Exception("Empty page")

            # 🔍 多位置检测
            texts = page.locator("text=No sessions currently available")
            count = texts.count()

            print("🔎 found 'No sessions' count:", count)

            page.close()

            # ✅ 判断逻辑
            if count < 2:
                return True
            else:
                return False

        except Exception as e:
            print(f"❌ attempt {attempt+1} failed:", e)

            try:
                page.close()
            except:
                pass

            time.sleep(3 + attempt * 3)

    # ❗ 所有尝试失败
    print("🚨 all retries failed")
    return None


# ================= 主程序 =================
def main():
    print("🔥 TCF monitor started (Worker mode)")

    send_telegram("🚀 TCF Monitor 已启动（Worker运行中）")

    last_state = None
    fail_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        while True:
            print("💓 alive ping")

            try:
                print("🔁 checking...")

                result = check_page(browser)

                # ❗ 请求失败
                if result is None:
                    fail_count += 1
                    print(f"⚠️ fetch failed ({fail_count})")

                    # 🚨 连续失败 → 冷却（防封）
                    if fail_count >= FAIL_LIMIT:
                        print("🧊 cooling down 5 minutes...")
                        time.sleep(300)
                        fail_count = 0
                    else:
                        time.sleep(CHECK_INTERVAL)

                    continue

                # ✅ 成功 → 重置失败计数
                fail_count = 0

                available = result
                print("📊 status:", "可能有考位" if available else "暂无")

                # 初始化
                if last_state is None:
                    last_state = available

                # 状态变化检测
                elif available and not last_state:
                    print("🎉 CHANGE detected!")

                    time.sleep(5)
                    confirm = check_page(browser)

                    if confirm:
                        send_telegram(
                            "🎉 TCF Canada 出现考位！（至少一个考点开放）\n\n" + URL
                        )
                    else:
                        print("⚠️ false positive ignored")

                last_state = available

            except Exception as e:
                print("❌ loop error:", e)

                # 🔥 浏览器恢复
                try:
                    browser.close()
                except:
                    pass

                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )

            # ✅ 固定60秒（稳定版）
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()