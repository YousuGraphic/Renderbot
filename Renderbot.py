import os
import re
import subprocess
import threading
import time
from telebot import TeleBot, types

# إعدادات البوت
TOKEN = '7990020438:AAHJ2-7l2JURUVgIV5tNliDiS53UsIbHbE4'  # توكن بوت التحكم
REPORT_BOT_TOKEN = '7990743429:AAGtuHxeR8q2vbxoL-Bnq_gcP9-6-plddMk'  # توكن بوت التقارير
OWNER_ID = 5777422098  # ايدي مالك البوت (الصلاحيات)
REPORT_CHAT_ID = 5777422098  # نفس ايدي مالك البوت لتلقي التقارير

bot = TeleBot(TOKEN)
report_bot = TeleBot(REPORT_BOT_TOKEN)

running_scripts = {}  # يحتفظ بالسكريبتات المشغلة {اسم_السكريبت: subprocess.Popen}
user_steps = {}       # حالة المستخدم أثناء تفاعل الخطوات

# === دالة إنشاء أزرار inline keyboard ===
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
        types.InlineKeyboardButton("▶️ تشغيل سكريبت", callback_data="run_script")
    )
    return kb

# === دالة إنشاء reply keyboard ===
def main_reply_keyboard():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("📤 رفع ملف"),
        types.KeyboardButton("📥 إدخال كود سكريبت"),
        types.KeyboardButton("⚙️ تعديل التوكن والايدي"),
        types.KeyboardButton("🗑️ حذف ملف"),
        types.KeyboardButton("📂 عرض السكريبتات المشغلة"),
        types.KeyboardButton("🛑 إيقاف سكريبت"),
        types.KeyboardButton("⚡️ تنفيذ أمر شيل"),
        types.KeyboardButton("▶️ تشغيل سكريبت")
    )
    return kb

# === رسالة /start ===
@bot.message_handler(commands=['start'])
def start_handler(msg):
    if msg.from_user.id != OWNER_ID:
        return
    bot.send_message(msg.chat.id, "🤖 مرحبًا بك في بوت التحكم:", reply_markup=main_inline_keyboard())

# === التعامل مع أزرار inline ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ لا تملك صلاحية.")
        return

    data = call.data
    uid = call.from_user.id

    if data == "upload_file":
        bot.answer_callback_query(call.id, "📤 أرسل ملف .py الآن.")
        user_steps[uid] = {'step': 'waiting_file'}

    elif data == "input_code":
        bot.answer_callback_query(call.id, "✍️ أرسل الكود كاملاً:")
        user_steps[uid] = {'step': 'input_code'}

    elif data == "edit_token":
        bot.answer_callback_query(call.id, "⚙️ أرسل اسم الملف لتعديل التوكن والايدي:")
        user_steps[uid] = {'step': 'edit_filename'}

    elif data == "delete_file":
        bot.answer_callback_query(call.id, "🗑️ أرسل اسم الملف للحذف:")
        user_steps[uid] = {'step': 'delete_file'}

    elif data == "list_scripts":
        if running_scripts:
            reply = "📂 السكريبتات المشغلة:\n" + "\n".join(running_scripts.keys())
        else:
            reply = "🟢 لا توجد سكريبتات مشغلة حالياً."
        bot.send_message(call.message.chat.id, reply)
        bot.answer_callback_query(call.id)

    elif data == "stop_script":
        bot.answer_callback_query(call.id, "🛑 أرسل اسم السكريبت لإيقافه:")
        user_steps[uid] = {'step': 'stop_script'}

    elif data == "shell_command":
        bot.answer_callback_query(call.id, "⚡️ أرسل أمر الشيل لتنفيذه:")
        user_steps[uid] = {'step': 'shell_command'}

    elif data == "run_script":
        bot.answer_callback_query(call.id, "▶️ أرسل اسم السكريبت لتشغيله:")
        user_steps[uid] = {'step': 'run_script'}

# === التعامل مع رفع ملفات ===
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
        bot.send_message(message.chat.id, f"📥 تم حفظ الملف: {name}", reply_markup=main_reply_keyboard())
        report_bot.send_message(REPORT_CHAT_ID, f"📥 تم رفع ملف جديد: {name}")
        user_steps.pop(message.from_user.id, None)

# === التعامل مع النصوص: reply keyboard + خطوات الإدخال ===
@bot.message_handler(content_types=['text'])
def handle_all(message):
    if message.from_user.id != OWNER_ID:
        return
    
    text = message.text.strip()
    uid = message.from_user.id
    step = user_steps.get(uid, {}).get('step')

    # دعم أزرار reply keyboard كأوامر
    if text == "📤 رفع ملف":
        bot.send_message(message.chat.id, "📤 أرسل ملف .py الآن.", reply_markup=main_reply_keyboard())
        user_steps[uid] = {'step': 'waiting_file'}
        return
    elif text == "📥 إدخال كود سكريبت":
        bot.send_message(message.chat.id, "✍️ أرسل الكود كاملاً:", reply_markup=main_reply_keyboard())
        user_steps[uid] = {'step': 'input_code'}
        return
    elif text == "⚙️ تعديل التوكن والايدي":
        bot.send_message(message.chat.id, "⚙️ أرسل اسم الملف لتعديل التوكن والايدي:", reply_markup=main_reply_keyboard())
        user_steps[uid] = {'step': 'edit_filename'}
        return
    elif text == "🗑️ حذف ملف":
        bot.send_message(message.chat.id, "🗑️ أرسل اسم الملف للحذف:", reply_markup=main_reply_keyboard())
        user_steps[uid] = {'step': 'delete_file'}
        return
    elif text == "📂 عرض السكريبتات المشغلة":
        if running_scripts:
            reply = "📂 السكريبتات المشغلة:\n" + "\n".join(running_scripts.keys())
        else:
            reply = "🟢 لا توجد سكريبتات مشغلة حالياً."
        bot.send_message(message.chat.id, reply, reply_markup=main_reply_keyboard())
        return
    elif text == "🛑 إيقاف سكريبت":
        bot.send_message(message.chat.id, "🛑 أرسل اسم السكريبت لإيقافه:", reply_markup=main_reply_keyboard())
        user_steps[uid] = {'step': 'stop_script'}
        return
    elif text == "⚡️ تنفيذ أمر شيل":
        bot.send_message(message.chat.id, "⚡️ أرسل أمر الشيل لتنفيذه:", reply_markup=main_reply_keyboard())
        user_steps[uid] = {'step': 'shell_command'}
        return
    elif text == "▶️ تشغيل سكريبت":
        bot.send_message(message.chat.id, "▶️ أرسل اسم السكريبت لتشغيله:", reply_markup=main_reply_keyboard())
        user_steps[uid] = {'step': 'run_script'}
        return

    if not step:
        bot.send_message(message.chat.id, "اختر من الأزرار أدناه:", reply_markup=main_reply_keyboard())
        return

    # --- خطوات التعامل مع كل حالة ---

    if step == 'input_code':
        filename = "uploaded_code.py"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(message.text)
        bot.send_message(message.chat.id, f"✅ تم حفظ الكود في {filename}", reply_markup=main_reply_keyboard())
        report_bot.send_message(REPORT_CHAT_ID, f"📝 تم رفع سكريبت نصي: {filename}")
        user_steps.pop(uid)

    elif step == 'delete_file':
        fname = message.text.strip()
        if os.path.exists(fname):
            os.remove(fname)
            bot.send_message(message.chat.id, f"🗑️ تم حذف: {fname}", reply_markup=main_reply_keyboard())
            report_bot.send_message(REPORT_CHAT_ID, f"🗑️ تم حذف الملف: {fname}")
        else:
            bot.send_message(message.chat.id, "❌ الملف غير موجود.", reply_markup=main_reply_keyboard())
        user_steps.pop(uid)

    elif step == 'edit_filename':
        fname = message.text.strip()
        if not os.path.isfile(fname):
            bot.send_message(message.chat.id, "❌ الملف غير موجود.", reply_markup=main_reply_keyboard())
            return
        user_steps[uid].update({'filename': fname, 'step': 'token_count'})
        bot.send_message(message.chat.id, "🔢 كم عدد التوكنات؟", reply_markup=main_reply_keyboard())

    elif step == 'token_count':
        try:
            count = int(message.text.strip())
            user_steps[uid].update({'token_count': count, 'tokens': [], 'step': 'token_input'})
            bot.send_message(message.chat.id, "🔐 أرسل التوكن رقم 1:", reply_markup=main_reply_keyboard())
        except:
            bot.send_message(message.chat.id, "❗ أرسل رقم صحيح.", reply_markup=main_reply_keyboard())

    elif step == 'token_input':
        user_steps[uid]['tokens'].append(message.text.strip())
        if len(user_steps[uid]['tokens']) < user_steps[uid]['token_count']:
            bot.send_message(message.chat.id, f"🔐 أرسل التوكن رقم {len(user_steps[uid]['tokens']) + 1}:", reply_markup=main_reply_keyboard())
        else:
            user_steps[uid]['step'] = 'user_id'
            bot.send_message(message.chat.id, "🆔 أرسل ID المستخدم الجديد:", reply_markup=main_reply_keyboard())

    elif step == 'user_id':
        try:
            new_id = int(message.text.strip())
            data = user_steps[uid]
            with open(data['filename'], 'r', encoding='utf-8') as f:
                content = f.read()

            tokens = data['tokens'][:]
            def replace_token(m):
                return f'"{tokens.pop(0)}"'
            content = re.sub(r'["\']\d{9,10}:[\w-]{30,}["\']', replace_token, content)

            content = re.sub(r'OWNER_ID\s*=\s*\d+', f'OWNER_ID = {new_id}', content)

            with open(data['filename'], 'w', encoding='utf-8') as f:
                f.write(content)

            bot.send_message(message.chat.id, "✅ تم تعديل الملف.", reply_markup=main_reply_keyboard())
            report_bot.send_message(REPORT_CHAT_ID, f"✅ تم تعديل الملف: {data['filename']}")
            user_steps.pop(uid)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ أثناء التعديل:\n{e}", reply_markup=main_reply_keyboard())

    elif step == 'stop_script':
        name = message.text.strip()
        p = running_scripts.get(name)
        if p:
            p.terminate()
            bot.send_message(message.chat.id, f"🛑 تم إيقاف: {name}", reply_markup=main_reply_keyboard())
            report_bot.send_message(REPORT_CHAT_ID, f"🛑 تم إيقاف السكريبت: {name}")
            running_scripts.pop(name, None)
        else:
            bot.send_message(message.chat.id, "❌ لم يتم العثور على العملية.", reply_markup=main_reply_keyboard())
        user_steps.pop(uid)

    elif step == 'shell_command':
        try:
            cmd = message.text.strip()
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=60)
            bot.send_message(message.chat.id, f"<code>{result.decode()}</code>", parse_mode="HTML", reply_markup=main_reply_keyboard())
            report_bot.send_message(REPORT_CHAT_ID, f"⚡️ تم تنفيذ أمر شيل:\n{cmd}\n\nالنتيجة:\n<code>{result.decode()}</code>", parse_mode="HTML")
        except subprocess.CalledProcessError as e:
            bot.send_message(message.chat.id, f"<code>{e.output.decode()}</code>", parse_mode="HTML", reply_markup=main_reply_keyboard())
        user_steps.pop(uid)

    elif step == 'run_script':
        name = message.text.strip()
        if not os.path.isfile(name):
            bot.send_message(message.chat.id, "❌ الملف غير موجود.", reply_markup=main_reply_keyboard())
            user_steps.pop(uid)
            return
        if name in running_scripts:
            bot.send_message(message.chat.id, "⚠️ السكريبت قيد التشغيل بالفعل.", reply_markup=main_reply_keyboard())
            user_steps.pop(uid)
            return

        try:
            p = subprocess.Popen(
                ['python3', name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            running_scripts[name] = p
            bot.send_message(message.chat.id, f"🚀 تم تشغيل: {name}", reply_markup=main_reply_keyboard())

            output_lines = []
            def read_output():
                for line in p.stdout:
                    output_lines.append(line)
            thread = threading.Thread(target=read_output)
            thread.start()

            time.sleep(3)
            partial_output = ''.join(output_lines[-50:])
            report_text = f"🚀 تم تشغيل السكريبت:\n\n<code>{partial_output}</code>\n\n<b>اسم السكريبت:</b> {name}"
            report_bot.send_message(REPORT_CHAT_ID, report_text, parse_mode="HTML")

            user_steps.pop(uid)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ أثناء تشغيل السكريبت:\n{e}", reply_markup=main_reply_keyboard())
            user_steps.pop(uid)

# === تشغيل البوت ===
bot.infinity_polling()
