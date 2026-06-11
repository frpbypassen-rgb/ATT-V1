from config import admin_bot, users
from telebot import types

@admin_bot.message_handler(func=lambda m: m.text == "👥 مراجعة البيانات")
def review_customers_data(msg):
    chat_id = msg.chat.id
    
    # رسالة تنبيه للإدارة أثناء الجلب
    status_msg = admin_bot.send_message(chat_id, "⏳ جاري سحب بيانات العملاء من قاعدة البيانات...")
    
    # جلب جميع العملاء من قاعدة البيانات
    all_users = list(users.find({}))
    
    if not all_users:
        return admin_bot.edit_message_text("📭 لا يوجد عملاء مسجلين في النظام حتى الآن.", chat_id, status_msg.message_id)
        
    admin_bot.delete_message(chat_id, status_msg.message_id)
    
    # ترويسة الرسالة
    text = "👥 **كشف بيانات العملاء المسجلين:**\n━━━━━━━━━━━━━━━\n"
    
    for index, user in enumerate(all_users, 1):
        uid = user.get('_id', 'غير متوفر')
        name = user.get('name', 'غير مسجل')
        phone = user.get('phone', 'غير متوفر')
        
        # جلب القيمة/الرصيد وتنسيقها
        balance = user.get('balance', 0.0)
        try:
            balance = float(balance)
        except:
            balance = 0.0
            
        # تصميم قالب عرض بيانات العميل
        user_info = (
            f"👤 **الاسم:** {name}\n"
            f"📱 **الهاتف:** `{phone}`\n"
            f"🆔 **الآيدي:** `{uid}`\n"
            f"💰 **القيمة (الرصيد):** `{balance:.2f}` د.ل\n"
            f"━━━━━━━━━━━━━━━\n"
        )
        
        # 🌟 الحماية ضد تجاوز حد تليجرام (4096 حرف للرسالة)
        # إذا اقتربنا من الحد، نرسل الرسالة الحالية ونبدأ رسالة جديدة
        if len(text) + len(user_info) > 4000:
            admin_bot.send_message(chat_id, text, parse_mode="Markdown")
            text = "" # تفريغ المتغير للرسالة التالية
            
        text += user_info
        
    # إرسال ما تبقى من النصوص
    if text:
        admin_bot.send_message(chat_id, text, parse_mode="Markdown")
        
    # رسالة ختامية بالعدد الإجمالي
    admin_bot.send_message(chat_id, f"✅ **تم عرض بيانات {len(all_users)} عميل بنجاح.**", parse_mode="Markdown")