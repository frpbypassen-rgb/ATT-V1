import telebot
from pymongo import MongoClient
import sys

# ==========================================================
# 1. إعدادات التليجرام (Tokens) والسرعة (Threads)
# ==========================================================
CUSTOMER_TOKEN = '8769145956:AAEriAt4W-PmjNJdX93T_pbol9XahSQFP3g'
ADMIN_TOKEN = '8628847468:AAHyl2mg5ziZZyZzez8_5FE6ME1pzQLagyw'

# رفعنا num_threads لكي يرد البوت على 20 عميل في نفس اللحظة بدون تأخير
customer_bot = telebot.TeleBot(CUSTOMER_TOKEN, num_threads=20)
admin_bot = telebot.TeleBot(ADMIN_TOKEN, num_threads=20)

# ==========================================================
# 2. إعدادات قاعدة البيانات (Local vs Cloud)
# ==========================================================
LOCAL_URI = "mongodb://localhost:27017/"
CLOUD_URI = "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority"
USE_CLOUD = False 

try:
    uri = CLOUD_URI if USE_CLOUD else LOCAL_URI
    client = MongoClient(uri)
    client.server_info()
    db = client['AlAhram_DB']
    print(f"✅ [Database] تم الاتصال بنجاح. الوضع: {'☁️ سحابي' if USE_CLOUD else '💻 محلي'}")
except Exception as e:
    print(f"❌ [Error] فشل الاتصال بقاعدة البيانات: {e}")
    sys.exit(1)

# ==========================================================
# 3. تعريف الجداول المشتركة
# ==========================================================
users = db.users
stock = db.stock
settings = db.settings  # جدول حفظ إعدادات النظام (مثل رقم الواتساب)
transactions = db.transactions
complaints = db.complaints
recharge_cards = db.recharge_cards  # جدول كروت شحن الرصيد
complaints_db = db.complaints  # جدول الشكاوى
counters = db.counters  # جدول لتخزين الأرقام التسلسلية
admins = db.admins
cart_db = db.cart  # <--- أضف هذا السطر
invoices = db.invoices

# ==========================================================
# 4. صلاحيات الإدارة
# ==========================================================
ADMIN_ID = 1262656649 # ضع ID الخاص بك هنا
ADMIN_IDS = [
    "1262656649",  # الأيدي الخاص بك
    "5388738070",  # الأيدي الخاص بالمشرف الجديد (استبدله بالرقم الحقيقي)
]
import os # تأكد من وجود هذا الاستدعاء في الأعلى

# ==========================================================
# 5. إعدادات الصور (جديد)
# ==========================================================
# تعريف جدول الصور في قاعدة البيانات
db_images = db.section_images

# تعريف مجلد الصور (سيكون داخل ATT_V2/Customer_Bot/images/)
# لكي يعمل الكود، يجب أن تقوم بإنشاء مجلد images داخل Customer_Bot
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#IMAGES_FOLDER = os.path.join(BASE_DIR, 'Customer_Bot', 'images')
#os.makedirs(IMAGES_FOLDER, exist_ok=True) # إنشاء المجلد إذا لم يكن موجوداً
