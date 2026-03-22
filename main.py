import time
import requests
from playwright.sync_api import sync_playwright

# ================= 配置 =================
URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

BOT_TOKEN = "8683283125:AAHTIr93G4VT2QVuCToBVHjVGcwIqxL-tHA"
CHAT_ID = 5068415693

CHECK_INTERVAL = 60  # 建议 30~60 秒


# ================= Telegram 推送 =================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        }, timeout=10)

        print("📲 Telegram:", r.text)

    except Exception as e:
        print("Telegram发送失败:", e)


# ================= 获取页面（真实浏览器） =================
def get_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, timeout=60000)
        page.wait_for_timeout(5000)  # 等JS加载

        html = page.content()
        browser.close()

        return html


# ================= 判断是否有考位 =================
def has_slots(html):
    keywords_no = [
        "No sessions currently available"
    ]

    keywords_yes = [
        "Book",
        "Register",
        "Available",
        "session"
    ]

    # 没有“无考位”关键词 + 出现一点“可能按钮词”
    if any(k in html for k in keywords_no):
        return False

    if any(k in html for k in keywords_yes):
        return True

    return False


# ================= 主循环 =================
def main():
    print("🚀 TCF监控启动（Telegram版）")

    last_state = None

    while True:
        try:
            html = get_page()
            available = has_slots(html)

            print("状态:", "有可能有考位" if available else "暂无", time.strftime("%H:%M:%S"))

            # 初始化
            if last_state is None:
                last_state = available

            # 从无 → 有（触发）
            elif available and not last_state:
                print("🎉 检测到考位变化！")

                send_telegram(
                    "🎉 TCF Canada 可能有新考位！\n\n"
                    f"{URL}"
                )

                last_state = available

            else:
                last_state = available

        except Exception as e:
            print("错误:", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()