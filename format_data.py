import json

# 1. اسم ملف النسخة الاحتياطية القديم
old_file = 'AlAhram_DB.stock.json'
# 2. اسم الملف الجديد الذي سيتم إنتاجه
new_file = 'formatted_stock.json'

def transform_data():
    try:
        with open(old_file, 'r', encoding='utf-8') as f:
            old_data = json.load(f)

        formatted_list = []

        for item in old_data:
            new_item = {
                "_id": item.get("_id"),
                "category": item.get("category"),
                "product": item.get("name"), # تغيير name إلى product
                "price_1": item.get("price_1"),
                "price_2": item.get("price_2"),
                "price_3": item.get("price_3"),
                "code": item.get("code"),
                "serial": item.get("serial"),
                "pin": item.get("pin"),
                "sold": item.get("sold", False),
                "sold_to": item.get("sold_to", None), # إضافة sold_to إذا لم توجد
                "added_date": item.get("added_at") # تغيير added_at إلى added_date
            }
            formatted_list.append(new_item)

        # حفظ الملف الجديد بتنسيق JSON مرتب
        with open(new_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_list, f, ensure_ascii=False, indent=2)
            
        print(f"✅ تم التحويل بنجاح! الملف الجاهز هو: {new_file}")

    except Exception as e:
        print(f"🚨 حدث خطأ أثناء التحويل: {e}")

if __name__ == "__main__":
    transform_data()