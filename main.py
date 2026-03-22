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

            page.goto(
                URL,
                timeout=60000,
                wait_until="domcontentloaded"
            )

            page.wait_for_timeout(3000)

            html = page.content()
            print("🔍 html length:", len(html))

            # ❗ 防空页面
            if len(html) < 100:
                raise Exception("Empty page")

            # 🔥 多位置检测
            texts = page.locator("text=No sessions currently available")
            count = texts.count()

            print("🔎 found 'No sessions' count:", count)

            page.close()

            # ✅ 逻辑：只要少于2个 → 有考位
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

            # 🔥 递增退避
            time.sleep(3 + attempt * 3)

    # ❗ 关键：失败返回 None（不误判）
    print("🚨 all retries failed")
    return None


# ================= 主程序 =================
def main():
    print("🔥 TCF monitor started (Worker mode)")

    # ✅ 启动通知
    send_telegram("🚀 TCF Monitor 已启动（Worker运行中）")

    last_state = None

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

                # ❗ 请求失败 → 跳过
                if result is None:
                    print("⚠️ skip this round (fetch failed)")
                    time.sleep(CHECK_INTERVAL)
                    continue

                available = result

                print("📊 status:", "可能有考位" if available else "暂无")

                # 初始化
                if last_state is None:
                    last_state = available

                # 状态变化检测
                elif available and not last_state:
                    print("🎉 CHANGE detected!")

                    # 二次确认
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

                # 🔥 浏览器级恢复
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