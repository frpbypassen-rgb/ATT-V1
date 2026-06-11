import os
import datetime
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper

def create_image_receipt(name, phone, user_id, amount, prev_balance, total_balance, op_date=None):
    """
    دالة توليد الإيصال المصور مع إصلاحات الوضوح ومكان التاريخ
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "assets", "receipt_template.jpg")
    font_path = os.path.join(base_dir, "assets", "Cairo-Bold.ttf") 
    
    # حل بديل في حال فقدان الخط لضمان عدم ظهور المربعات
    if not os.path.exists(font_path):
        font_path = "C:\\Windows\\Fonts\\arialbd.ttf" 

    output_dir = os.path.join(base_dir, "receipts_output")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%y%m%d%H%M%S')
    output_path = os.path.join(output_dir, f"Receipt_{user_id}_{timestamp}.jpg")

    try:
        img = Image.open(template_path)
        draw = ImageDraw.Draw(img)

        # أحجام الخطوط
        font_main = ImageFont.truetype(font_path, 34)
        font_date = ImageFont.truetype(font_path, 26)

        def format_arabic(text):
            if not text: return ""
            reshaped_text = arabic_reshaper.reshape(str(text).strip())
            return reshaped_text[::-1]

        # 1. رسم التاريخ: تم ضبطه ليكون داخل الشريط البرتقالي العلوي
        if op_date and isinstance(op_date, datetime.datetime):
            date_str = op_date.strftime("%Y-%m-%d   %I:%M %p")
        else:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d   %I:%M %p")

        draw.text((580, 245), date_str, font=font_date, fill=(255, 255, 255), anchor="mm")
        
        # إحداثيات النصوص (بناءً على مقاساتك المعتمدة)
        X_POS = 300  
        TEXT_COLOR = (30, 30, 30) # لون غامق جداً للوضوح
        
        # 2. بيانات العميل
        draw.text((X_POS, 565), format_arabic(name), font=font_main, fill=TEXT_COLOR, anchor="mm")
        draw.text((X_POS, 630), str(phone), font=font_main, fill=TEXT_COLOR, anchor="mm")
        draw.text((X_POS, 715), str(user_id), font=font_main, fill=TEXT_COLOR, anchor="mm")
        
        # 3. تفاصيل المبالغ
        currency = format_arabic("د.ل")
        amount_str = f"{amount:.2f}  {currency}"
        prev_str = f"{prev_balance:.2f}  {currency}"
        total_str = f"{total_balance:.2f}  {currency}"

        draw.text((X_POS, 845), amount_str, font=font_main, fill=TEXT_COLOR, anchor="mm")
        draw.text((X_POS, 915), prev_str, font=font_main, fill=TEXT_COLOR, anchor="mm")
        draw.text((X_POS, 975), total_str, font=font_main, fill=(243, 112, 33), anchor="mm") # برتقالي

        img.save(output_path, quality=100)
        return output_path
        
    except Exception as e:
        print(f"🚨 خطأ في توليد صورة الإيصال: {e}")
        return None