from config import customer_bot, admin_bot, users, transactions, complaints_db, ADMIN_ID ,stock, admins # تم إضافة admins هنا
from telebot import types
import datetime
from bson.objectid import ObjectId

# --- 1. القائمة الرئيسية للشكاوى ---
@customer_bot.message_handler(func=lambda m: m.text == "📩 تقديم شكوى")
def complaint_menu(msg):
    uid = msg.chat.id
    user = users.find_one({"_id": uid})
    
    if not user or user.get("status") != "active":
        return customer_bot.send_message(uid, "⚠️ عذراً، يجب تفعيل حسابك أولاً.")

    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🧾 شكوى بخصوص فاتورة/طلب", callback_data="comp_invoice"),
        types.InlineKeyboardButton("💳 شكوى بخصوص كارت محدد", callback_data="comp_card"),
        types.InlineKeyboardButton("🗂️ سجل الشكاوى السابقة", callback_data="comp_history")
    )
    
    customer_bot.send_message(uid, "🎧 **مركز الدعم الفني لشركة الأهرام:**\nيرجى تحديد نوع الشكوى:", reply_markup=kb, parse_mode="Markdown")

# --- 2. زر الرجوع للقائمة الرئيسية للشكاوى ---
@customer_bot.callback_query_handler(func=lambda call: call.data == "back_to_comp_main")
def back_to_main_complaint(call):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🧾 شكوى بخصوص فاتورة/طلب", callback_data="comp_invoice"),
        types.InlineKeyboardButton("💳 شكوى بخصوص كارت محدد", callback_data="comp_card"),
        types.InlineKeyboardButton("🗂️ سجل الشكاوى السابقة", callback_data="comp_history")
    )
    customer_bot.edit_message_text("🎧 **مركز الدعم الفني لشركة الأهرام:**\nيرجى تحديد نوع الشكوى:", call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
    customer_bot.answer_callback_query(call.id)

# --- 3. قسم شكاوى الفواتير ---
@customer_bot.callback_query_handler(func=lambda call: call.data == "comp_invoice")
def show_invoices_for_complaint(call):
    print("🔘 تم الضغط على زر: شكوى بخصوص فاتورة")
    try:
        uid = call.message.chat.id
        
        # استخدام طريقة الترتيب الأكثر أماناً في PyMongo
        recent_orders = list(transactions.find({"user_id": uid}).sort([("date", -1)]).limit(5))
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        
        if recent_orders:
            for order in recent_orders:
                # استخدام .get() لحماية الكود من الانهيار إذا كانت الفاتورة قديمة أو ناقصة البيانات
                o_id = order.get('order_id', 'بدون_رقم')
                price = order.get('total_price', 0.0)
                
                btn_text = f"📦 طلب: {o_id} | 💰 {price} د.ل"
                kb.add(types.InlineKeyboardButton(btn_text, callback_data=f"sel_inv_{o_id}"))
                
        kb.add(types.InlineKeyboardButton("🔍 البحث برقم الفاتورة", callback_data="search_invoice"))
        kb.add(types.InlineKeyboardButton("⬅️ رجوع", callback_data="back_to_comp_main"))
        
        text = "🧾 **اختر الفاتورة التي تواجه بها مشكلة:**\n*(تظهر هنا آخر 5 فواتير لك)*"
        customer_bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
        customer_bot.answer_callback_query(call.id)
        print("✅ تم عرض قائمة الفواتير بنجاح")
        
    except Exception as e:
        print(f"🚨 خطأ فني داخل زر الفواتير: {e}")
        customer_bot.answer_callback_query(call.id, "❌ حدث خطأ فني أثناء جلب الفواتير، راجع التيرمينال.", show_alert=True)

# --- 4. قسم البحث اليدوي عن فاتورة ---
@customer_bot.callback_query_handler(func=lambda call: call.data == "search_invoice")
def ask_invoice_number(call):
    res = customer_bot.send_message(call.message.chat.id, "✍️ **أرسل رقم الفاتورة (Order ID) الآن:**")
    customer_bot.register_next_step_handler(res, process_invoice_search)
    customer_bot.answer_callback_query(call.id)

def process_invoice_search(msg):
    order_id = msg.text.strip()
    order = transactions.find_one({"order_id": order_id, "user_id": msg.chat.id})
    
    if not order:
        return customer_bot.send_message(msg.chat.id, "❌ لم يتم العثور على فاتورة بهذا الرقم في حسابك.")
    
    ask_complaint_reason(msg, order_id)

# --- 5. اختيار الفاتورة وطلب السبب ---
@customer_bot.callback_query_handler(func=lambda call: call.data.startswith("sel_inv_"))
def handle_invoice_selection(call):
    order_id = call.data.replace("sel_inv_", "")
    ask_complaint_reason(call.message, order_id)
    customer_bot.answer_callback_query(call.id)

def ask_complaint_reason(msg, order_id):
    res = customer_bot.send_message(msg.chat.id, f"🧾 **الفاتورة رقم:** `{order_id}`\n\n✍️ **الرجاء كتابة تفاصيل المشكلة بدقة الآن:**", parse_mode="Markdown")
    customer_bot.register_next_step_handler(res, submit_final_complaint, order_id)


# --- دالة مساعدة لإرسال الإشعارات للمشرفين (تم إضافتها) ---
def notify_admins(admin_msg, kb):
    # إرسال للسوبر أدمن أولاً
    try:
        admin_bot.send_message(ADMIN_ID, admin_msg, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        print(f"🚨 لم يتم إرسال الإشعار للسوبر أدمن بسبب خطأ: {e}")

    # جلب جميع المشرفين من قاعدة البيانات
    all_admins = list(admins.find())
    for admin in all_admins:
        admin_chat_id = admin.get("_id")
        # التأكد من عدم إرسال الرسالة للسوبر أدمن مرتين
        if str(admin_chat_id) != str(ADMIN_ID):
            try:
                 admin_bot.send_message(admin_chat_id, admin_msg, reply_markup=kb, parse_mode="Markdown")
            except Exception as e:
                 print(f"🚨 لم يتم إرسال الإشعار للمشرف {admin_chat_id} بسبب خطأ: {e}")


# --- 6. إرسال شكوى الفاتورة للإدارة ---
def submit_final_complaint(msg, order_id):
    uid = msg.chat.id
    reason = msg.text
    user = users.find_one({"_id": uid})
    order = transactions.find_one({"order_id": order_id})

    complaint_id = datetime.datetime.now().strftime("C%y%m%d%H%M")
    complaints_db.insert_one({
        "comp_id": complaint_id, "user_id": uid, "order_id": order_id,
        "reason": reason, "status": "pending", "date": datetime.datetime.now()
    })

    customer_bot.send_message(uid, f"✅ **تم استلام شكواك بنجاح!**\nرقم الشكوى: `{complaint_id}`\n⏳ *حالة الطلب: قيد المراجعة من قبل الإدارة.*", parse_mode="Markdown")

    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🔄 إرجاع نفس الملف", callback_data=f"resend_{order_id}_{uid}"),
        types.InlineKeyboardButton("📤 تعديل وإرسال ملف جديد", callback_data=f"newfile_{order_id}_{uid}"),
        types.InlineKeyboardButton("💰 إلغاء الطلب وإرجاع القيمة", callback_data=f"refund_{order_id}_{uid}")
    )

    admin_msg = (
        f"🚨 **شكوى فاتورة جديدة!**\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 **العميل:** {user.get('name')} | 📞 `{user.get('phone', '00')}`\n"
        f"🆔 **الـ ID:** `{uid}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"🧾 **رقم الفاتورة:** `{order_id}`\n"
        f"📦 **المنتج:** {order.get('product')} | 🔢 **الكمية:** {order.get('qty')}\n"
        f"💵 **القيمة:** `{order.get('total_price')}` د.ل\n"
        "━━━━━━━━━━━━━━━\n"
        f"📝 **المشكلة:**\n{reason}"
    )
    # استخدام الدالة الجديدة لإرسال الإشعار للمشرفين (تم تعديل هذا السطر)
    notify_admins(admin_msg, kb)

# --- 7. قسم شكاوى الكروت المحددة ---
@customer_bot.callback_query_handler(func=lambda call: call.data == "comp_card")
def show_card_complaint(call):
    res = customer_bot.send_message(
        call.message.chat.id, 
        "💳 **أرسل الآن (كود الكارت) أو (السيريال) الذي تواجه مشكلة به:**\n*(اكتب الأرقام فقط بدقة)*", 
        parse_mode="Markdown"
    )
    customer_bot.register_next_step_handler(res, process_card_search)
    customer_bot.answer_callback_query(call.id)

def process_card_search(msg):
    uid = msg.chat.id
    search_val = msg.text.strip()
    
    # البحث في المخزن عن كارت تم بيعه لهذا العميل ويطابق الكود أو السيريال
    card = stock.find_one({
        "sold_to": uid,
        "$or": [{"code": search_val}, {"serial": search_val}]
    })
    
    if not card:
        return customer_bot.send_message(uid, "❌ لم يتم العثور على هذا الكارت في سجل مشترياتك. تأكد من الرقم أو السيريال وأعد المحاولة.")
        
    # البحث عن الفاتورة المرتبطة (نجلب أحدث فاتورة لهذا المنتج لنفس العميل)
    product_name = card.get("product")
    related_order = transactions.find_one({"user_id": uid, "product": product_name}, sort=[("date", -1)])
    order_id = related_order.get("order_id") if related_order else "غير محدد"
            
    # تجهيز النص وتظليل الكارت
    text = (
        f"✅ **تم مطابقة الكارت في سجلاتك:**\n"
        f"🧾 **الفاتورة المرتبطة:** `{order_id}`\n"
        f"📦 **المنتج:** {product_name}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔑 **بيانات الكارت (المظللة):**\n"
        f"🔸 الكود: `{card.get('code', 'غير متوفر')}`\n"
        f"🔸 السيريال: `{card.get('serial', 'غير متوفر')}`\n"
        f"🔸 الرقم السري: `{card.get('pin', 'غير متوفر')}`\n"
        f"🔸 اوبريشن كود: `{card.get('op_code', 'غير متوفر')}`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"❓ **ما هي المشكلة التي تواجهها مع هذا الكارت تحديداً؟**"
    )
    
    # خيارات الشكوى
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("❌ الكارت لا يعمل", callback_data=f"cr_{card['_id']}_notworking"),
        types.InlineKeyboardButton("♻️ الكارت مستخدم مسبقاً", callback_data=f"cr_{card['_id']}_used"),
        types.InlineKeyboardButton("💬 مشكلة أخرى", callback_data=f"cr_{card['_id']}_other")
    )
    
    customer_bot.send_message(uid, text, reply_markup=kb, parse_mode="Markdown")

# --- 8. إرسال شكوى الكارت للإدارة ---
@customer_bot.callback_query_handler(func=lambda call: call.data.startswith("cr_"))
def submit_card_complaint(call):
    data_parts = call.data.split("_")
    card_id = data_parts[1]
    reason_code = data_parts[2]
    uid = call.message.chat.id
    
    reasons_dict = {
        "notworking": "الكارت لا يعمل نهائياً",
        "used": "الكارت يظهر أنه مستخدم مسبقاً",
        "other": "مشكلة أخرى (غير محددة)"
    }
    reason_text = reasons_dict.get(reason_code, "غير معروف")
    
    card = stock.find_one({"_id": ObjectId(card_id)})
    user = users.find_one({"_id": uid})
    
    if not card:
        return customer_bot.answer_callback_query(call.id, "❌ خطأ فني في استرجاع الكارت.", show_alert=True)
        
    complaint_id = datetime.datetime.now().strftime("CC%y%m%d%H%M")
    
    # أرشفة الشكوى
    complaints_db.insert_one({
        "comp_id": complaint_id, "user_id": uid, "card_id": card_id,
        "type": "single_card", "reason": reason_text, "status": "pending", "date": datetime.datetime.now()
    })
    
    customer_bot.edit_message_text(
        f"✅ **تم إرسال شكواك للإدارة بنجاح!**\n"
        f"🔖 رقم الشكوى: `{complaint_id}`\n"
        f"📌 المشكلة: {reason_text}\n"
        f"⏳ *حالة الطلب: قيد المراجعة.*",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown"
    )
    
    # إرسال التنبيه للإدارة
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💰 إرجاع قيمة الكارت (كارت واحد)", callback_data=f"ref1card_{card_id}_{uid}"),
        types.InlineKeyboardButton("↩️ الرد على العميل", callback_data=f"replycomp_{uid}")
    )
    
    admin_msg = (
        f"🚨 **شكوى كارت محدد جديدة!**\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 **العميل:** {user.get('name')} | 📞 `{user.get('phone', '00')}`\n"
        f"🆔 **الـ ID:** `{uid}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📦 **المنتج:** {card.get('product')}\n"
        f"🔑 **الكود المشتكى منه:** `{card.get('code')}`\n"
        f"⚙️ **السيريال:** `{card.get('serial')}`\n"
        "━━━━━━━━━━━━━━━\n"
        f"📝 **المشكلة:** {reason_text}\n"
        f"🔖 **رقم الشكوى:** `{complaint_id}`"
    )
    
    # استخدام الدالة الجديدة لإرسال الإشعار للمشرفين (تم تعديل هذا السطر)
    notify_admins(admin_msg, kb)


# --- 8. سجل الشكاوى السابقة (محدث ومحمي) ---
@customer_bot.callback_query_handler(func=lambda call: call.data == "comp_history")
def show_complaints_history(call):
    print("🔘 تم الضغط على زر: سجل الشكاوى")
    try:
        uid = call.message.chat.id
        
        # 1. جلب الشكاوى بالطريقة الآمنة (مع الأقواس المربعة)
        comps = list(complaints_db.find({"user_id": uid}).sort([("date", -1)]).limit(5))
        
        if not comps:
            return customer_bot.answer_callback_query(call.id, "📭 لا يوجد لديك شكاوى مسجلة في النظام.", show_alert=True)
        
        # 2. تجهيز النص وعرض الحالة بناءً على قرار الإدارة
        text = "🗂️ **سجل الشكاوى الخاصة بك (آخر 5):**\n\n"
        for c in comps:
            status_code = c.get("status", "pending")
            
            # ترجمة حالة الشكوى لشكل احترافي للعميل
            if status_code == "pending":
                status_text = "قيد المراجعة ⏳"
            elif status_code.startswith("refunded"):
                status_text = "تم الإرجاع 💸"
            elif status_code.startswith("resolved"):
                status_text = "تم الحل ✅"
            else:
                status_text = "مغلقة 🔒"

            text += (
                f"🔖 **رقم الشكوى:** `{c.get('comp_id', 'بدون_رقم')}`\n"
                f"📌 **الحالة:** {status_text}\n"
                "━━━━━━━━━━━━━━━\n"
            )
            
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ رجوع", callback_data="back_to_comp_main"))
        
        # 3. إرسال السجل للعميل
        customer_bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
        customer_bot.answer_callback_query(call.id)
        
    except Exception as e:
        print(f"🚨 خطأ فني في سجل الشكاوى: {e}")
        customer_bot.answer_callback_query(call.id, "❌ حدث خطأ فني أثناء جلب السجل، راجع التيرمينال.", show_alert=True)