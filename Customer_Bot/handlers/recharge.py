import datetime
import os
from config import customer_bot, admin_bot, ADMIN_ID, users, db

# 🌟 استدعاء صانع الإيصالات المصورة
from receipt_generator import create_image_receipt

cards_collection = db.recharge_cards

def use_recharge_card(msg):
    uid = msg.chat.id
    code = msg.text.strip()
    
    print(f"🔄 محاولة شحن كود: {code} للعميل {uid}")
    card = cards_collection.find_one({"code": code, "status": "active"})

    if not card:
        return customer_bot.send_message(uid, "❌ عذراً، هذا الكود غير صحيح أو تم استخدامه مسبقاً.")

    card_value = float(card.get('value', 0.0))
    
    # جلب بيانات العميل لمعرفة الرصيد السابق للإيصال
    user_info = users.find_one({"_id": uid})
    prev_balance = float(user_info.get('balance', 0))
    new_total = prev_balance + card_value
    user_name = user_info.get('name', 'عميل الأهرام')
    user_phone = user_info.get('phone', '---')

    # 1. تحديث الرصيد
    users.update_one({"_id": uid}, {"$inc": {"balance": card_value}})

    # 2. تغيير حالة الكارت 
    cards_collection.update_one(
        {"code": code},
        {"$set": {"status": "used", "used_by": uid, "used_date": datetime.datetime.now()}}
    )

    # 3. إشعار الإدارة
    try:
        admin_msg = (
            f"🚨 **إشعار شحن كارت تعبئة** 🚨\n"
            f"👤 **العميل:** `{user_name}`\n"
            f"💰 **القيمة المشحونة:** `{card_value:.2f}` د.ل\n"
        )
        admin_bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    except: pass

    # 🌟 4. توليد وإرسال الإيصال المصور للعميل
    try:
        customer_bot.send_message(uid, "⏳ جاري إصدار الإيصال الإلكتروني...")
        
        image_path = create_image_receipt(
            name=user_name, phone=user_phone, user_id=uid, 
            amount=card_value, prev_balance=prev_balance, total_balance=new_total
        )
        
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                caption = f"✅ **تم شحن حسابك بنجاح!**\nإليك إيصال السداد الإلكتروني المعتمد."
                customer_bot.send_photo(uid, photo, caption=caption, parse_mode="Markdown")
            os.remove(image_path) # تنظيف الملف بعد الإرسال
        else:
            customer_bot.send_message(uid, f"✅ تم شحن حسابك بقيمة {card_value:.2f} د.ل بنجاح.")
            
    except Exception as e:
        print(f"🚨 فشل في إرسال الفاتورة المصورة: {e}")
        customer_bot.send_message(uid, f"✅ تم شحن حسابك بقيمة {card_value:.2f} د.ل بنجاح.")