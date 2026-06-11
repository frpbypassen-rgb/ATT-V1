from config import admin_bot, users
from telebot import types

# --- 1. بدء عملية البحث عن مستخدم ---
@admin_bot.message_handler(func=lambda m: m.text == "⚙️ تحكم العملاء")
def start_user_search(msg):
    admin_bot.clear_step_handler_by_chat_id(chat_id=msg.chat.id)
    res = admin_bot.send_message(
        msg.chat.id, 
        "🔍 **إدارة المستخدمين:**\nالرجاء إرسال **رقم الهاتف** أو **الـ ID** للبحث عنه:", 
        parse_mode="Markdown"
    )
    admin_bot.register_next_step_handler(res, search_user_logic)

# --- 2. محرك البحث الهجين وعرض لوحة التحكم ---
def search_user_logic(msg):
    raw_input = msg.text.strip()
    clean_phone = raw_input.replace("+", "").replace(" ", "")
    phone_no_zero = clean_phone[1:] if clean_phone.startswith("0") else clean_phone
    
    search_criteria = [
        {"phone": raw_input},                       
        {"phone": phone_no_zero},                   
        {"phone": f"0{phone_no_zero}"},             
        {"phone": f"+218{phone_no_zero}"},          
        {"phone": f"218{phone_no_zero}"}            
    ]

    if raw_input.isdigit():
        search_criteria.append({"_id": int(raw_input)})
        search_criteria.append({"_id": raw_input})
    
    user = users.find_one({"$or": search_criteria})
    
    if not user:
        return admin_bot.send_message(msg.chat.id, f"⚠️ **لم يتم العثور على مستخدم!**\nالإدخال: `{raw_input}` غير مسجل.", parse_mode="Markdown")
    
    uid = user.get("_id")
    name = user.get("name", "غير مسجل")
    phone = user.get("phone", "غير مسجل")
    balance = user.get("balance", 0.0)
    level = user.get("level", 1)
    status = user.get("status", "active")

    levels_map = {1: "عادي 🥉", 2: "موزع 🥈", 3: "جملة 🥇"}
    level_name = levels_map.get(level, "غير محدد")

    user_card = (
        f"👤 **ملف المستخدم:**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📝 **الاسم:** {name}\n"
        f"📞 **الهاتف:** `{phone}`\n"
        f"🆔 **ID:** `{uid}`\n"
        f"💰 **الرصيد:** `{balance:.2f}` د.ل\n"
        f"⭐ **المستوى:** {level_name}\n"
        f"🚦 **الحالة:** {'✅ نشط' if status == 'active' else '🚫 محظور'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    kb = types.InlineKeyboardMarkup(row_width=2)
    
    # الصف الأول: تعديل البيانات الأساسية
    btn_edit_name = types.InlineKeyboardButton("📝 تعديل الاسم", callback_data=f"edit_name_{uid}")
    btn_edit_balance = types.InlineKeyboardButton("💰 تعديل الرصيد", callback_data=f"set_balance_{uid}")
    
    # الصف الثاني: المستوى والشحن السريع
    btn_level = types.InlineKeyboardButton("⚙️ تغيير المستوى", callback_data=f"edit_level_{uid}")
    btn_recharge = types.InlineKeyboardButton("➕ شحن سريع", callback_data=f"recharge_from_manage_{uid}")
    
    # الصف الثالث: الحظر والتفعيل
    status_btn = "🚫 حظر" if status == "active" else "✅ تفعيل"
    status_val = "ban" if status == "active" else "active"
    btn_status = types.InlineKeyboardButton(status_btn, callback_data=f"set_status_{status_val}_{uid}")

    kb.add(btn_edit_name, btn_edit_balance)
    kb.add(btn_level, btn_recharge)
    kb.add(btn_status)

    admin_bot.send_message(msg.chat.id, user_card, reply_markup=kb, parse_mode="Markdown")

# --- 3. معالجة تعديل الاسم ---
@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("edit_name_"))
def edit_name_prompt(call):
    uid = call.data.split("_")[2]
    admin_bot.delete_message(call.message.chat.id, call.message.message_id)
    res = admin_bot.send_message(call.message.chat.id, "📝 **أرسل الاسم الجديد للعميل الآن:**", parse_mode="Markdown")
    admin_bot.register_next_step_handler(res, save_new_name, uid)

def save_new_name(msg, uid):
    new_name = msg.text.strip()
    try:
        users.update_one({"_id": int(uid)}, {"$set": {"name": new_name}})
    except:
        users.update_one({"_id": uid}, {"$set": {"name": new_name}})
    
    admin_bot.send_message(msg.chat.id, f"✅ تم تحديث اسم العميل بنجاح إلى: **{new_name}**", parse_mode="Markdown")

# --- 4. معالجة تعديل الرصيد (تغيير القيمة مباشرة) ---
@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("set_balance_"))
def edit_balance_prompt(call):
    uid = call.data.split("_")[2]
    admin_bot.delete_message(call.message.chat.id, call.message.message_id)
    res = admin_bot.send_message(call.message.chat.id, "💰 **أرسل قيمة الرصيد الجديد بالكامل:**\n*(سيتم استبدال الرصيد الحالي بالقيمة التي ستكتبها)*", parse_mode="Markdown")
    admin_bot.register_next_step_handler(res, save_new_balance, uid)

def save_new_balance(msg, uid):
    try:
        new_balance = float(msg.text.strip())
        try:
            users.update_one({"_id": int(uid)}, {"$set": {"balance": new_balance}})
        except:
            users.update_one({"_id": uid}, {"$set": {"balance": new_balance}})
        
        admin_bot.send_message(msg.chat.id, f"✅ تم تعديل الرصيد بنجاح. القيمة الحالية: **{new_balance:.2f}** د.ل", parse_mode="Markdown")
    except ValueError:
        admin_bot.send_message(msg.chat.id, "❌ خطأ: يرجى إرسال أرقام فقط لتعديل الرصيد.")

# --- 5. معالجة المستويات والحالة والشحن (الموجودة مسبقاً) ---
@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("edit_level_"))
def change_level_menu(call):
    uid = call.data.split("_")[2]
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("عادي 🥉", callback_data=f"save_level_{uid}_1"),
        types.InlineKeyboardButton("موزع 🥈", callback_data=f"save_level_{uid}_2"),
        types.InlineKeyboardButton("جملة 🥇", callback_data=f"save_level_{uid}_3")
    )
    admin_bot.edit_message_text("⚙️ اختر المستوى الجديد:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("save_level_"))
def save_level_logic(call):
    data = call.data.split("_")
    uid, new_level = data[2], int(data[3])
    try:
        users.update_one({"_id": int(uid)}, {"$set": {"level": new_level}})
    except:
        users.update_one({"_id": uid}, {"$set": {"level": new_level}})
    admin_bot.edit_message_text(f"✅ تم تغيير المستوى بنجاح.", call.message.chat.id, call.message.message_id)

@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("set_status_"))
def change_status_logic(call):
    _, _, status, uid = call.data.split("_")
    try:
        users.update_one({"_id": int(uid)}, {"$set": {"status": status}})
    except:
        users.update_one({"_id": uid}, {"$set": {"status": status}})
    admin_bot.edit_message_text(f"📝 تم تحديث حالة المستخدم إلى: {status}", call.message.chat.id, call.message.message_id)

@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("recharge_from_manage_"))
def recharge_shortcut(call):
    uid_str = call.data.split("_")[3]
    admin_bot.delete_message(call.message.chat.id, call.message.message_id)
    try:
        from Admin_bot.admin_handlers.charge_wallet import ask_for_amount_by_id
        ask_for_amount_by_id(call.message, uid_str)
    except Exception as e:
        admin_bot.send_message(call.message.chat.id, f"❌ خطأ الربط: {e}")