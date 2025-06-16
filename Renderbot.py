import os
import re
import subprocess
import threading
import time
from datetime import datetime
from telebot import TeleBot, types
from flask import Flask

# === إعدادات البوت ===
TOKEN = '7990020438:AAHJ2-7l2JURUVgIV5tNliDiS53UsIbHbE4'  # بوت التحكم
REPORT_BOT_TOKEN = '7990743429:AAGtuHxeR8q2vbxoL-Bnq_gcP9-6-plddMk'  # بوت التقارير
OWNER_ID = 5777422098  # ايدي المستخدم صاحب الصلاحيات
REPORT_CHAT_ID = 5777422098  # نفس الايدي لتلقي تقارير البوت
WELCOME_USER_ID = 5777422098  # المستخدم الذي سيرسل له رسالة ترحيب مرتين يومياً

bot = TeleBot(TOKEN)
report_bot = TeleBot(REPORT_BOT_TOKEN)

running_scripts = {}
user_steps = {}

# === دالة إنشاء الأزرار inline keyboard ===
def main_inline_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📤 رفع ملف", callback_data="upload_file"),
        types.InlineKeyboardButton("📥 إدخال كود سكريبت", callback_data="input_code"),
        types.InlineKeyboardButton("⚙️ تعديل التوكن والايدي", callback_data="edit_token"),
        types.InlineKeyboardButton("🗑️ حذف ملف", callback_data="delete_file"),
        types.InlineKeyboardButton("📂 عرض السكريبتات المشغلة", callback_data="list_scripts"),
        types.InlineKeyboardButton("🛑 إيقاف سكريبت", callback_data="stop_script"),
        types.InlineKeyboardButton("⚡️ تنفيذ أمر شيل", callback_data="shell_command"),
    )
    return kb

# === رسالة /start ===
@bot.message_handler(commands=['start'])
def start_handler(msg):
    if msg.from_user.id != OWNER_ID:
        return
    bot.send_message(msg.chat.id, "🤖 مرحبًا بك في بوت التحكم:", reply_markup=main_inline_keyboard())

# === التعامل مع الضغط على الأزرار inline ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية.")
        return
    
    data = call.data
    
    if data == "upload_file":
        bot.answer_callback_query(call.id, "📤 أرسل ملف .py الآن.")
        user_steps[call.from_user.id] = {'step': 'waiting_file'}

    elif data == "input_code":
        bot.answer_callback_query(call.id, "✍️ أرسل الكود كاملاً:")
        user_steps[call.from_user.id] = {'step': 'input_code'}

    elif data == "edit_token":
        bot.answer_callback_query(call.id, "⚙️ أرسل اسم الملف لتعديل التوكن والايدي:")
        user_steps[call.from_user.id] = {'step': 'edit_filename'}

    elif data == "delete_file":
        bot.answer_callback_query(call.id, "🗑️ أرسل اسم الملف للحذف:")
        user_steps[call.from_user.id] = {'step': 'delete_file'}

    elif data == "list_scripts":
        if running_scripts:
            reply = "📂 السكريبتات المشغلة:\n" + "\n".join(running_scripts.keys())
        else:
            reply = "🟢 لا توجد سكريبتات مشغلة حالياً."
        bot.send_message(call.message.chat.id, reply)
        bot.answer_callback_query(call.id)

    elif data == "stop_script":
        bot.answer_callback_query(call.id, "🛑 أرسل اسم السكريبت لإيقافه:")
        user_steps[call.from_user.id] = {'step': 'stop_script'}

    elif data == "shell_command":
        bot.answer_callback_query(call.id, "⚡️ أرسل أمر الشيل لتنفيذه:")
        user_steps[call.from_user.id] = {'step': 'shell_command'}

# === رفع ملف ===
@bot.message_handler(content_types=['document'])
def upload_script(message):
    if message.from_user.id != OWNER_ID:
        return
    step = user_steps.get(message.from_user.id, {}).get('step')
    if step == 'waiting_file':
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        name = message.document.file_name
        if not name.endswith('.py'):
            bot.send_message(message.chat.id, "❌ فقط ملفات .py مسموح بها.")
            return
        with open(name, 'wb') as f:
            f.write(downloaded_file)
        bot.send_message(message.chat.id, f"📥 تم حفظ الملف: {name}")
        report_bot.send_message(REPORT_CHAT_ID, f"📥 تم رفع ملف جديد: {name}")
        user_steps.pop(message.from_user.id, None)

# === التعامل مع النصوص بحسب الخطوات ===
@bot.message_handler(content_types=['text'])
def handle_all(message):
    if message.from_user.id != OWNER_ID:
        return
    
    uid = message.from_user.id
    step = user_steps.get(uid, {}).get('step')

    if not step:
        # إذا لم يكن في خطوة محددة، لا نفعل شيء
        return

    # خطوات إدخال كود نصي
    if step == 'input_code':
        filename = "uploaded_code.py"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(message.text)
        bot.send_message(message.chat.id, f"✅ تم حفظ الكود في {filename}")
        report_bot.send_message(REPORT_CHAT_ID, f"📝 تم رفع سكريبت نصي: {filename}")
        user_steps.pop(uid)

    # حذف ملف
    elif step == 'delete_file':
        fname = message.text.strip()
        if os.path.exists(fname):
            os.remove(fname)
            bot.send_message(message.chat.id, f"🗑️ تم حذف: {fname}")
            report_bot.send_message(REPORT_CHAT_ID, f"🗑️ تم حذف الملف: {fname}")
        else:
            bot.send_message(message.chat.id, "❌ الملف غير موجود.")
        user_steps.pop(uid)

    # تعديل التوكن والايدي: الخطوة 1 - اسم الملف
    elif step == 'edit_filename':
        fname = message.text.strip()
        if not os.path.isfile(fname):
            bot.send_message(message.chat.id, "❌ الملف غير موجود.")
            return
        user_steps[uid].update({'filename': fname, 'step': 'token_count'})
        bot.send_message(message.chat.id, "🔢 كم عدد التوكنات؟")

    # تعديل التوكن والايدي: الخطوة 2 - عدد التوكنات
    elif step == 'token_count':
        try:
            count = int(message.text.strip())
            user_steps[uid].update({'token_count': count, 'tokens': [], 'step': 'token_input'})
            bot.send_message(message.chat.id, "🔐 أرسل التوكن رقم 1:")
        except:
            bot.send_message(message.chat.id, "❗ أرسل رقم صحيح.")

    # تعديل التوكن والايدي: الخطوة 3 - إدخال التوكنات
    elif step == 'token_input':
        user_steps[uid]['tokens'].append(message.text.strip())
        if len(user_steps[uid]['tokens']) < user_steps[uid]['token_count']:
            bot.send_message(message.chat.id, f"🔐 أرسل التوكن رقم {len(user_steps[uid]['tokens']) + 1}:")
        else:
            user_steps[uid]['step'] = 'user_id'
            bot.send_message(message.chat.id, "🆔 أرسل ID المستخدم الجديد:")

    # تعديل التوكن والايدي: الخطوة 4 - إدخال اليوزر ايدي
    elif step == 'user_id':
        try:
            new_id = int(message.text.strip())
            data = user_steps[uid]
            with open(data['filename'], 'r', encoding='utf-8') as f:
                content = f.read()

            # استبدال كل التوكنات القديمة بالتي أُدخلت
            tokens = data['tokens'][:]
            def replace_token(m):
                return f'"{tokens.pop(0)}"'
            content = re.sub(r'["\']\d{9,10}:[\w-]{30,}["\']', replace_token, content)

            # تعديل OWNER_ID
            content = re.sub(r'OWNER_ID\s*=\s*\d+', f'OWNER_ID = {new_id}', content)

            with open(data['filename'], 'w', encoding='utf-8') as f:
                f.write(content)

            bot.send_message(message.chat.id, "✅ تم تعديل الملف.")
            report_bot.send_message(REPORT_CHAT_ID, f"✅ تم تعديل الملف: {data['filename']}")
            user_steps.pop(uid)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ حصل خطأ أثناء التعديل:\n{e}")

    # إيقاف سكريبت
    elif step == 'stop_script':
        name = message.text.strip()
        p = running_scripts.get(name)
        if p:
            p.terminate()
            bot.send_message(message.chat.id, f"🛑 تم إيقاف: {name}")
            report_bot.send_message(REPORT_CHAT_ID, f"🛑 تم إيقاف السكريبت: {name}")
            running_scripts.pop(name, None)
        else:
            bot.send_message(message.chat.id, "❌ لم يتم العثور على العملية.")
        user_steps.pop(uid)

    # تنفيذ أمر شيل
    elif step == 'shell_command':
        try:
            cmd = message.text.strip()
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=60)
            bot.send_message(message.chat.id, f"<code>{result.decode()}</code>", parse_mode="HTML")
            report_bot.send_message(REPORT_CHAT_ID, f"⚡️ تم تنفيذ أمر شيل:\n{cmd}")
        except subprocess.CalledProcessError as e:
            bot.send_message(message.chat.id, f"<code>{e.output.decode()}</code>", parse_mode="HTML")
        user_steps.pop(uid)

# === أوامر تشغيل السكربتات ===
@bot.message_handler(commands=['run'])
def run_script(message):
    if message.from_user.id != OWNER_ID:
        return
    name = message.text.replace('/run', '').strip()
    if not os.path.isfile(name):
        bot.send_message(message.chat.id, "❌ الملف غير موجود.")
        return
    if name in running_scripts:
        bot.send_message(message.chat.id, "⚠️ السكربت قيد التشغيل بالفعل.")
        return
    p = subprocess.Popen(['python3', name])
    running_scripts[name] = p
    bot.send_message(message.chat.id, f"🚀 تم تشغيل: {name}")
    report_bot.send_message(REPORT_CHAT_ID, f"🚀 تم تشغيل السكربت: {name}")

# === عرض السكربتات المشغلة ===
@bot.message_handler(commands=['scripts'])
def list_scripts(message):
    if message.from_user.id != OWNER_ID:
        return
    if running_scripts:
        reply = "📂 السكربتات المشغلة:\n" + '\n'.join(running_scripts.keys())
    else:
        reply = "🟢 لا توجد سكربتات مشغلة حاليًا."
    bot.send_message(message.chat.id, reply)

# === إيقاف سكربت بواسطة أمر ===
@bot.message_handler(commands=['stop'])
def stop_script_cmd(message):
    if message.from_user.id != OWNER_ID:
        return
    name = message.text.replace('/stop', '').strip()
    p = running_scripts.get(name)
    if p:
        p.terminate()
        bot.send_message(message.chat.id, f"🛑 تم إيقاف: {name}")
        report_bot.send_message(REPORT_CHAT_ID, f"🛑 تم إيقاف السكربت: {name}")
        running_scripts.pop(name, None)
    else:
        bot.send_message(message.chat.id, "❌ لم يتم العثور على العملية.")

# === تنفيذ أوامر شيل بواسطة أمر ===
@bot.message_handler(commands=['exec'])
def exec_shell(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        cmd = message.text.replace('/exec', '').strip()
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=60)
        bot.send_message(message.chat.id, f"<code>{result.decode()}</code>", parse_mode="HTML")
        report_bot.send_message(REPORT_CHAT_ID, f"⚡️ تم تنفيذ أمر شيل:\n{cmd}")
    except subprocess.CalledProcessError as e:
        bot.send_message(message.chat.id, f"<code>{e.output.decode()}</code>", parse_mode="HTML")

# === إرسال رسالة ترحيب مرتين يومياً ===
def welcome_job():
    last_sent_date = None
    while True:
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        if last_sent_date != today_str and (now.hour == 9 or now.hour == 21):
            try:
                bot.send_message(WELCOME_USER_ID, "🤖 مرحباً! هذه رسالة الترحيب اليومية من بوت التحكم.")
                last_sent_date = today_str
            except Exception as e:
                print(f"Error sending welcome message: {e}")
        time.sleep(60)

# === تشغيل بوت التيليجرام بشكل غير محظور ===
def run_bot():
    bot.infinity_polling()

# === تشغيل Flask لخدمة Render ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running..."

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=welcome_job, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
