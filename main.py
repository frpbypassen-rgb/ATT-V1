import threading
from keep_alive import keep_alive
from config import admin_bot, customer_bot
from auto_updater import start_updater

# استدعاء ملفات الأوامر لتشغيلها في الذاكرة
import Admin_bot.admin_main
import Customer_Bot.handlers.shop  
import Customer_Bot.handlers.start_menu
import Customer_Bot.handlers.purchase_history
import Customer_Bot.handlers.shop
import Customer_Bot.handlers.balance
import Customer_Bot.handlers.complaints
import Customer_Bot.handlers.cart
import Customer_Bot.handlers.can_recharge
import Customer_Bot.handlers.recharge

def run_admin_bot():
    print("🚀 جاري تشغيل بوت الإدارة...")
    admin_bot.infinity_polling(timeout=10, long_polling_timeout=5)

def run_customer_bot():
    print("🚀 جاري تشغيل بوت العملاء...")
    customer_bot.infinity_polling(timeout=10, long_polling_timeout=5)

def run_admin_panel():
    try:
        print("🚀 جاري تشغيل لوحة الإدارة الويب (منفذ 5000)...")
        from Admin_Panel.app import app as admin_app
        admin_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"🚨 فشل تشغيل لوحة الإدارة الويب: {e}")

def run_customer_panel():
    try:
        print("🚀 جاري تشغيل بوابة العملاء الويب (منفذ 5001)...")
        from Customer_Panel.app import app as customer_app
        customer_app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
    except Exception as e:
        print(f"🚨 فشل تشغيل بوابة العملاء الويب: {e}")

if __name__ == "__main__":
    # 0. تشغيل فاحص التحديثات التلقائي
    start_updater(interval_seconds=30)

    # 1. تشغيل السيرفر الوهمي لإرضاء Render
    keep_alive()
    
    # 2. تشغيل بوت الإدارة في مسار مستقل
    t_admin = threading.Thread(target=run_admin_bot)
    t_admin.start()
    
    # 3. تشغيل بوت العميل في مسار مستقل
    t_customer = threading.Thread(target=run_customer_bot)
    t_customer.start()

    # 4. تشغيل لوحة الإدارة الويب في الخلفية
    t_admin_web = threading.Thread(target=run_admin_panel)
    t_admin_web.daemon = True
    t_admin_web.start()

    # 5. تشغيل بوابة العملاء الويب في الخلفية
    t_customer_web = threading.Thread(target=run_customer_panel)
    t_customer_web.daemon = True
    t_customer_web.start()


    