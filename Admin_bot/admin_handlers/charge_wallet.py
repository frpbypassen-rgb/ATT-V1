from config import admin_bot, customer_bot, users
from telebot import types

# --- 1. بدء عملية الشحن ---
@admin_bot.message_handler(func=lambda m: m.text == "💰 شحن رصيد")
def start_charge_wallet(msg):
    res = admin_bot.send_message(
        msg.chat.id, 
        "📞 **شحن محفظة عميل:**\nالرجاء إرسال **رقم هاتف** العميل للبحث عنه في النظام:", 
        parse_mode="Markdown"
    )
    admin_bot.register_next_step_handler(res, search_user_by_phone)

# --- 2. التحقق من العميل عبر الهاتف (نظام البحث الذكي) ---
def search_user_by_phone(msg):
    phone_input = msg.text.strip()
    
    # 1. تنظيف الرقم وتجهيز الاحتمالات
    clean_phone = phone_input.replace("+", "").replace(" ", "")
    # استخراج الرقم بدون الصفر في البداية (لو كان موجود)
    phone_no_zero = clean_phone[1:] if clean_phone.startswith("0") else clean_phone
    
    # 2. محرك البحث الشامل عن الهاتف (نص أو رقم رياضي)
    search_query = {
        "$or": [
            {"phone": phone_input},                       # الإدخال كما هو
            {"phone": phone_no_zero},                     # بدون صفر (940719000)
            {"phone": f"0{phone_no_zero}"},               # بصفر (0940719000)
            {"phone": f"+218{phone_no_zero}"},            # بالرمز الدولي الليبي (+)
            {"phone": f"218{phone_no_zero}"},             # بالرمز الدولي بدون (+)
            {"phone": int(phone_no_zero) if phone_no_zero.isdigit() else None},
            {"phone": int(clean_phone) if clean_phone.isdigit() else None}
        ]
    }
    
    # البحث في قاعدة البيانات
    user = users.find_one(search_query)
    
    if not user:
        return admin_bot.send_message(
            msg.chat.id, 
            f"⚠️ **لم يتم العثور على عميل.**\n"
            f"لا يوجد حساب مسجل بالرقم: `{phone_input}`\n"
            f"📌 *ملاحظة:* تأكد أن العميل قام بإضافة رقم هاتفه في حسابه داخل البوت.",
            parse_mode="Markdown"
        )
    
    # استخراج بيانات العميل بعد العثور عليه
    target_uid = user.get("_id")
    customer_name = user.get("name", "غير مسجل")
    current_balance = user.get("balance", 0.0)
    
    # جلب الهاتف الفعلي المسجل به في القاعدة لطباعته
    actual_phone = user.get("phone", phone_input)

    res = admin_bot.send_message(
        msg.chat.id, 
        f"👤 **العميل:** {customer_name}\n"
        f"📞 **الهاتف المسجل:** `{actual_phone}`\n"
        f"💳 **الرصيد الحالي:** `{current_balance:.2f}` د.ل\n\n"
        f"💵 **أرسل المبلغ المراد إضافته الآن:**\n"
        f"*(لخصم الرصيد، أرسل الرقم بالسالب، مثال: -50)*", 
        parse_mode="Markdown"
    )
    admin_bot.register_next_step_handler(res, process_payment, target_uid)

# --- 3. تنفيذ العملية وتحديث قاعدة البيانات (هذه هي الدالة التي كانت مفقودة) ---
def process_payment(msg, target_uid):
    try:
        try: uid = int(target_uid)
        except: uid = target_uid

        # تحويل النص إلى رقم
        amount = float(msg.text.strip())
        
        # تحديث الرصيد في الداتابيز
        users.update_one({"_id": uid}, {"$inc": {"balance": amount}})
        
        # جلب الرصيد الجديد
        updated_user = users.find_one({"_id": uid})
        new_balance = updated_user.get("balance", 0.0)

        # 1. إشعار الإدارة بالنجاح
        admin_bot.send_message(
            msg.chat.id, 
            f"✅ **تم تحديث المحفظة بنجاح!**\n"
            f"💰 الرصيد الجديد للعميل: `{new_balance:.2f}` د.ل", 
            parse_mode="Markdown"
        )
        
        # 2. إرسال إيصال إلكتروني للعميل
        try:
            if amount > 0:
                customer_text = (
                    f"💰 **إشعار إيداع:**\n"
                    f"تم شحن حسابك بمبلغ `{amount:.2f}` د.ل من قِبل الإدارة.\n"
                    f"💳 رصيدك الحالي: `{new_balance:.2f}` د.ل"
                )
            else:
                customer_text = (
                    f"💸 **إشعار خصم:**\n"
                    f"تم خصم `{abs(amount):.2f}` د.ل من حسابك بواسطة الإدارة.\n"
                    f"💳 رصيدك الحالي: `{new_balance:.2f}` د.ل"
                )
            customer_bot.send_message(target_uid, customer_text, parse_mode="Markdown")
        except Exception as e:
            print(f"🚨 لم يتم إرسال الإشعار للعميل: {e}")

    except ValueError:
        admin_bot.send_message(msg.chat.id, "❌ خطأ: الرجاء إدخال أرقام صحيحة فقط (مثال: 50 أو -20).")
        # --- دالة الربط السريع لملف إدارة المستخدمين ---
def ask_for_amount_by_id(msg, target_uid):
    try: uid = int(target_uid)
    except: uid = target_uid

    user = users.find_one({"_id": uid})
    if not user: return
    
    customer_name = user.get("name", "غير مسجل")
    res = admin_bot.send_message(
        msg.chat.id, 
        f"💵 **شحن رصيد للعميل:** {customer_name}\n"
        f"أرسل المبلغ الآن المراد إضافته:", 
        parse_mode="Markdown"
    )
    admin_bot.register_next_step_handler(res, process_payment, target_uid)