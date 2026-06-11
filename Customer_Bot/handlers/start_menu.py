import datetime
import random
from telebot import types
from config import customer_bot, admin_bot, users, ADMIN_ID, ADMIN_IDS 

# ذاكرة مؤقتة لحفظ الاسم أثناء خطوات التسجيل
registration_state = {}

# ==========================================
# 1. شاشة البداية (التحقق من العميل)
# ==========================================
@customer_bot.message_handler(commands=['start'])
def start_and_register(msg):
    print("📩 [Customer Bot] رسالة start وصلت إلى الكود بنجاح!")
    
    uid = msg.chat.id

    # التحقق: هل العميل مسجل مسبقاً في قاعدة البيانات؟
    user = users.find_one({"_id": uid})
    
    if user:
        # إذا كان الحساب موجوداً ولكنه "معلق" ينتظر موافقة الإدارة
        if user.get("status") == "pending":
            return customer_bot.send_message(
                uid, 
                "⏳ **حسابك قيد المراجعة**\nبياناتك لدى الإدارة حالياً، يرجى الانتظار لحين تفعيل حسابك.",
                parse_mode="Markdown"
            )
        # إذا كان الحساب مفعلاً، نعرض له القائمة الرئيسية للمتجر
        else:
            return show_main_menu(msg) 

    # إذا كان عميلاً جديداً، نبدأ رحلة التسجيل
    res = customer_bot.send_message(
        uid,
        "👋 **مرحباً بك في متجر شركة الأهرام!**\n\n"
        "للبدء في استخدام خدماتنا، نحتاج لبعض البيانات الأساسية.\n\n"
        "📝 **يرجى إرسال اسمك الثلاثي الآن:**",
        parse_mode="Markdown"
    )
    customer_bot.register_next_step_handler(res, process_name_step)

# ==========================================
# 2. استلام الاسم وطلب رقم الهاتف (توثيق تليجرام)
# ==========================================
def process_name_step(msg):
    uid = msg.chat.id
    name = msg.text.strip()

    # حفظ الاسم مؤقتاً
    registration_state[uid] = {"name": name}

    # إنشاء زر "مشاركة جهة الاتصال" الإجباري
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_contact = types.KeyboardButton(text="📱 مشاركة رقم الهاتف", request_contact=True)
    kb.add(btn_contact)

    res = customer_bot.send_message(
        uid,
        f"أهلاً بك يا {name} ✨\n\n"
        "🔒 **الخطوة الأخيرة:**\n"
        "لضمان أمان حسابك، اضغط على الزر بالأسفل لمشاركة رقم هاتفك المرتبط بالتليجرام:",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    customer_bot.register_next_step_handler(res, process_contact_step)

# ==========================================
# 3. استلام الرقم، التوثيق الأمني، وإشعار الإدارة
# ==========================================
def process_contact_step(msg):
    uid = msg.chat.id

    # أ. التحقق من استخدام الزر المخصص
    if not msg.contact:
        res = customer_bot.send_message(uid, "❌ **خطأ:** يرجى استخدام زر (📱 مشاركة رقم الهاتف) الموجود في الأسفل بدلاً من الكتابة.")
        return customer_bot.register_next_step_handler(res, process_contact_step)

    # ب. التوثيق الأمني (منع إرسال رقم شخص آخر)
    if msg.contact.user_id != uid:
        res = customer_bot.send_message(uid, "❌ **خطأ أمني:** يرجى مشاركة رقمك أنت، وليس جهة اتصال لشخص آخر!")
        return customer_bot.register_next_step_handler(res, process_contact_step)

    # ج. سحب البيانات وتجهيزها
    phone = msg.contact.phone_number
    name = registration_state.get(uid, {}).get("name", msg.from_user.first_name)
    remove_kb = types.ReplyKeyboardRemove() # لإخفاء زر المشاركة بعد الانتهاء

    # د. حفظ العميل الجديد في قاعدة البيانات (كحساب معلق)
    new_user = {
        "_id": uid,
        "name": name,
        "phone": phone,
        "balance": 0.0,
        "level": 1,
        "status": "pending", # الحساب يبدأ "معلق" حتى تفاعله الإدارة
        "reg_date": datetime.datetime.now()
    }
    
    try:
        users.insert_one(new_user)
    except Exception:
        pass # تجاهل الخطأ في حال كان العميل موجوداً مسبقاً بالصدفة

    registration_state.pop(uid, None) # تنظيف الذاكرة المؤقتة

    # هـ. رسالة نهاية التسجيل للعميل
    customer_bot.send_message(
        uid,
        "✅ **تم تسجيل حسابك بنجاح!**\n\n"
        "تم إرسال بياناتك للإدارة للمراجعة. ستصلك رسالة فور تفعيل حسابك لتتمكن من الشراء.",
        reply_markup=remove_kb,
        parse_mode="Markdown"
    )

    # و. إرسال الإشعار الفوري لكل المشرفين
    notify_admin_new_user(uid, name, phone)

# ==========================================
# 4. دالة الإشعار الفوري (محدثة لترسل لجميع المشرفين)
# ==========================================
def notify_admin_new_user(user_id, name, phone):
    admin_text = (
        f"🔔 **تسجيل عميل جديد!**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📝 **الاسم:** {name}\n"
        f"📞 **الهاتف:** `{phone}`\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💡 *حساب العميل مقيد حالياً بانتظار التفعيل.*"
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ تفعيل العميل الآن", callback_data=f"set_status_active_{user_id}"))

    # المرور على قائمة جميع المشرفين وإرسال الإشعار
    for admin_id in ADMIN_IDS:
        try:
            admin_bot.send_message(admin_id, admin_text, reply_markup=kb, parse_mode="Markdown")
        except Exception as e:
            print(f"🚨 تعذر إرسال الإشعار للمشرف {admin_id}: {e}")

# ==========================================
# 5. القائمة الرئيسية (تظهر للعملاء المفعلين)
# ==========================================
def show_main_menu(msg):
    uid = msg.chat.id

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton("🛒 شراء كروت"), types.KeyboardButton("👤 الحساب"))
    kb.add(types.KeyboardButton("📩 تقديم شكوى"), types.KeyboardButton("📜 سجل المشتريات"))
    kb.add(types.KeyboardButton("🛒 سلة المشتريات"), types.KeyboardButton("📋 كشف أسعار"))

    customer_bot.send_message(
        uid,
        "**القائمة الرئيسية**\nأهلاً بك في متجر شركة الأهرام، اختر من القائمة بالأسفل:",
        reply_markup=kb,
        parse_mode="Markdown"
    )