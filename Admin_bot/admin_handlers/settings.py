from config import admin_bot, settings
from telebot import types

# --- 1. زر تغيير حساب الدعم الفني ---
@admin_bot.message_handler(func=lambda m: m.text == "⚙️ إعدادات الدعم" or m.text == "/support")
def manage_support_contact(msg):
    current_setting = settings.find_one({"_id": "support_contact"})
    # جلب اليوزر نيم الحالي
    current_user = current_setting.get("username", "لم يتم تحديده") if current_setting else "لم يتم تحديده"
    
    text = (
        "⚙️ **إعدادات الدعم الفني (تليجرام)**\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 **الحساب الحالي:** `@{current_user}`\n\n"
        "✍️ **للتغيير:** أرسل (المعرف/Username) الجديد الآن بدون علامة @\n"
        "*(مثال: ZoneTech_Support)*"
    )
    
    res = admin_bot.send_message(msg.chat.id, text, parse_mode="Markdown")
    admin_bot.register_next_step_handler(res, save_new_support)

def save_new_support(msg):
    new_user = msg.text.strip().replace("@", "") # تنظيف اليوزر من العلامة لو وجدت
    
    if new_user == "الغاء":
        return admin_bot.send_message(msg.chat.id, "✅ تم إلغاء العملية.")
        
    settings.update_one(
        {"_id": "support_contact"}, 
        {"$set": {"username": new_user}}, 
        upsert=True
    )
    
    admin_bot.send_message(msg.chat.id, f"✅ **تم الحفظ!**\nسيتم تحويل العملاء الآن إلى الحساب: `@{new_user}`", parse_mode="Markdown")