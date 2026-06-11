import subprocess
import sys
import os
import time

root_dir = os.path.abspath(os.path.dirname(__file__))
env = os.environ.copy()
env["PYTHONPATH"] = root_dir

print("🚀 جاري إقلاع منظومة شركة الأهرام...")

try:
    print("🤖 بدء تشغيل بوت العملاء...")
    customer_process = subprocess.Popen([sys.executable, os.path.join("Customer_Bot", "main.py")], env=env)
    time.sleep(3)
    
    print("🛠️ بدء تشغيل بوت الإدارة...")
    admin_process = subprocess.Popen([sys.executable, os.path.join("Admin_bot", "admin_main.py")], env=env)

    print("\n✅ المنظومة تعمل الآن بكامل طاقتها! (اضغط Ctrl + C للإيقاف)\n")
    customer_process.wait()
    admin_process.wait()

except KeyboardInterrupt:
    print("\n🛑 جاري إيقاف المنظومة بأمان...")
    customer_process.terminate()
    admin_process.terminate()
    print("👋 تم إيقاف كافة البوتات.")
except Exception as e:
    print(f"🚨 حدث خطأ غير متوقع: {e}")