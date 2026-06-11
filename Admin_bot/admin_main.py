import telebot
from config import admin_bot, ADMIN_ID
from telebot import types
import datetime
from config import ADMIN_IDS

# 1. استيراد جميع الوظائف (Handlers) التي برمجناها سابقاً
# تأكد أن أسماء الملفات تطابق ما لديك في مجلد admin_handlers
import Admin_bot.admin_handlers.manage_users        # إدارة المستخدمين والتفعيل
import Admin_bot.admin_handlers.add_stock           # إضافة الكروت والمخزون
import Admin_bot.admin_handlers.complaints_manager  # إدارة الشكاوى والتعويضات
import Admin_bot.admin_handlers.settings            # إعدادات الدعم الفني (تليجرام)
import Admin_bot.admin_handlers.sales_report        # تقارير المبيعات
import Admin_bot.admin_handlers.generate_cards      # توليد كروت العملاء
import Admin_bot.admin_handlers.users_report        # توليد ملف العملاء
import Admin_bot.admin_handlers.manage_images       # إدارة صور الاقسام
import Admin_bot.admin_handlers.charge_wallet       # شحن رصيد للعميل
import Admin_bot.admin_handlers.Invoice_search      # البحث عن فاتورة
import Admin_bot.admin_handlers.edit_prices         # تعديل اسعار المستويات
import Admin_bot.admin_handlers.inventory_report    # تقرير المخزن كامل
import Admin_bot.admin_handlers.review_users        # ملف العملاء


# --- 2. لوحة التحكم الرئيسية للإدارة ---
@admin_bot.message_handler(commands=['start', 'menu'])
def admin_main_menu(message):
    uid = message.chat.id
    
    # 🌟 التعديل تم هنا: فحص ذكي للمشرفين (القائمة الثابتة + قاعدة البيانات)
    is_admin = False
    if str(uid) == str(ADMIN_ID) or str(uid) in ADMIN_IDS:
        is_admin = True
    elif db.admins.find_one({"_id": uid}):
        is_admin = True
        
    # إذا لم يكن مشرفاً، يتم طرده
    if not is_admin:
        return admin_bot.reply_to(message, "⚠️ عذراً، هذه اللوحة مخصصة لإدارة شركة الأهرام فقط.")

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # توزيع الأزرار بشكل منظم
    btn1 = types.KeyboardButton("📊 تقرير المبيعات")
    btn2 = types.KeyboardButton("📩 الشكاوي المعلقة")
    btn3 = types.KeyboardButton("📦 إضافة أكواد")
    btn4 = types.KeyboardButton("⚙️ تحكم العملاء")
    btn5 = types.KeyboardButton("⚙️ إعدادات الدعم")
    btn6 = types.KeyboardButton("💰 شحن رصيد")
    btn7 = types.KeyboardButton("💰 توليد كروت شحن")
    btn8 = types.KeyboardButton("📂 قائمة المشتركين")
    btn9 = types.KeyboardButton("🖼️ إدارة الصور")
    btn10 = types.KeyboardButton("🔍 البحث عن فاتورة")
    btn11 = types.KeyboardButton("🏷️ تعديل أسعار المنتجات")
    btn12 = types.KeyboardButton("📦 المخزون")
    btn13 = types.KeyboardButton("🛑 ضبط ليمت عميل")
    btn14 = types.KeyboardButton("⚙️ ترتيب واجهة الأقسام")
    btn15 = types.KeyboardButton("👥 مراجعة البيانات")
    

    kb.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10, btn11, btn12, btn13, btn14, btn15)
    
    welcome_text = (
        "👑 **مرحباً بك في لوحة تحكم مدير شركة الأهرام**\n"
        "━━━━━━━━━━━━━━━\n"
        "من هنا يمكنك متابعة المبيعات، حل مشاكل العملاء، وتحديث بيانات النظام بالكامل."
    )
    admin_bot.send_message(message.chat.id, welcome_text, reply_markup=kb, parse_mode="Markdown")

# --- 3. تشغيل البوت مع نظام حماية من التوقف ---
print("✅ [Admin Bot] تم تحميل جميع الملفات بنجاح.")
print("🚀 بوت الإدارة قيد التشغيل الآن...")


from config import admin_bot, users, stock, transactions, db
from telebot import types
# ==========================================
# 🛑 أمر الـ FRP السري لتصفير المنظومة 🛑
# ==========================================
@admin_bot.message_handler(commands=['frp'])
def frp_warning(msg):
    uid = msg.chat.id
    
    # 🔒 حماية تم إضافتها: المدير العام الأصلي فقط يمكنه عمل فورمات
    if str(uid) != str(ADMIN_ID):
        return admin_bot.reply_to(msg, "❌ عذراً، هذا الأمر الحساس لمالك المنظومة فقط ولا يسمح للمشرفين باستخدامه.")
    
    warning_text = (
        "⚠️ **تـحـذيـر خـطـيـر جـداً (Factory Reset WIPE)** ⚠️\n"
        "━━━━━━━━━━━━━━━\n"
        "أنت على وشك **مسح جميع البيانات** من المنظومة نهائياً!\n\n"
        "هذا الإجراء سيقوم بمسح:\n"
        "❌ كل العملاء (وأرصدتهم وحساباتهم).\n"
        "❌ كل المخزون (الكروت المتاحة والمباعة).\n"
        "❌ كل المبيعات (الفواتير والأرشيف).\n"
        "❌ كل الشكاوي المعلقة والمحلولة.\n"
        "❌ كل أكواد الشحن الآلي.\n\n"
        "إذا كنت متأكداً 100% أنك تريد تصفير المنظومة والبدء من الصفر، أرسل الجملة التالية حرفياً:\n\n"
        "`تصفير المنظومة الان`\n\n"
        "*(لإلغاء العملية، أرسل أي كلمة أخرى أو اضغط على أي زر)*"
    )
    
    res = admin_bot.send_message(uid, warning_text, parse_mode="Markdown")
    admin_bot.register_next_step_handler(res, frp_execute)

def frp_execute(msg):
    uid = msg.chat.id
    
    if msg.text == "تصفير المنظومة الان":
        admin_bot.send_message(uid, "⏳ جاري عمل Format للمنظومة بالكامل... يرجى الانتظار.")
        
        try:
            # 1. مسح جميع المجموعات (Collections) من قاعدة البيانات
            users.delete_many({})
            stock.delete_many({})
            transactions.delete_many({})
            db.complaints.delete_many({})
            db.wallet_codes.delete_many({})
            db.counters.delete_many({}) # تصفير عداد الفواتير
            
            # 2. إرسال رسالة النجاح
            success_msg = (
                "✅ **تم عمل FRP بنجاح!**\n"
                "المنظومة الآن 'نظيفة' تماماً ولا تحتوي على أي بيانات.\n\n"
                "أرسل `/start` لإعادة تهيئة البوت من جديد."
            )
            admin_bot.send_message(uid, success_msg, parse_mode="Markdown")
            
        except Exception as e:
            admin_bot.send_message(uid, f"🚨 حدث خطأ أثناء مسح قاعدة البيانات: {e}")
            
    else:
        admin_bot.send_message(uid, "🛡️ **تم إلغاء عملية التصفير.** بياناتك في أمان ولم يتم مسح أي شيء.", parse_mode="Markdown")


from config import admin_bot, db, ADMIN_ID
from telebot import types

# إنشاء جدول المشرفين في قاعدة البيانات
admins_collection = db.admins

# ==========================================
# 🔐 أمر إضافة مشرف جديد (للسوبر أدمن فقط)
# ==========================================
@admin_bot.message_handler(commands=['add'])
def add_admin_command(msg):
    uid = msg.chat.id
    
    # التحقق: هل أنت السوبر أدمن الأصلي؟
    if str(uid) != str(ADMIN_ID):
        return admin_bot.reply_to(msg, "❌ عذراً، هذا الأمر مخصص لمالك المنظومة فقط.")

    res = admin_bot.send_message(
        uid, 
        "➕ **إضافة مشرف جديد:**\n\nأرسل الآن الـ **ID الخاص بالمشرف** الجديد (أرقام فقط):", 
        parse_mode="Markdown"
    )
    admin_bot.register_next_step_handler(res, process_add_admin)
   
def process_add_admin(msg):
    uid = msg.chat.id
    try:
        new_admin_id = int(msg.text.strip())
        
        # التأكد من أنه ليس مضافاً مسبقاً
        exists = admins_collection.find_one({"_id": new_admin_id})
        if exists:
            return admin_bot.send_message(uid, "⚠️ هذا المشرف مضاف بالفعل في المنظومة.")

        # إضافة المشرف الجديد
        admins_collection.insert_one({
            "_id": new_admin_id,
            "added_by": uid,
            "date": datetime.datetime.now()
        })
        
        admin_bot.send_message(uid, f"✅ تم تعيين المستخدم `{new_admin_id}` كمشرف بنجاح!", parse_mode="Markdown")
        
        # إشعار للمشرف الجديد
        try:
            admin_bot.send_message(new_admin_id, "🎉 تهانينا! لقد تم تعيينك كمشرف في بوت إدارة شركة الأهرام.")
        except:
            pass # في حال لم يبدأ المشرف الجديد المحادثة مع البوت بعد

    except ValueError:
        admin_bot.send_message(uid, "❌ خطأ: يرجى إرسال الـ ID كأرقام فقط.")

if __name__ == "__main__":
    try:
        admin_bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"🚨 حدث خطأ مفاجئ في بوت الإدارة: {e}")