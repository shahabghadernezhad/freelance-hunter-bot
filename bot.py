import requests, os, time
from telegram import Bot
from bs4 import BeautifulSoup
import schedule

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "@shahabjumper")

def fetch_projects():
    keywords = ["cctv", "surveillance", "network infrastructure", "security camera"]
    bot = Bot(token=BOT_TOKEN)
    for kw in keywords:
        url = f"https://www.upwork.com/ab/feed/jobs/rss?q={kw.replace(' ', '+')}&sort=recency"
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(resp.text, "xml")
            items = soup.find_all("item")[:2]
            for item in items:
                msg = f"🎯 {item.title.text}\n\n{item.description.text[:150]}\n\n🔗 {item.link.text}"
                bot.send_message(chat_id=CHAT_ID, text=msg)
                time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
    print("Done!")

schedule.every().day.at("09:00").do(fetch_projects)
fetch_projects()

while True:
    schedule.run_pending()
    time.sleep(60)
