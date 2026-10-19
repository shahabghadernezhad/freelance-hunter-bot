import requests, os, time, json, hashlib
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from bs4 import BeautifulSoup
import schedule
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "93113468")

SENT_FILE = "/tmp/sent_projects.json"
def load_sent():
    try:
        with open(SENT_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_sent(sent):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent), f)

def get_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

def fetch_remoteok():
    try:
        resp = requests.get("https://remoteok.com/api", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json()
        projects = []
        for item in data[1:]:
            if not item.get("position"):
                continue
            title = item.get("position", "")
            desc = item.get("description", "")[:200]
            link = item.get("url", "")
            if any(kw in title.lower() or kw in desc.lower() for kw in ["cctv", "surveillance", "network", "security", "camera", "ip camera"]):
                projects.append({"title": title, "desc": desc, "link": link, "source": "RemoteOK"})
        return projects
    except Exception as e:
        print(f"RemoteOK error: {e}")
        return []

def fetch_freelancer():
    try:
        url = "https://www.freelancer.com/rss.xml?q=cctv+network+security"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(resp.text, "xml")
        projects = []
        for item in soup.find_all("item")[:10]:
            title = item.title.text
            desc = item.description.text[:200]
            link = item.link.text
            projects.append({"title": title, "desc": desc, "link": link, "source": "Freelancer"})
        return projects
    except Exception as e:
        print(f"Freelancer error: {e}")
        return []

def fetch_projects():
    sent = load_sent()
    new_projects = []

    sources = [
        ("RemoteOK", fetch_remoteok),
        ("Freelancer", fetch_freelancer),
    ]

    for source_name, fetch_func in sources:
        try:
            projects = fetch_func()
            for proj in projects:
                proj_hash = get_hash(proj["title"] + proj["link"])
                if proj_hash not in sent:
                    sent.add(proj_hash)
                    new_projects.append(proj)
            print(f"{source_name}: {len(projects)} found, {len([p for p in projects if get_hash(p['title']+p['link']) not in sent])} new")
        except Exception as e:
            print(f"{source_name} error: {e}")

    if new_projects:
        bot = Bot(token=BOT_TOKEN)
        for proj in new_projects[:15]:
            msg = f"""🎯 **{proj['title']}**

📋 {proj['desc']}

🔗 {proj['link']}

📌 منبع: {proj['source']}
⏰ {datetime.now().strftime('%H:%M')}"""
            try:
                bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
                time.sleep(1)
            except Exception as e:
                print(f"Send error: {e}")

        save_sent(sent)
        print(f"✅ Sent {len(new_projects)} new projects")
    else:
        print("⏭ No new projects")

# Telegram Commands
async def start_command(update, context):
    await update.message.reply_text(
        "🤖 **Freelance Hunter Pro**\n\n"
        "پروژه‌های فریلنسری رو real-time پیدا میکنم!\n\n"
        "هر ۱۵ دقیقه check میکنم.\n"
        "پروژه جدید = فوری ارسال.\n\n"
        "دستورات:\n"
        "/start - شروع\n"
        "/status - وضعیت\n"
        "/check - check فوری",
        parse_mode="Markdown"
    )

async def status_command(update, context):
    sent = load_sent()
    await update.message.reply_text(
        f"📊 **وضعیت**\n\n"
        f"پروژه‌های ارسال شده: {len(sent)}\n"
        f"interval: ۱۵ دقیقه\n"
        f"منابع: RemoteOK, Freelancer",
        parse_mode="Markdown"
    )

async def check_command(update, context):
    await update.message.reply_text("🔍 در حال check...")
    fetch_projects()
    await update.message.reply_text("✅ Check انجام شد!")

# Main
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("check", check_command))

    # Every 15 minutes
    schedule.every(15).minutes.do(fetch_projects)

    # Immediate check
    fetch_projects()

    print("🚀 Bot started! Real-time mode.")
    app.run_polling()

if __name__ == "__main__":
    main()
