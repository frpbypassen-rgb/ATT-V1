import sys
import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

# ربط موقع العميل بقاعدة البيانات المشتركة
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_path)

try:
    from config import db, users, stock, transactions
except ImportError:
    print("🚨 خطأ: لم يتم العثور على ملف config.py")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = "AlAhram_Customer_Portal_2026_Secure"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('customer_logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        tg_id = request.form.get('tg_id', '').strip()
        password = request.form.get('password', '').strip()

        if not password.isdigit() or len(password) != 6:
            flash("كلمة المرور يجب أن تتكون من 6 أرقام فقط!", "danger")
            return redirect(url_for('login'))

        try: tg_id_int = int(tg_id)
        except: tg_id_int = tg_id

        user = users.find_one({
            "$or": [{"_id": tg_id_int}, {"_id": str(tg_id)}],
            "web_password": password
        })

        if user:
            session['customer_logged_in'] = True
            session['customer_id'] = user.get('_id')
            session['customer_name'] = user.get('name') or user.get('first_name') or 'عميلنا العزيز'
            return redirect(url_for('index'))
        else:
            flash("بيانات الدخول غير صحيحة! تأكد من رقم التليجرام وكلمة المرور.", "danger")

    return render_template('login.html')

@app.route('/')
def index():
    if not session.get('customer_logged_in'):
        return redirect(url_for('login'))
    
    user_id = session.get('customer_id')
    user = users.find_one({"_id": user_id})
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
        
    # جلب وتنسيق الرصيد
    balance = "{:.2f}".format(float(user.get('balance', 0)))
    
    # جلب آخر الفواتير والمشتريات
    user_trans = list(transactions.find({"user_id": {"$in": [user_id, str(user_id)]}}).sort("date", -1))
    
    total_spent = 0
    recent_orders = []
    seen_orders = set()
    
    for t in user_trans:
        oid = t.get('order_id')
        price = t.get('total_price', 0)
        total_spent += price
        
        if oid and oid not in seen_orders:
            seen_orders.add(oid)
            # إضافة آخر 5 طلبات فقط للعرض السريع في الرئيسية
            if len(recent_orders) < 5:
                d_obj = t.get('date')
                date_str = d_obj.strftime('%Y-%m-%d') if isinstance(d_obj, datetime.datetime) else "---"
                recent_orders.append({
                    "order_id": oid,
                    "date": date_str,
                    "price": "{:.2f}".format(float(price))
                })
                
    formatted_total = "{:.2f}".format(float(total_spent))

    return render_template('index.html', 
                           customer_name=session.get('customer_name'), 
                           balance=balance, 
                           total_spent=formatted_total,
                           recent_orders=recent_orders)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)