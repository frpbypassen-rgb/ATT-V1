from config import customer_bot, users, stock, transactions, db, admin_bot, ADMIN_ID, cart_db
from telebot import types
import datetime
import re
import threading

# تعريف المجموعات (Collections)
db_images = db.section_images
cat_config = db.categories_config  # حفظ ترتيب الأقسام

# ==========================================
# دوال مساعدة عامة
# ==========================================

# 1. استخراج الأرقام من النصوص للترتيب (مثل 13, 26, 50)
def extract_number(name):
    numbers = re.findall(r'\d+', name)
    return int(numbers[0]) if numbers else 0

# 2. دالة الأسعار اللحظية (3 مستويات) باستخدام البحث المرن
def get_live_price(user_id, product_data):
    user = users.find_one({"_id": {"$in": [user_id, str(user_id)]}})
    level = int(user.get("level", 1)) if user else 1 
    
    if level >= 3:
        return product_data.get("price_3", product_data.get("price_1", 0.0))
    elif level == 2:
        return product_data.get("price_2", product_data.get("price_1", 0.0))
    else:
        return product_data.get("price_1", 0.0)

# ==========================================
# 1. القائمة الرئيسية للأقسام للمشتريات
# ==========================================
@customer_bot.message_handler(func=lambda m: m.text == "🛒 شراء كروت")
def shop_visual_menu(msg):
    uid = msg.chat.id
    user = users.find_one({"_id": {"$in": [uid, str(uid)]}})
    
    if not user or user.get("status") != "active":
        return customer_bot.send_message(uid, "⚠️ عذراً، يجب تفعيل حسابك أولاً لتتمكن من الشراء.")

    # جلب الأقسام المتوفرة
    available_categories = stock.distinct("category", {"sold": False})
    if not available_categories:
        return customer_bot.send_message(uid, "📭 المتجر فارغ حالياً.")

    # جلب ترتيب الأقسام من الإعدادات
    configs = list(cat_config.find({}))
    order_map = {c['category']: c['order'] for c in configs}
    
    # فرز الأقسام بناءً على الترتيب المخصص (الافتراضي 999 للأقسام الجديدة)
    available_categories.sort(key=lambda x: order_map.get(x, 999))

    customer_bot.send_message(uid, "📸 **متجر الأهرام - تفضل باختيار القسم:**", parse_mode="Markdown")

    db_images_list = list(db_images.find({}))
    images_dict = {img['category']: img['file_id'] for img in db_images_list if 'file_id' in img}

    kb_fallback = types.InlineKeyboardMarkup(row_width=2)
    has_images = False

    for cat in available_categories:
        callback_val = f"m_cat_{cat}"
        if cat in images_dict:
            try:
                kb_cat = types.InlineKeyboardMarkup()
                kb_cat.add(types.InlineKeyboardButton(f"🔗 دخول قسم {cat}", callback_data=callback_val))
                customer_bot.send_photo(uid, images_dict[cat], caption=f"✨ **قسم: {cat}**", reply_markup=kb_cat, parse_mode="Markdown")
                has_images = True
            except:
                kb_fallback.add(types.InlineKeyboardButton(f"📂 {cat}", callback_data=callback_val))
        else:
            kb_fallback.add(types.InlineKeyboardButton(f"📂 {cat}", callback_data=callback_val))

    if len(kb_fallback.keyboard) > 0:
        text = "🔽 **أقسام إضافية:**" if has_images else "🔗 **الأقسام المتوفرة:**"
        customer_bot.send_message(uid, text, reply_markup=kb_fallback, parse_mode="Markdown")

# ==========================================
# 2. عرض المنتجات (مرتبة رقمياً 13, 26...)
# ==========================================
@customer_bot.callback_query_handler(func=lambda call: call.data.startswith("m_cat_"))
def view_subcategories(call):
    category_name = call.data.replace("m_cat_", "")
    available_subs = stock.distinct("product", {"category": category_name, "sold": False})
    
    if not available_subs:
        return customer_bot.answer_callback_query(call.id, "❌ القسم فارغ حالياً.", show_alert=True)

    # ترتيب الكروت رقمياً (13، 26، 38، 50...)
    available_subs.sort(key=extract_number)

    kb = types.InlineKeyboardMarkup(row_width=2)
    for sub in available_subs:
        kb.add(types.InlineKeyboardButton(sub, callback_data=f"v_sub_{sub}"))
    
    kb.add(types.InlineKeyboardButton("⬅️ رجوع للأقسام", callback_data="back_to_shop"))
    
    text = f"📦 **منتجات {category_name}:**\nاختر الكارت المطلوب:"
    try:
        customer_bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
    except:
        customer_bot.send_message(call.message.chat.id, text, reply_markup=kb, parse_mode="Markdown")

@customer_bot.callback_query_handler(func=lambda call: call.data == "back_to_shop")
def back_to_shop_callback(call):
    try: 
        customer_bot.delete_message(call.message.chat.id, call.message.message_id)
    except: 
        pass
    shop_visual_menu(call.message)

# ==========================================
# 3. طلب الكمية من العميل للإضافة للسلة
# ==========================================
@customer_bot.callback_query_handler(func=lambda call: call.data.startswith("v_sub_"))
def ask_quantity(call):
    uid = call.message.chat.id
    sub_name = call.data.replace("v_sub_", "")
    sample = stock.find_one({"product": sub_name, "sold": False})
    
    if not sample:
        return customer_bot.answer_callback_query(call.id, "❌ نفذت الكمية!", show_alert=True)

    price = get_live_price(uid, sample)
    qty_available = stock.count_documents({"product": sub_name, "sold": False})
    
    text = (
        f"💎 **المنتج:** {sub_name}\n"
        f"💰 **السعر:** `{price:.2f}` د.ل\n"
        f"🔢 **المتوفر:** `{qty_available}`\n\n"
        "✍️ **أرسل الكمية المطلوبة الآن (أرقام فقط):**"
    )
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ تراجع ورجوع للأقسام", callback_data="cancel_qty_step"))
    
    customer_bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
    customer_bot.answer_callback_query(call.id)
    
    customer_bot.register_next_step_handler(call.message, process_final_purchase, sub_name, price, qty_available, call.message.message_id)

@customer_bot.callback_query_handler(func=lambda call: call.data == "cancel_qty_step")
def cancel_quantity_prompt(call):
    uid = call.message.chat.id
    customer_bot.clear_step_handler_by_chat_id(uid) # تفريغ الذاكرة من انتظار الرقم
    
    try:
        customer_bot.delete_message(uid, call.message.message_id)
    except:
        pass
        
    shop_visual_menu(call.message)
    customer_bot.answer_callback_query(call.id, "تم التراجع عن إضافة المنتج.")

# ==========================================
# 4. معالجة الإضافة للسلة 
# ==========================================
def process_final_purchase(msg, sub_name, price, max_available, prompt_msg_id=None):
    uid = msg.chat.id
    
    try:
        customer_bot.delete_message(uid, msg.message_id)
        if prompt_msg_id:
            customer_bot.delete_message(uid, prompt_msg_id)
    except:
        pass

    try:
        qty = int(msg.text.strip())
    except:
        err = customer_bot.send_message(uid, "❌ خطأ: يرجى إرسال أرقام فقط.")
        threading.Timer(3.0, lambda: customer_bot.delete_message(uid, err.message_id)).start()
        return shop_visual_menu(msg)

    if qty <= 0 or qty > max_available:
        err = customer_bot.send_message(uid, f"❌ الكمية غير متاحة. المتاح {max_available} فقط.")
        threading.Timer(3.0, lambda: customer_bot.delete_message(uid, err.message_id)).start()
        return shop_visual_menu(msg)

    total_price = qty * price
    
    cart_item = {
        "user_id": uid,
        "product": sub_name,
        "qty": qty,
        "total_price": float(total_price)
    }
    cart_db.insert_one(cart_item)
    
    success_msg = f"✅ **تم إضافة المنتج للسلة بنجاح!**\nالمنتج: {sub_name}\nالكمية: {qty}"
    temp_msg = customer_bot.send_message(uid, success_msg, parse_mode="Markdown")
    
    def delete_temp_message():
        try:
            customer_bot.delete_message(uid, temp_msg.message_id)
        except:
            pass
            
    threading.Timer(3.0, delete_temp_message).start()
    shop_visual_menu(msg)

# ==========================================
# 5. عرض كشف الأسعار السريع (منسق ومرتب)
# ==========================================
@customer_bot.message_handler(func=lambda m: m.text == "📋 كشف أسعار")
def show_price_list(msg):
    uid = msg.chat.id
    user = users.find_one({"_id": {"$in": [uid, str(uid)]}})
    level = int(user.get("level", 1)) if user else 1
    
    status_msg = customer_bot.send_message(uid, "⏳ جاري تحضير قائمة الأسعار المخصصة لك...")

    try:
        pipeline = [
            {"$match": {"sold": False}},
            {"$group": {
                "_id": "$product",
                "category": {"$first": "$category"},
                "price_1": {"$first": "$price_1"},
                "price_2": {"$first": "$price_2"},
                "price_3": {"$first": "$price_3"}
            }}
        ]
        products = list(stock.aggregate(pipeline))
        
        if not products:
            return customer_bot.edit_message_text("❌ عذراً، لا توجد منتجات متاحة في المتجر حالياً.", uid, status_msg.message_id)

        categorized_products = {}
        for p in products:
            cat_name = p.get("category", "منتجات أخرى")
            if cat_name not in categorized_products:
                categorized_products[cat_name] = []
            categorized_products[cat_name].append(p)

        # ترتيب الأقسام نفسها كما في المتجر
        configs = list(cat_config.find({}))
        order_map = {c['category']: c['order'] for c in configs}
        
        sorted_cats = sorted(categorized_products.keys(), key=lambda x: order_map.get(x, 999))

        text = "📋 **قائمة أسعار المنتجات:**\n\n"
        
        for cat in sorted_cats:
            prods = categorized_products[cat]
            text += f"📦 **قسم: {cat}**\n━━━━━━━━━━━━━━━\n"
            
            # ترتيب المنتجات بالرقم 13، 26 الخ
            prods.sort(key=lambda x: extract_number(x['_id']))
            
            for p in prods:
                if level >= 3:
                    price = p.get('price_3', p.get('price_1', 0.0))
                elif level == 2:
                    price = p.get('price_2', p.get('price_1', 0.0))
                else:
                    price = p.get('price_1', 0.0)
                    
                text += f"🔹 {p['_id']} ⟵ `{price:.2f}` د.ل\n"
            
            text += "\n" 
            
        text += "💡 *تُخصم القيمة تلقائياً من رصيدك عند إتمام عملية الشراء.*"
        
        customer_bot.edit_message_text(text, uid, status_msg.message_id, parse_mode="Markdown")
        
    except Exception as e:
        print(f"🚨 خطأ في استخراج قائمة الأسعار: {e}")
        customer_bot.edit_message_text("❌ حدث خطأ أثناء جلب الأسعار، يرجى المحاولة لاحقاً.", uid, status_msg.message_id)

# ==========================================
# 6. إدارة "ترتيب الأقسام" (خاص بالمدير/المشرفين)
# ==========================================
@admin_bot.message_handler(func=lambda m: m.text == "⚙️ ترتيب واجهة الأقسام")
def admin_start_reorder(msg):
    show_admin_category_list(msg.chat.id)

def show_admin_category_list(chat_id, message_id=None):
    categories = stock.distinct("category")
    if not categories:
        return admin_bot.send_message(chat_id, "❌ لا توجد أقسام في المخزن حالياً.")

    configs = list(cat_config.find({}))
    order_map = {c['category']: c['order'] for c in configs}
    categories.sort(key=lambda x: order_map.get(x, 999))

    kb = types.InlineKeyboardMarkup(row_width=1)
    for cat in categories:
        current_order = order_map.get(cat, "⚠️")
        kb.add(types.InlineKeyboardButton(f"[{current_order}] - {cat}", callback_data=f"reorder_cat_{cat}"))
    
    kb.add(types.InlineKeyboardButton("✅ إنهاء الترتيب والرجوع", callback_data="admin_finish_reorder"))

    text = "⚙️ **لوحة ترتيب الأقسام:**\nاضغط على القسم الذي تريد تغيير مكانه في الواجهة:"
    
    if message_id:
        admin_bot.edit_message_text(text, chat_id, message_id, reply_markup=kb, parse_mode="Markdown")
    else:
        admin_bot.send_message(chat_id, text, reply_markup=kb, parse_mode="Markdown")

@admin_bot.callback_query_handler(func=lambda call: call.data.startswith("reorder_cat_"))
def admin_ask_new_order(call):
    cat_name = call.data.replace("reorder_cat_", "")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="admin_cancel_reorder"))
    
    res = admin_bot.edit_message_text(
        f"🔢 القسم المحدد: **{cat_name}**\n\nأرسل الآن رقم الترتيب الجديد (مثلاً: 1 للظهور في البداية):",
        call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="Markdown"
    )
    admin_bot.register_next_step_handler(res, process_new_category_order, cat_name, call.message.message_id)

def process_new_category_order(msg, cat_name, original_msg_id):
    chat_id = msg.chat.id
    try:
        admin_bot.delete_message(chat_id, msg.message_id) # تنظيف الشات من الرقم
        
        new_order = int(msg.text.strip())
        cat_config.update_one(
            {"category": cat_name},
            {"$set": {"order": new_order}},
            upsert=True
        )
        show_admin_category_list(chat_id, original_msg_id)
    except ValueError:
        admin_bot.send_message(chat_id, "❌ خطأ: يرجى إدخال أرقام فقط.")
        show_admin_category_list(chat_id)

@admin_bot.callback_query_handler(func=lambda call: call.data in ["admin_cancel_reorder", "admin_finish_reorder"])
def admin_finish_reorder(call):
    admin_bot.answer_callback_query(call.id, "تم حفظ الترتيب ✅")
    try:
        admin_bot.edit_message_text("✅ تم اعتماد الترتيب الجديد في واجهة المتجر.", call.message.chat.id, call.message.message_id)
    except:
        pass