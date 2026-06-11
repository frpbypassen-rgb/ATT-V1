# fix_db.py
from config import stock  # نستدعي مجموعة المخزن من إعداداتك الحالية
import time

def fix_database_codes():
    print("⏳ جاري الاتصال بقاعدة البيانات وفحص الأكواد...")
    
    # جلب جميع الكروت الموجودة في المخزن
    cards = stock.find({})
    updated_count = 0
    scanned_count = 0

    for card in cards:
        scanned_count += 1
        
        # 🌟 التعديل هنا: جلبنا حقل category بدلاً من product
        category_name = str(card.get('category', '')).strip()
        code = str(card.get('code', '')).strip()

        # تخطي القيم الفارغة أو غير الموجودة
        if not code or code == 'nan' or code == 'None':
            continue

        # إزالة أي فواصل عشرية (.0) لو تم حفظها بالخطأ سابقاً
        if code.endswith('.0'):
            code = code[:-2]

        new_code = code

        # تطبيق قواعد عدد الأرقام والأصفار بناءً على اسم القسم (إنجليزي أو عربي)
        if 'Vodafone' in category_name or 'فودافون' in category_name:
            new_code = code.zfill(16)
            
        elif 'Orange' in category_name or 'اورانج' in category_name or 'أورانج' in category_name:
            new_code = code.zfill(16)
            
        elif 'Etsalat' in category_name or 'اتصالات' in category_name:
            new_code = code.zfill(15)

        # إذا اكتشف السكريبت أن الكود يحتاج للتصحيح، يقوم بتحديثه في قاعدة البيانات
        if new_code != code:
            stock.update_one(
                {"_id": card["_id"]},
                {"$set": {"code": new_code}}
            )
            updated_count += 1

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🔍 تم فحص: {scanned_count} كارت.")
    print(f"✅ تم تصحيح وإضافة الأصفار لـ: {updated_count} كارت.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    fix_database_codes()