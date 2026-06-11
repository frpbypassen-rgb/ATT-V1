from keep_alive import keep_alive
from config import customer_bot

# استدعاء ملفات بوت العميل (Handlers) لتفعيلها في الذاكرة
import Customer_Bot.handlers.start_menu
import Customer_Bot.handlers.purchase_history
import Customer_Bot.handlers.shop
import Customer_Bot.handlers.balance
import Customer_Bot.handlers.complaints
import Customer_Bot.handlers.recharge
import Customer_Bot.handlers.cart
import Customer_Bot.handlers.can_recharge

print("✅ تم تحميل ملفات بوت العميل.")

if __name__ == "__main__":
    # تشغيل السيرفر الوهمي (لأجل Render)
    keep_alive()
    
    # تشغيل بوت العميل مباشرة في المسار الرئيسي
    print("🚀 بوت العملاء انطلق الآن...")
    customer_bot.infinity_polling(timeout=60, long_polling_timeout=5)