from config import admin_bot, customer_bot, db, stock
from telebot import types

db_images = db.section_images

@admin_bot.message_handler(func=lambda m: m.text == "🖼️ إدارة الصور")
def start_manage_images(msg):
    categories = stock.distinct("category")
    if not categories:
        return admin_bot.send_message(msg.chat.id, "⚠️ لا توجد أقسام في المخزن حالياً.")

    kb = types.InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        kb.add(types.InlineKeyboardButton(f"🖼️ ضبط صورة لـ {cat}", callback_data=f"setimg_{cat}"))
    
    admin_bot.send_message(msg.chat.id, "📸 **إدارة الصور:** اختر القسم المطلوب:", reply_markup=kb, parse_mode="Markdown")

@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("setimg_"))
def ask_for_photo(call):
    category_name = call.data.replace("setimg_", "")
    res = admin_bot.send_message(call.message.chat.id, f"🖼️ أرسل الآن الصورة لقسم: **{category_name}**")
    admin_bot.register_next_step_handler(res, save_category_image, category_name)

def save_category_image(msg, category_name):
    if not msg.photo:
        return admin_bot.send_message(msg.chat.id, "❌ خطأ: يرجى إرسال صورة فقط.")

    # 1. تحميل الصورة من سيرفرات تليجرام
    file_info = admin_bot.get_file(msg.photo[-1].file_id)
    downloaded_file = admin_bot.download_file(file_info.file_path)

    try:
        # 2. إرسال الصورة "مخفياً" عبر بوت العميل (إرسال ثم حذف فوراً)
        temp_msg = customer_bot.send_photo(msg.chat.id, downloaded_file)
        new_file_id = temp_msg.photo[-1].file_id
        customer_bot.delete_message(msg.chat.id, temp_msg.message_id) # الحذف الفوري

        # 3. حفظ الكود الجديد في قاعدة البيانات
        db_images.update_one(
            {"category": category_name},
            {"$set": {"category": category_name, "file_id": new_file_id}},
            upsert=True
        )
        
        admin_bot.send_message(msg.chat.id, f"✅ **تم تحديث صورة قسم {category_name} بنجاح.**")
    except Exception as e:
        print(f"🚨 خطأ في تحديث صورة القسم: {e}")
        admin_bot.send_message(
            msg.chat.id, 
            "❌ **فشل تحديث الصورة!**\n\n"
            "تأكد من أنك قمت بتشغيل بوت العملاء أولاً (أرسل له `/start`) لكي يتمكن البوت من إرسال الصورة وحفظ معرفها الفريد.", 
            parse_mode="Markdown"
        )