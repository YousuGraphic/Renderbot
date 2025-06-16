import os, re, threading, time, schedule
from flask import Flask
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ——— منع التكرار: قفل التشغيل ———
LOCK_FILE = "run.lock"
if os.path.exists(LOCK_FILE):
    print("⛔️ نسخة سابقة تعمل، إيقاف التكرار.")
    exit()
with open(LOCK_FILE, "w") as f:
    f.write("locked")

import atexit
def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
atexit.register(remove_lock)

# ——— إعداد التوكنات ———
BOT_TOKEN         = "7990020438:AAHJ2-7l2JURUVgIV5tNliDiS53UsIbHbE4"
REPORT_BOT_TOKEN  = "7990743429:AAGtuHxeR8q2vbxoL-Bnq_gcP9-6-plddMk"
REPORT_BOT_ID     = 5777422098          # شات تقارير
CONTROL_CHAT_ID   = 5777422098          # الشات الذي سيرسل إليه البوت نص "/start"

bot         = TeleBot(BOT_TOKEN)
report_bot  = TeleBot(REPORT_BOT_TOKEN)

user_steps = {}          # تتبُّع خطوات تعديل الملفات

# ——— لوحة الأزرار الرئيسية ———
def main_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📂 استدعاء ملف", callback_data="call_file"))
    return kb

# ——— زر استدعاء ملف ———
@bot.callback_query_handler(func=lambda c: c.data == "call_file")
def ask_filename(c):
    bot.send_message(c.message.chat.id, "✍️ أرسل اسم الملف الذي تريد استدعاءه:")
    bot.register_next_step_handler_by_chat_id(c.message.chat.id, send_file)

def send_file(msg):
    name = msg.text.strip()
    if os.path.exists(name):
        with open(name, 'rb') as f:
            bot.send_document(msg.chat.id, f)
    else:
        bot.send_message(msg.chat.id, "❌ الملف غير موجود.")

# ——— استقبال أوّل /start ———
@bot.message_handler(commands=['start'])
def welcome(msg):
    bot.send_message(msg.chat.id,
                     "🤖 بوت التحكم جاهز — استخدم الأزرار بالأسفل.",
                     reply_markup=main_kb())

# ——— مثال مختصر لتعديل التوكنات و OWNER_ID ———
@bot.message_handler(func=lambda m: True)
def handle_steps(m):
    uid = m.from_user.id
    if uid not in user_steps:
        return

    step = user_steps[uid]['step']
    if step == 'tokens':
        user_steps[uid]['tokens'].append(m.text.strip())
        if len(user_steps[uid]['tokens']) < user_steps[uid]['token_count']:
            bot.send_message(uid, f"🔐 أرسل التوكن رقم {len(user_steps[uid]['tokens'])+1}:")
        else:
            user_steps[uid]['step'] = 'user_id'
            bot.send_message(uid, "🆔 أرسل ID المستخدم الجديد:")

    elif step == 'user_id':
        try:
            new_id = int(m.text.strip())
            data   = user_steps[uid]
            with open(data['filename'], 'r') as f:
                content = f.read()

            pattern = r'["\']\d{10}:[\w-]{30,}["\']'
            for t in data['tokens']:
                content = re.sub(pattern, f'"{t}"', content, count=1)

            content = re.sub(r"OWNER_ID\s*=\s*\d+", f"OWNER_ID = {new_id}", content)

            with open(data['filename'], 'w') as f:
                f.write(content)

            bot.send_message(uid, "✅ تم تعديل الملف.")
            report_bot.send_message(REPORT_BOT_ID,
                                    f"✅ تم تعديل الملف: **{data['filename']}**",
                                    parse_mode='Markdown')
        except Exception as e:
            bot.send_message(uid, f"❌ خطأ أثناء التعديل:\n{e}")
        finally:
            user_steps.pop(uid, None)

# ——— تشغيل البوت مع إعادة المحاولة ———
def run_bot():
    while True:
        try:
            bot.infinity_polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            try:
                report_bot.send_message(REPORT_BOT_ID, f"❌ خطأ في بوت التحكم:\n{e}")
            except:
                pass
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()

# ——— جدولة إرسال نص "/start" مرتين يومياً ———
def send_start():
    try:
        bot.send_message(CONTROL_CHAT_ID, "/start")
    except Exception as err:
        report_bot.send_message(REPORT_BOT_ID, f"⚠️ لم أستطع إرسال /start:\n{err}")

schedule.every().day.at("00:00").do(send_start)
schedule.every().day.at("12:00").do(send_start)

def schedule_loop():
    while True:
        schedule.run_pending()
        time.sleep(30)

threading.Thread(target=schedule_loop, daemon=True).start()

# ——— Flask للإبقاء على الخدمة حيّة في Render ———
app = Flask(__name__)

@app.route('/')
def root():
    return "Bot is running..."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
