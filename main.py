import threading
from keep_alive import keep_alive
from config import admin_bot, customer_bot

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

if __name__ == "__main__":
    # 1. تشغيل السيرفر الوهمي لإرضاء Render
    keep_alive()
    
    # 2. تشغيل بوت الإدارة في مسار مستقل
    t_admin = threading.Thread(target=run_admin_bot)
    t_admin.start()
    
    # 3. تشغيل بوت العميل في مسار مستقل
    t_customer = threading.Thread(target=run_customer_bot)
    t_customer.start()
    