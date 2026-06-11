from pymongo import MongoClient
import datetime

print("🔄 جاري الاتصال بقاعدة البيانات لتحديث الفواتير القديمة...")

# 1. الاتصال بقاعدة البيانات
client = MongoClient("mongodb://localhost:27017/")
db = client['AlAhram_DB']

transactions = db.transactions
stock = db.stock
invoices = db.invoices
counters = db.counters

# 2. جلب كل أرقام الفواتير القديمة
old_orders = transactions.find({"order_id": {"$not": {"$regex": "^ATT-"}}}).distinct("order_id")

if not old_orders:
    print("✅ لا توجد فواتير قديمة تحتاج إلى تحديث. قاعدة البيانات موحدة بالفعل!")
    exit()

print(f"📦 تم العثور على {len(old_orders)} فاتورة قديمة، جاري التحديث...")

updated_count = 0

# 3. المرور على الفواتير وتحديثها
for old_id in old_orders:
    sample_trans = transactions.find_one({"order_id": old_id})
    if not sample_trans:
        continue
        
    trans_date = sample_trans.get('date')
    user_id = sample_trans.get('user_id')
    
    # 🌟 الحل هنا: التأكد من نوع البيانات (إذا لم يكن تاريخاً حقيقياً، نستخدم تاريخ اليوم)
    if not isinstance(trans_date, datetime.datetime):
        trans_date = datetime.datetime.now()
    
    yymm_str = trans_date.strftime('%y%m')
    
    seq_doc = counters.find_one_and_update(
        {"_id": f"invoice_seq_{yymm_str}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    
    sequence_number = str(seq_doc["seq"]).zfill(3)
    new_invoice_id = f"ATT-{yymm_str}-{sequence_number}"
    
    print(f"🔄 تغيير: {old_id}  ⬅️  {new_invoice_id}")
    
    # تحديث الجداول
    transactions.update_many({"order_id": old_id}, {"$set": {"order_id": new_invoice_id}})
    stock.update_many({"order_id": old_id}, {"$set": {"order_id": new_invoice_id}})
    
    all_items = list(transactions.find({"order_id": new_invoice_id}))
    total_amount = sum(item.get('total_price', 0) for item in all_items)
    
    invoices.update_one(
        {"invoice_id": old_id},
        {"$set": {
            "invoice_id": new_invoice_id,
            "user_id": user_id,
            "total_amount": total_amount,
            "items_count": len(all_items),
            "date": trans_date
        }},
        upsert=True
    )
    
    updated_count += 1

print("━━━━━━━━━━━━━━━")
print(f"🎉 تمت العملية بنجاح! تم تحديث وتوحيد {updated_count} فاتورة إلى التنسيق الجديد.")