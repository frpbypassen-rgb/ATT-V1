from config import customer_bot, admin_bot, ADMIN_ID, users, recharge_cards
from Customer_Bot.handlers.can_recharge import send_recharge_invoice
from config import customer_bot, admin_bot, users, transactions, recharge_cards, ADMIN_ID
from telebot import types
import datetime

# --- 1. عرض تفاصيل الحساب ---
@customer_bot.message_handler(func=lambda m: m.text == "👤 الحساب")
def show_account_details(msg):
    uid = msg.chat.id
    try:
        # جلب بيانات المستخدم
        user_data = users.find_one({"_id": uid})
        if not user_data:
            return customer_bot.send_message(uid, "❌ لم يتم العثور على بيانات حسابك.")

        # حساب استهلاك اليوم
        start_of_today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_txs = list(transactions.find({
            "user_id": uid,
            "date": {"$gte": start_of_today}
        }))
        total_spent_today = sum(t.get('total_price', 0) for t in today_txs)

        # تجهيز النص
        account_text = (
            "👤 **بروفايل العميل - شركة الأهرام**\n"
            "━━━━━━━━━━━━━━━\n"
            f"📝 **الاسم:** {user_data.get('name', 'غير مسجل')}\n"
            f"🆔 **المعرف (ID):** `{uid}`\n"
            f"📞 **الهاتف:** `{user_data.get('phone', '00000')}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"💰 **رصيدك الحالي:** `{user_data.get('balance', 0.0):.2f}` د.ل\n"
            f"📊 **استهلاكك اليوم:** `{total_spent_today:.2f}` د.ل\n"
            "━━━━━━━━━━━━━━━\n"
            "⚠️ *أدخل الكود بدقة، 4 محاولات خطأ تؤدي للحظر.*"
        )

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("💳 شحن رصيد بكارت", callback_data="request_charge"))
        
        customer_bot.send_message(uid, account_text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        print(f"🚨 خطأ في عرض الحساب: {e}")
        customer_bot.send_message(uid, "❌ عذراً، حدث خطأ فني أثناء جلب بيانات الحساب.")

# --- 2. طلب كود الشحن ---
@customer_bot.callback_query_handler(func=lambda call: call.data == "request_charge")
def ask_for_card(call):
    uid = call.message.chat.id
    user = users.find_one({"_id": uid})
    
    if user.get("status") == "blocked":
        return customer_bot.answer_callback_query(call.id, "🚫 حسابك محظور حالياً.", show_alert=True)

    res = customer_bot.send_message(uid, "💳 **يرجى إدخال كود كارت الشحن الآن:**")
    customer_bot.register_next_step_handler(res, validate_recharge_card)
    customer_bot.answer_callback_query(call.id)

# --- 3. التحقق من الكارت والأمان ---
def validate_recharge_card(msg):
    uid = msg.chat.id
    # تنظيف الكود وتحويله لحروف كبيرة لضمان التطابق
    card_code = msg.text.strip().upper() 
    user = users.find_one({"_id": uid})
    
    # التعديل هنا: استخدام status بدلاً من used
    card = recharge_cards.find_one({"code": card_code, "status": "active"})

    if card:
        amount = float(card.get("value", 0.0))
        
        # 1. تحديث الرصيد وإعادة تعيين المحاولات الفاشلة
        users.update_one({"_id": uid}, {
            "$inc": {"balance": amount},
            "$set": {"failed_attempts": 0}
        })
        
        # 2. تحديث حالة الكارت إلى مستخدم
        recharge_cards.update_one({"code": card_code}, {
            "$set": {
                "status": "used", 
                "used_by": uid, 
                "use_date": datetime.datetime.now()
            }
        })
        
        # 3. إرسال رسالة النجاح للعميل
        customer_bot.send_message(uid, f"✅ **تم الشحن بنجاح!**\nتم إضافة `{amount:.2f}` د.ل لرصيدك.")
        

# 🌟 إرسال إشعار فوري للإدارة (نسخة التعبئة)
        try:
            # جلب اسم العميل إذا كان موجوداً
            user_name = user.get("name", "غير معروف") if user else "غير معروف"
            
            # تصميم رسالة الإدارة
            admin_msg = (
                f"🚨 **إشعار عملية شحن جديدة** 🚨\n\n"
                f"👤 **العميل:** `{user_name}`\n"
                f"🆔 **المعرف:** `{uid}`\n"
                f"💳 **الكود المستخدم:** `{card_code}`\n"
                f"💰 **القيمة المشحونة:** `{amount:.2f}` د.ل\n"
                f"⏰ **الوقت:** `{datetime.datetime.now().strftime('%Y-%m-%d | %I:%M %p')}`"
            )
            
            # إرسال الرسالة لبوت الإدارة
            admin_bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
            print("✅ [نجاح]: تم إرسال إشعار التعبئة للإدارة.")
            
        except Exception as e:
            print(f"🚨 [خطأ]: فشل في إرسال إشعار الإدارة: {e}")



        # 4. إرسال الفاتورة (PDF) 
        try:
            # تم استخدام المتغير user بدلاً من user_data وإزاحة الكود بمسافة صحيحة
            user_name = user.get('name', 'عميل غير معروف') if user else 'عميل غير معروف'
            user_phone = user.get('phone', 'غير متوفر') if user else 'غير متوفر'
            
            send_recharge_invoice(uid, amount, user_name, user_phone, customer_bot)
        except Exception as e:
            print(f"🚨 فشل إرسال PDF: {e}")
            
    else:
        # --- منطق المحاولات الفاشلة العبقري الخاص بك ---
        new_attempts = user.get("failed_attempts", 0) + 1
        users.update_one({"_id": uid}, {"$set": {"failed_attempts": new_attempts}})
        
        if new_attempts >= 4:
            users.update_one({"_id": uid}, {"$set": {"status": "blocked"}})
            customer_bot.send_message(uid, "🚨 **تم حظر حسابك تلقائياً!**\nاكتشف النظام محاولة تخمين. تواصل مع الإدارة.")
            
            # إرسال تنبيه للأدمن
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("✅ فك الحظر", callback_data=f"unblock_{uid}"),
                types.InlineKeyboardButton("💀 طرد", callback_data=f"kick_{uid}")
            )
            alert = (
                "🚨 **محاولة تخمين كروت!**\n"
                f"👤 العميل: {user.get('name', 'غير مسجل')}\n"
                f"📞 الهاتف: {user.get('phone', '00000')}\n"
                f"🆔 الـ ID: `{uid}`\n"
                "📌 **تم الحظر تلقائياً.**"
            )
            admin_bot.send_message(ADMIN_ID, alert, reply_markup=kb, parse_mode="Markdown")
        else:
            customer_bot.send_message(uid, f"❌ كود خاطئ أو مستخدم مسبقاً! متبقي لك ({4 - new_attempts}) محاولات.")