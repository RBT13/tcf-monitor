import time
import random
import requests
import json
from playwright.sync_api import sync_playwright

# ================= 配置 =================
URL = "https://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

BOT_TOKEN = "8683283125:AAEmfiRTMxN35jTAsQfqF_HIQ6YymYoHyXI"
CHAT_ID = "5068415693"   # ⚠️ 一定要是字符串

CHECK_INTERVAL = 60  # 每60秒检查一次


URLS = {
    "367": "https://www.alliance-francaise.ca/api/groupcourses?enddate=gte&limit=150&openspaces=1&orderby=course.startDate&othercategory=367&status=0",
    "368": "https://www.alliance-francaise.ca/api/groupcourses?enddate=gte&limit=150&openspaces=1&orderby=course.startDate&othercategory=368&status=0"
}

# ================= Telegram =================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        }, timeout=10)
        print("📲 Telegram sent")
    except Exception as e:
        print("❌ Telegram error:", e)


# ================= 获取API数据 =================
def fetch_courses(url):
    r = requests.get(url, timeout=15)
    data = r.json()
    return data.get("courses", [])


# ================= 判断是否有考位 =================
def has_slots(courses):
    """
    判断逻辑：
    - courses 不为空
    - 或 openSpaces > 0
    """
    for c in courses:
        try:
            if c.get("openSpaces", 0) > 0:
                return True
        except:
            continue
    return False


# ================= 主逻辑 =================
def check_all():

    results = {}
    total_slots = 0

    for key, url in URLS.items():
        try:
            courses = fetch_courses(url)

            slots = has_slots(courses)
            count = len(courses)

            results[key] = {
                "slots": slots,
                "count": count
            }

            if slots:
                total_slots += 1

            print(f"📊 category {key}: count={count}, slots={slots}")

        except Exception as e:
            print(f"❌ category {key} error:", e)
            results[key] = {"slots": False, "count": 0}

    return results, total_slots


# ================= 主循环 =================
def main():

    print("🔥 TCF API monitor started (FINAL PROD VERSION)")

    send_telegram("🚀 TCF Monitor 启动（API稳定生产版）")

    last_state = None

    while True:
        try:
            results, total_slots = check_all()

            # 当前状态hash（用于防重复通知）
            state = json.dumps(results, sort_keys=True)

            print("📦 total categories with slots:", total_slots)

            # ================= 初始化 =================
            if last_state is None:
                last_state = state
                time.sleep(CHECK_INTERVAL)
                continue

            # ================= 检测变化 =================
            if state != last_state and total_slots > 0:

                print("🎉 SLOT DETECTED!")

                msg = "🎉 TCF Canada 发现考位！\n\n"

                for k, v in results.items():
                    if v["slots"]:
                        msg += f"✔ Category {k}: 有空位 ({v['count']} courses)\n"
                    else:
                        msg += f"✖ Category {k}: 无\n"

                msg += "\nhttps://www.alliance-francaise.ca/en/exams/tests/informations-about-tcf-canada/tcf-canada"

                send_telegram(msg)

                last_state = state

            else:
                print("⏳ no change")

                last_state = state

        except Exception as e:
            print("❌ main loop error:", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()