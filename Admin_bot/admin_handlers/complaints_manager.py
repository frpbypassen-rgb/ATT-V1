import datetime
import pandas as pd
import io
from config import admin_bot, customer_bot, users, transactions, complaints_db, stock
from telebot import types
from bson.objectid import ObjectId

# --- إعدادات النظام المطور ---
ITEMS_PER_PAGE = 3  # عدد الشكاوى المعروضة في كل صفحة لمنع الزحام

# ==========================================
# 1. شكاوى النصوص العادية (الرد المباشر)
# ==========================================
@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("replycomp_"))
def ask_reply_complaint(call):
    uid = int(call.data.split("_")[1])
    res = admin_bot.send_message(call.message.chat.id, f"✍️ **اكتب ردك الآن للعميل صاحب الـ ID (`{uid}`):**\n*(بمجرد إرسال الرسالة، ستصل للعميل فوراً)*", parse_mode="Markdown")
    admin_bot.register_next_step_handler(res, send_reply_to_customer, uid)
    admin_bot.answer_callback_query(call.id)

def send_reply_to_customer(msg, uid):
    reply_text = msg.text
    if not reply_text:
        return admin_bot.send_message(msg.chat.id, "❌ خطأ: الرد يجب أن يكون نصياً.")

    customer_msg = f"📨 **رسالة من الإدارة (تحديث لشكواك):**\n━━━━━━━━━━━━━━━\n{reply_text}\n━━━━━━━━━━━━━━━\n👨‍💻 *فريق الدعم - شركة الأهرام*"
    try:
        customer_bot.send_message(uid, customer_msg, parse_mode="Markdown")
        admin_bot.send_message(msg.chat.id, "✅ **تم إرسال ردك للعميل بنجاح!**")
    except Exception as e:
        print(f"🚨 خطأ: {e}")
        admin_bot.send_message(msg.chat.id, "❌ فشل إرسال الرد. قد يكون العميل قام بحظر البوت الخاص به.")

# ==========================================
# 2. شكاوى الفواتير (إرجاع، ملف جديد، استرداد)
# ==========================================
@admin_bot.callback_query_handler(func=lambda call: call.data.startswith(("resend_", "newfile_", "refund_")))
def handle_invoice_complaint_actions(call):
    try:
        data_parts = call.data.split("_")
        action = data_parts[0]
        order_id = data_parts[1]
        uid = int(data_parts[2])

        order = transactions.find_one({"order_id": order_id})
        
        # حماية: إذا كانت الفاتورة ملغاة مسبقاً، لا يمكن استردادها أو إرسال ملفها مرة أخرى
        if not order and action != "newfile": 
            return admin_bot.answer_callback_query(call.id, "❌ الفاتورة غير موجودة، يبدو أنه تم إرجاعها وحذفها مسبقاً.", show_alert=True)

        # ----------------------------------------------------
        # إجراء 1: استرداد القيمة وحذف الفاتورة
        # ----------------------------------------------------
        if action == "refund":
            amount = order.get("total_price", 0.0)
            users.update_one({"_id": uid}, {"$inc": {"balance": amount}})
            transactions.delete_one({"order_id": order_id})
            complaints_db.update_many({"order_id": order_id}, {"$set": {"status": "refunded", "resolved_date": datetime.datetime.now()}})
            
            admin_bot.edit_message_text(
                f"💰 **تمت عملية الإرجاع بنجاح**\n━━━━━━━━━━━━━━━\n🧾 فاتورة رقم: `{order_id}`\n👤 العميل ID: `{uid}`\n💵 المبلغ المسترد: `{amount}` د.ل\n📌 **الإجراء:** تم إرجاع المبلغ وحذف الفاتورة.", 
                call.message.chat.id, call.message.message_id, parse_mode="Markdown"
            )
            
            try:
                customer_bot.send_message(uid, f"💸 **إشعار من الإدارة:**\nتم قبول شكواك للفاتورة `{order_id}`.\n✅ **تم إرجاع `{amount}` د.ل لرصيدك.**", parse_mode="Markdown")
            except: pass

        # ----------------------------------------------------
        # إجراء 2: توليد وإرجاع نفس الملف القديم (نظام البحث الذكي)
        # ----------------------------------------------------
        elif action == "resend":
            try:
                qty = int(order.get("qty", 1))
                product_name = order.get("product")
                
                # 1. المحاولة الأولى: البحث الدقيق (العميل + القسم + التاريخ)
                sold_cards = list(stock.find({
                    "sold_to": uid, 
                    "subcategory": product_name
                }).sort([("sold_date", -1)]).limit(qty))
                
                # 2. المحاولة الثانية (الإنقاذ): إذا كانت بيانات قديمة، ابحث عن أي كروت مباعة لهذا القسم
                if not sold_cards:
                    sold_cards = list(stock.find({
                        "subcategory": product_name, 
                        "sold": True
                    }).sort([("_id", -1)]).limit(qty))
                
                # إذا استمر الفشل (القسم فارغ تماماً من المبيعات)
                if not sold_cards:
                    admin_bot.answer_callback_query(call.id, "❌ لم يتم العثور على أي كروت تطابق هذه الفاتورة في الأرشيف.", show_alert=True)
                    return

                # حماية الأعمدة من الانهيار
                df = pd.DataFrame(sold_cards)
                expected_cols = ['name', 'code', 'serial', 'pin', 'op_code']
                
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = "غير مسجل"
                        
                df = df[expected_cols]
                df.rename(columns={'name': 'المنتج', 'code': 'الكود', 'serial': 'السيريال', 'pin': 'الرقم السري', 'op_code': 'أوبريشن'}, inplace=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                output.seek(0)
                output.name = f"AlAhram_Copy_{order_id}.xlsx"

                complaints_db.update_many({"order_id": order_id}, {"$set": {"status": "resolved_resend", "resolved_date": datetime.datetime.now()}})
                
                customer_bot.send_document(
                    uid, 
                    output, 
                    caption=f"📁 **تحديث بخصوص شكواك:**\nمرفق نسخة من الكروت للفاتورة رقم `{order_id}`.", 
                    parse_mode="Markdown"
                )
                
                admin_bot.edit_message_text(f"✅ **تم استخراج الملف من الأرشيف وإرساله للعميل بنجاح.**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
                
            except Exception as e:
                print(f"🚨 خطأ فني في إعادة التوليد: {e}")
                admin_bot.answer_callback_query(call.id, "❌ حدث خطأ فني، راجع شاشة الأوامر.", show_alert=True)

        # ----------------------------------------------------
        # إجراء 3: إرسال ملف تعويضي جديد يدوياً
        # ----------------------------------------------------
        elif action == "newfile":
            res = admin_bot.send_message(call.message.chat.id, f"📤 **أرسل الآن ملف الـ Excel (أو الصورة) الجديد لتعويض الفاتورة (`{order_id}`):**")
            admin_bot.register_next_step_handler(res, forward_custom_file_to_customer, uid, order_id)
        
        # إغلاق أيقونة التحميل من على الزر
        admin_bot.answer_callback_query(call.id)
        
    except Exception as e:
        print(f"🚨 خطأ في أزرار لوحة التحكم: {e}")
        admin_bot.answer_callback_query(call.id, "❌ حدث خطأ فني أثناء التنفيذ.", show_alert=True)

# --- استلام الملف التعويضي وإرساله (مطور لحل مشكلة تليجرام) ---
def forward_custom_file_to_customer(msg, uid, order_id):
    if not msg.document and not msg.photo:
        res = admin_bot.send_message(msg.chat.id, "❌ يجب إرسال ملف أو صورة. حاول مرة أخرى:")
        admin_bot.register_next_step_handler(res, forward_custom_file_to_customer, uid, order_id)
        return

    caption = f"🎁 **تعويض من الإدارة:**\nمرفق بديل بخصوص الفاتورة رقم `{order_id}`. نعتذر عن أي إزعاج."
    
    try:
        # رسالة لتطمينك أن البوت يعمل ولم يتوقف
        admin_bot.send_message(msg.chat.id, "🔄 جاري معالجة الملف وتمريره للعميل، لحظات...")

        if msg.document:
            # 1. تحميل الملف من بوت الإدارة
            file_info = admin_bot.get_file(msg.document.file_id)
            downloaded_file = admin_bot.download_file(file_info.file_path)
            
            # 2. إرسال الملف الفعلي عبر بوت العميل
            customer_bot.send_document(
                uid, 
                downloaded_file, 
                visible_file_name=msg.document.file_name, # يحافظ على اسم الإكسيل
                caption=caption, 
                parse_mode="Markdown"
            )

        elif msg.photo:
            # 1. تحميل الصورة من بوت الإدارة
            file_info = admin_bot.get_file(msg.photo[-1].file_id)
            downloaded_file = admin_bot.download_file(file_info.file_path)
            
            # 2. إرسال الصورة عبر بوت العميل
            customer_bot.send_photo(
                uid, 
                downloaded_file, 
                caption=caption, 
                parse_mode="Markdown"
            )
        
        # 3. تحديث حالة الشكوى في النظام
        complaints_db.update_many({"order_id": order_id}, {"$set": {"status": "resolved_replacement", "resolved_date": datetime.datetime.now()}})
        admin_bot.send_message(msg.chat.id, "✅ **تم إرسال الملف التعويضي للعميل بنجاح وإغلاق الشكوى.**")
        
    except Exception as e:
        print(f"🚨 خطأ أثناء النقل بين البوتين: {e}")
        admin_bot.send_message(msg.chat.id, "❌ فشل الإرسال، تأكد أن حجم الملف ليس كبيراً جداً، أو أن العميل لم يقم بإيقاف البوت.")

# --- إضافة دالة للتعامل مع شكوى الكارت الفردي ---
@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("ref1card_"))
def handle_single_card_refund(call):
    data_parts = call.data.split("_")
    card_id = data_parts[1]
    uid = int(data_parts[2])

    from bson.objectid import ObjectId
    card = stock.find_one({"_id": ObjectId(card_id)})
    
    if not card:
        return admin_bot.answer_callback_query(call.id, "❌ الكارت غير موجود في النظام.", show_alert=True)
        
    # جلب سعر الكارت من الكارت نفسه (الـ price_1)
    card_price = card.get("price_1", 0.0)
    
    # 1. إرجاع قيمة الكارت فقط لحساب العميل
    users.update_one({"_id": uid}, {"$inc": {"balance": card_price}})
    
    # 2. حذف الكارت من قاعدة البيانات لأنه تالف/مستخدم
    stock.delete_one({"_id": ObjectId(card_id)})
    
    # 3. إغلاق الشكوى
    complaints_db.update_many({"card_id": card_id}, {"$set": {"status": "refunded_single", "resolved_date": datetime.datetime.now()}})
    
    # تحديث رسالة الإدارة
    admin_bot.edit_message_text(
        f"✅ **تم تعويض العميل عن الكارت التالف**\n"
        f"تم إرجاع `{card_price}` د.ل لرصيده وحذف الكارت من قاعدة البيانات.", 
        call.message.chat.id, call.message.message_id, parse_mode="Markdown"
    )
    
    # إشعار العميل
    try:
        customer_bot.send_message(
            uid, 
            f"💸 **تحديث بخصوص شكوى الكارت:**\nتمت مراجعة الكود، وتم إرجاع قيمة الكارت (`{card_price}` د.ل) إلى رصيدك. نعتذر عن هذا الخطأ.", 
            parse_mode="Markdown"
        )
    except: pass

# ==========================================
# 3. المحرك الرئيسي لعرض الشكاوي المعلقة (المطور)
# ==========================================

@admin_bot.message_handler(func=lambda m: m.text == "📩 الشكاوي المعلقة")
def list_pending_complaints_start(msg):
    # بدء العرض من الصفحة رقم 0
    show_complaints_page(msg.chat.id, page=0)

def show_complaints_page(chat_id, page):
    # جلب جميع الشكاوي المعلقة وفرزها من الأحدث للأقدم
    pending_complaints = list(complaints_db.find({"status": "pending"}).sort("date", -1))
    total_count = len(pending_complaints)

    if total_count == 0:
        return admin_bot.send_message(chat_id, "✅ **لا توجد شكاوي معلقة حالياً.**\nكل شيء تحت السيطرة!", parse_mode="Markdown")

    # حساب النطاق للصفحة الحالية
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_batch = pending_complaints[start_idx:end_idx]

    admin_bot.send_message(chat_id, f"📂 **إدارة الشكاوي** (الصفحة {page+1})\nإجمالي المعلق: `{total_count}` شكوى", parse_mode="Markdown")

    for comp in current_batch:
        uid = comp.get("user_id")
        order_id = comp.get("order_id")
        comp_text = comp.get("reason", "لا يوجد نص")
        c_date = comp.get("date", datetime.datetime.now())
        comp_id = str(comp.get("_id"))
        
        # ميزة التنبيه للشكاوى المتأخرة (أكثر من 24 ساعة)
        is_urgent = (datetime.datetime.now() - c_date).total_seconds() > 86400
        priority_tag = "🚨 **تنبيه: شكوى متأخرة!**\n" if is_urgent else ""
        
        # جلب بيانات العميل للتوضيح
        user_data = users.find_one({"_id": uid})
        user_name = user_data.get("name", "غير مسجل") if user_data else "غير مسجل"

        # تجهيز النص المعروض للأدمن
        report_text = (
            f"{priority_tag}"
            f"📩 **شكوى من العميل:** {user_name}\n"
            f"🆔 **معرف العميل:** `{uid}`\n"
            f"🧾 **رقم الفاتورة:** `{order_id if order_id else 'شكوى عامة'}`\n"
            f"📅 **وقت الشكوى:** `{c_date.strftime('%Y-%m-%d %H:%M')}`\n"
            f"📝 **نص الشكوى:**\n{comp_text}\n"
            f"━━━━━━━━━━━━━━━"
        )

        kb = types.InlineKeyboardMarkup(row_width=2)
        
        # أزرار الإجراءات الخاصة بالفواتير
        if order_id:
            btn_resend = types.InlineKeyboardButton("🔄 إعادة إرسال", callback_data=f"resend_{order_id}_{uid}")
            btn_refund = types.InlineKeyboardButton("💰 استرداد القيمة", callback_data=f"refund_{order_id}_{uid}")
            btn_newfile = types.InlineKeyboardButton("📂 إرسال تعويض", callback_data=f"newfile_{order_id}_{uid}")
            kb.add(btn_resend, btn_newfile)
            kb.add(btn_refund)
        
        # أزرار الردود (تم إضافة الرد السريع)
        btn_quick = types.InlineKeyboardButton("⚡ رد سريع", callback_data=f"quickmenu_{comp_id}_{uid}")
        btn_reply = types.InlineKeyboardButton("💬 رد نصي", callback_data=f"replycomp_{uid}")
        kb.add(btn_quick, btn_reply)

        admin_bot.send_message(chat_id, report_text, reply_markup=kb, parse_mode="Markdown")

    # أزرار التنقل بين الصفحات (Pagination)
    nav_kb = types.InlineKeyboardMarkup()
    nav_btns = []
    if page > 0:
        nav_btns.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"cpage_{page-1}"))
    if end_idx < total_count:
        nav_btns.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"cpage_{page+1}"))
        
    if nav_btns:
        nav_kb.add(*nav_btns)
        admin_bot.send_message(chat_id, "🔄 **التنقل بين الشكاوي:**", reply_markup=nav_kb)

# ==========================================
# 4. معالجات تفاعلية (التنقل + الردود السريعة)
# ==========================================

# معالج التنقل بين الصفحات
@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("cpage_"))
def handle_complaints_pagination(call):
    page = int(call.data.split("_")[1])
    # مسح أزرار التنقل القديمة لترتيب الشاشة
    admin_bot.delete_message(call.message.chat.id, call.message.message_id)
    show_complaints_page(call.message.chat.id, page)
    admin_bot.answer_callback_query(call.id)

# معالج فتح قائمة الردود السريعة
@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("quickmenu_"))
def show_quick_replies(call):
    _, comp_id, c_uid = call.data.split("_")
    kb = types.InlineKeyboardMarkup(row_width=1)
    
    # الخيارات المتاحة
    kb.add(
        types.InlineKeyboardButton("🔎 جاري فحص المشكلة", callback_data=f"execq_{comp_id}_{c_uid}_check"),
        types.InlineKeyboardButton("✅ تم الحل بنجاح", callback_data=f"execq_{comp_id}_{c_uid}_solved"),
        types.InlineKeyboardButton("💰 تم تحديث الرصيد", callback_data=f"execq_{comp_id}_{c_uid}_balance"),
        types.InlineKeyboardButton("❌ إلغاء قائمة الرد السريع", callback_data="cancel_quick")
    )
    admin_bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb)

# معالج زر الإلغاء
@admin_bot.callback_query_handler(func=lambda call: call.data == "cancel_quick")
def cancel_quick_menu(call):
    admin_bot.answer_callback_query(call.id, "تم الإلغاء")
    # مسح القائمة المنبثقة
    admin_bot.delete_message(call.message.chat.id, call.message.message_id)

# معالج تنفيذ الرد السريع وإرساله للعميل
@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("execq_"))
def execute_quick_reply(call):
    parts = call.data.split("_")
    comp_id = parts[1]
    c_uid = int(parts[2])
    action = parts[3]
    
    # نصوص القوالب الجاهزة
    QUICK_TEXTS = {
        "check": "🔎 جاري فحص مشكلتك الآن، سنوافيك بالرد فوراً.",
        "solved": "✅ تم حل المشكلة بنجاح، نعتذر عن الإزعاج.",
        "balance": "💰 تم مراجعة الرصيد وتحديثه في حسابك."
    }
    reply_text = QUICK_TEXTS.get(action, "تم الرد")
    
    try:
        # إرسال للعميل
        customer_msg = f"📨 **رسالة من الإدارة (تحديث لشكواك):**\n━━━━━━━━━━━━━━━\n{reply_text}\n━━━━━━━━━━━━━━━\n👨‍💻 *فريق الدعم - شركة الأهرام*"
        customer_bot.send_message(c_uid, customer_msg, parse_mode="Markdown")
        
        # تحديث حالة الشكوى في الداتابيز
        if action == "solved":
            complaints_db.update_many({"_id": ObjectId(comp_id)}, {"$set": {"status": "solved", "resolved_date": datetime.datetime.now()}})
        else:
            complaints_db.update_many({"_id": ObjectId(comp_id)}, {"$set": {"status": "replied"}})
            
        admin_bot.answer_callback_query(call.id, "✅ تم إرسال الرد السريع")
        admin_bot.edit_message_text(f"✅ **تم الرد السريع على العميل ({c_uid}):**\n_{reply_text}_", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    except Exception as e:
        print(f"🚨 فشل الرد السريع: {e}")
        admin_bot.answer_callback_query(call.id, "❌ فشل الإرسال (قد يكون العميل حظر البوت)", show_alert=True)