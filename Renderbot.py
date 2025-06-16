import os
import re
import threading
import time
import schedule
from flask import Flask
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==== إعدادات البوتات ====
BOT_TOKEN = "7990020438:AAHJ2-7l2JURUVgIV5tNliDiS53UsIbHbE4"
REPORT_BOT_TOKEN = "7990743429:AAGtuHxeR8q2vbxoL-Bnq_gcP9-6-plddMk"
REPORT_BOT_ID = 5777422098  # رقم معرف بوت التقارير
CONTROL_BOT_CHAT_ID = None  # لأنك تريد إرسال /start داخل نفس بوت التحكم نفسه

bot = TeleBot(BOT_TOKEN)
report_bot = TeleBot(REPORT_BOT_TOKEN)

user_steps = {}

# ==== دالة لوحة الأزرار مع زر استدعاء ملف ====

def get_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    # أزرارك السابقة (أضفها هنا حسب حاجتك)
    markup.add(InlineKeyboardButton("📂 استدعاء ملف", callback_data="call_file"))
    return markup

# ==== معالجة الأزرار ====

@bot.callback_query_handler(func=lambda call: call.data == "call_file")
def ask_for_filename(call):
    bot.send_message(call.message.chat.id, "✍️ أرسل اسم الملف الذي تريد استدعاؤه:")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, send_file_by_name)

def send_file_by_name(message):
    filename = message.text.strip()
    data_dir = "./"  # مجلد الملفات المرفوعة (يمكن تعديله)

    filepath = os.path.join(data_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            bot.send_document(message.chat.id, f)
    else:
        bot.send_message(message.chat.id, "❌ الملف غير موجود، تأكد من الاسم وأعد المحاولة.")

# ==== جزء تعديل الملفات بناءً على التوكن و ID المستخدم ====

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    uid = message.from_user.id

    # افترض وجود خطوات في user_steps - مثال مبسط
    if uid in user_steps:
        step = user_steps[uid].get('step')

        if step == 'tokens':
            if len(user_steps[uid]['tokens']) < user_steps[uid]['token_count']:
                user_steps[uid]['tokens'].append(message.text.strip())
                bot.send_message(message.chat.id, f"🔐 أرسل التوكن رقم {len(user_steps[uid]['tokens']) + 1}:")
            else:
                user_steps[uid]['step'] = 'user_id'
                bot.send_message(message.chat.id, "🆔 أرسل ID المستخدم الجديد:")

        elif step == 'user_id':
            try:
                new_id = int(message.text.strip())
                data = user_steps[uid]
                with open(data['filename'], 'r') as f:
                    content = f.read()

                pattern = r'["\']\d{10}:[\w-]{30,}["\']'
                # استبدال التوكنات
                for token in data['tokens']:
                    content = re.sub(pattern, f'"{token}"', content, count=1)
                # استبدال OWNER_ID
                content = re.sub(r"OWNER_ID\s*=\s*\d+", f"OWNER_ID = {new_id}", content)

                with open(data['filename'], 'w') as f:
                    f.write(content)

                bot.send_message(message.chat.id, "✅ تم تعديل الملف.")
                report_bot.send_message(REPORT_BOT_ID, f"✅ تم تعديل الملف: **{data['filename']}**", parse_mode='Markdown')
                user_steps.pop(uid)

            except Exception as e:
                bot.send_message(message.chat.id, f"❌ حصل خطأ أثناء التعديل:\n{e}")

# ==== إعادة تشغيل البوت تلقائياً عند الأخطاء ====

def run_bot():
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            try:
                report_bot.send_message(REPORT_BOT_ID, f"❌ خطأ في بوت التحكم:\n{e}")
            except:
                pass
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()

# ==== جدولة إرسال "/start" مرتين يومياً ====

def send_start_message():
    try:
        # إرسال نص /start إلى بوت التحكم نفسه (نفس الشات الذي يعمل فيه البوت)
        # إذا BOT لديه chat_id معروف يمكن تغييره
        # هنا نرسل إلى نفس البوت إلى أول مستخدم - أو يمكن التعديل حسب حاجتك
        # لأن بوت لا يمكن أن يرسل إلى نفسه مباشرة، أرسل إلى معرف دردشة معروف:
        if CONTROL_BOT_CHAT_ID:
            bot.send_message(CONTROL_BOT_CHAT_ID, "/start")
        else:
            # بديل: أرسل إلى المطور (REPORT_BOT_ID) أو غيره
            report_bot.send_message(REPORT_BOT_ID, "/start (تم إرسال أمر start)")

    except Exception as e:
        try:
            report_bot.send_message(REPORT_BOT_ID, f"❌ خطأ أثناء إرسال /start:\n{e}")
        except:
            pass

schedule.every().day.at("00:00").do(send_start_message)
schedule.every().day.at("12:00").do(send_start_message)

def schedule_runner():
    while True:
        schedule.run_pending()
        time.sleep(30)

threading.Thread(target=schedule_runner, daemon=True).start()

# ==== Flask لخدمة Render ====

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running..."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
