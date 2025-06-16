import os
import re
import subprocess
from telebot import TeleBot, types

# توكن البوت الرئيسي
TOKEN = '7990020438:AAGHUMX78JtCimQNiY4-NvK8jJg7cXz8'
OWNER_ID = 5777422098

# بوت التقارير
REPORT_BOT_TOKEN = '7990743429:AAH6tF8wnu80ZJ-Jd_j3Z-Jni0x2zjFJss8'
REPORT_BOT_ID = 5777422098

bot = TeleBot(TOKEN)
report_bot = TeleBot(REPORT_BOT_TOKEN)

# العمليات الجارية
running_scripts = {}
user_steps = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.from_user.id != OWNER_ID:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📤 رفع ملف", "📥 إدخال كود سكريبت")
    markup.add("⚙️ تعديل التوكن والايدي", "🗑️ حذف ملف")
    bot.send_message(message.chat.id, "🤖 مرحبًا بك في بوت التحكم:", reply_markup=markup)

@bot.message_handler(commands=['run'])
def run_script(message):
    if message.from_user.id != OWNER_ID:
        return
    name = message.text.replace('/run', '').strip()
    if not os.path.isfile(name):
        bot.send_message(message.chat.id, "❌ الملف غير موجود.")
        return
    p = subprocess.Popen(['python3', name])
    running_scripts[name] = p
    bot.send_message(message.chat.id, f"🚀 تم تشغيل: {name}")
    report_bot.send_message(REPORT_BOT_ID, f"🚀 تم تشغيل السكربت: {name}")

@bot.message_handler(commands=['stop'])
def stop_script(message):
    if message.from_user.id != OWNER_ID:
        return
    name = message.text.replace('/stop', '').strip()
    p = running_scripts.get(name)
    if p:
        p.terminate()
        bot.send_message(message.chat.id, f"🛑 تم إيقاف: {name}")
        report_bot.send_message(REPORT_BOT_ID, f"🛑 تم إيقاف السكربت: {name}")
        del running_scripts[name]
    else:
        bot.send_message(message.chat.id, "❌ لم يتم العثور على العملية.")

@bot.message_handler(commands=['scripts'])
def list_scripts(message):
    if message.from_user.id != OWNER_ID:
        return
    if running_scripts:
        reply = "📂 السكربتات المشغلة:\n" + '\n'.join(running_scripts.keys())
    else:
        reply = "🟢 لا توجد سكربتات مشغلة حاليًا."
    bot.send_message(message.chat.id, reply)

@bot.message_handler(commands=['exec'])
def exec_shell(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        cmd = message.text.replace('/exec', '').strip()
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=60)
        bot.send_message(message.chat.id, f"<code>{result.decode()}</code>", parse_mode="HTML")
    except subprocess.CalledProcessError as e:
        bot.send_message(message.chat.id, f"<code>{e.output.decode()}</code>", parse_mode="HTML")

@bot.message_handler(content_types=['document'])
def upload_script(message):
    if message.from_user.id != OWNER_ID:
        return
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    name = message.document.file_name
    with open(name, 'wb') as f:
        f.write(downloaded_file)
    bot.send_message(message.chat.id, f"📥 تم حفظ الملف: {name}")
    report_bot.send_message(REPORT_BOT_ID, f"📥 تم رفع ملف جديد: {name}")

@bot.message_handler(func=lambda m: m.text == "📥 إدخال كود سكريبت")
def insert_code(message):
    bot.send_message(message.chat.id, "✍️ أرسل الكود كاملاً:")
    user_steps[message.from_user.id] = {'step': 'code'}

@bot.message_handler(func=lambda m: m.text == "📤 رفع ملف")
def request_file(message):
    bot.send_message(message.chat.id, "📄 أرسل الآن ملف .py ليتم رفعه.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف ملف")
def delete_request(message):
    bot.send_message(message.chat.id, "🗑️ أرسل اسم الملف المراد حذفه:")
    user_steps[message.from_user.id] = {'step': 'delete'}

@bot.message_handler(func=lambda m: m.text == "⚙️ تعديل التوكن والايدي")
def ask_filename(message):
    bot.send_message(message.chat.id, "📂 أرسل اسم الملف (مثال: bot.py):")
    user_steps[message.from_user.id] = {'step': 'filename'}

@bot.message_handler(content_types=['text'])
def handle_all(message):
    if message.from_user.id != OWNER_ID:
        return

    uid = message.from_user.id
    if uid in user_steps:
        step = user_steps[uid]['step']

        if step == 'code':
            filename = "uploaded_code.py"
            with open(filename, 'w') as f:
                f.write(message.text)
            bot.send_message(message.chat.id, f"✅ تم حفظ الكود في {filename}")
            report_bot.send_message(REPORT_BOT_ID, f"📝 تم رفع سكربت نصي: {filename}")
            user_steps.pop(uid)

        elif step == 'delete':
            fname = message.text.strip()
            if os.path.exists(fname):
                os.remove(fname)
                bot.send_message(message.chat.id, f"🗑️ تم حذف: {fname}")
                report_bot.send_message(REPORT_BOT_ID, f"🗑️ تم حذف الملف: {fname}")
            else:
                bot.send_message(message.chat.id, "❌ الملف غير موجود.")
            user_steps.pop(uid)

        elif step == 'filename':
            fname = message.text.strip()
            if not os.path.isfile(fname):
                bot.send_message(message.chat.id, "❌ الملف غير موجود.")
                return
            user_steps[uid].update({'filename': fname, 'step': 'token_count'})
            bot.send_message(message.chat.id, "🔢 كم عدد التوكنات؟")

        elif step == 'token_count':
            try:
                count = int(message.text.strip())
                user_steps[uid].update({'token_count': count, 'tokens': [], 'step': 'token_input'})
                bot.send_message(message.chat.id, "🔐 أرسل التوكن رقم 1:")
            except:
                bot.send_message(message.chat.id, "❗ أرسل رقم صحيح.")

        elif step == 'token_input':
            user_steps[uid]['tokens'].append(message.text.strip())
            if len(user_steps[uid]['tokens']) < user_steps[uid]['token_count']:
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
                content = re.sub(pattern, lambda m: f'"{data["tokens"].pop(0)}"', content)
                content = re.sub(r"OWNER_ID\s*=\s*\d+", f"OWNER_ID = {new_id}", content)
                with open(data['filename'], 'w') as f:
                    f.write(content)
                bot.send_message(message.chat.id, "✅ تم تعديل الملف.")
                report_bot.send_message(REPORT_BOT_ID, f"✅ تم تعديل الملف: {data['filename']}")
                user_steps.pop(uid)
            except:
                bot.send_message(message.chat.id, "❌ حصل خطأ أثناء التعديل.")

bot.infinity_polling()
