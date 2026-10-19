import requests, os, time, json, hashlib
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from bs4 import BeautifulSoup
import schedule
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "93113468")

# Track sent projects
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
    """Fetch from RemoteOK API"""
    try:
        resp = requests.get("https://remoteok.com/api", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json()
        projects = []
        for item in data[1:]:  # Skip first element
            if not item.get("position"):
                continue
            title = item.get("position", "")
            desc = item.get("description", "")[:200]
            link = item.get("url", "")
            tags = item.get("tags", [])
            if any(kw in title.lower() or kw in desc.lower() for kw in ["cctv", "surveillance", "network", "security", "camera"]):
                projects.append({"title": title, "desc": desc, "link": link, "source": "RemoteOK"})
        return projects
    except Exception as e:
        print(f"RemoteOK error: {e}")
        return []

def fetch_freelancer():
    """Fetch from Freelancer RSS"""
    try:
        url = "https://www.freelancer.com/rss.xml?q=cctv+network+security"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(resp.text, "xml")
        projects = []
        for item in soup.find_all("item")[:5]:
            title = item.title.text
            desc = item.description.text[:200]
            link = item.link.text
            projects.append({"title": title, "desc": desc, "link": link, "source": "Freelancer"})
        return projects
    except Exception as e:
        print(f"Freelancer error: {e}")
        return []

def fetch_projects():
    """Main fetch function"""
    sent = load_sent()
    new_projects = []

    # Fetch from all sources
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
            print(f"{source_name}: {len(projects)} found")
        except Exception as e:
            print(f"{source_name} error: {e}")

    # Send new projects
    if new_projects:
        bot = Bot(token=BOT_TOKEN)
        for proj in new_projects[:10]:  # Max 10 per run
            msg = f"""🎯 **{proj['title']}**

📋 {proj['desc']}

🔗 {proj['link']}

📌 منبع: {proj['source']}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
            try:
                bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
                time.sleep(1)
            except Exception as e:
                print(f"Send error: {e}")

        save_sent(sent)
        print(f"Sent {len(new_projects)} new projects")
    else:
        print("No new projects found")

# Telegram Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Freelance Hunter Bot**\n\n"
        "پروژه‌های فریلنسری CCTV/Network/Security رو پیدا میکنم.\n\n"
        "دستورات:\n"
        "/start - شروع\n"
        "/status - وضعیت\n"
        "/help - راهنما",
        parse_mode="Markdown"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sent = load_sent()
    await update.message.reply_text(
        f"📊 **وضعیت Bot**\n\n"
        f"پروژه‌های ارسال شده: {len(sent)}\n"
        f"زمان بعدی: 18:00\n"
        f"منابع: RemoteOK, Freelancer",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 **راهنما**\n\n"
        "Bot هر روز عصر (18:00) پروژه‌های جدید رو میفرسته.\n"
        "پروژه‌های تکراری رو نمیفرسته.\n"
        "منابع: RemoteOK, Freelancer.com"
    )

# Main
def main():
    # Setup Telegram bot with commands
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("help", help_command))

    # Schedule
    schedule.every().day.at("18:00").do(fetch_projects)

    # Immediate check
    fetch_projects()

    # Run bot
    print("Bot started! Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
