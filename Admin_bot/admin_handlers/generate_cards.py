import random
import string
from config import admin_bot, db
from telebot import types

# الإشارة إلى جدول الكروت في قاعدة البيانات
cards_collection = db.recharge_cards 

@admin_bot.message_handler(func=lambda m: m.text == "💰 توليد كروت شحن")
def start_card_generation(msg):
    text = "🔢 **كم عدد الكروت التي تود توليدها؟**\n(أرسل رقم فقط، مثال: 10)"
    res = admin_bot.send_message(msg.chat.id, text, parse_mode="Markdown")
    admin_bot.register_next_step_handler(res, get_card_value)

def get_card_value(msg):
    if not msg.text.isdigit():
        return admin_bot.send_message(msg.chat.id, "❌ خطأ: يرجى إرسال رقم صحيح.")
    
    count = int(msg.text)
    text = f"💵 **ما هي قيمة الشحن لكل كارت؟**\n(سيتم توليد {count} كارت، أرسل القيمة الآن)"
    res = admin_bot.send_message(msg.chat.id, text, parse_mode="Markdown")
    admin_bot.register_next_step_handler(res, process_generation, count)

def process_generation(msg, count):
    if not msg.text.isdigit():
        return admin_bot.send_message(msg.chat.id, "❌ خطأ: يرجى إرسال قيمة صحيحة.")
    
    value = float(msg.text)
    generated_cards = []

    for _ in range(count):
        # توليد كود عشوائي (مثال: AHRAM-XXXX-XXXX)
        code = "AHRAM-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        card_data = {
            "code": code,
            "value": value,
            "status": "active", # active تعني لم يستخدم بعد
            "used_by": None,
            "created_at": msg.date
        }
        cards_collection.insert_one(card_data)
        generated_cards.append(f"`{code}`")

    # إرسال الكروت للأدمن لنسخها وتوزيعها
    cards_list = "\n".join(generated_cards)
    response_text = (
        f"✅ **تم توليد {count} كارت بنجاح!**\n"
        f"💰 **قيمة الكارت الواحد:** {value} د.ل\n\n"
        f"📜 **الكروت الملحقة:**\n{cards_list}\n\n"
        "⚠️ قم بنسخها وتوزيعها على العملاء أو الوكلاء."
    )
    admin_bot.send_message(msg.chat.id, response_text, parse_mode="Markdown")
    