import subprocess
import time
import os
import threading

def check_updates_loop(interval_seconds=30):
    print("🔄 تم تفعيل فاحص التحديثات التلقائي (يعمل كل {} ثانية)...".format(interval_seconds))
    while True:
        try:
            # fetch remote status
            subprocess.run(["git", "fetch"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            # get current local commit hash
            local_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
            
            # get remote upstream commit hash
            remote_hash = subprocess.check_output(["git", "rev-parse", "@{u}"]).decode().strip()
            
            if local_hash != remote_hash:
                print("\n===================================================")
                print("✨ [تحديث جديد] تم اكتشاف تعديلات جديدة على GitHub!")
                print("🔄 جاري إيقاف البوت لتنزيل التعديلات وإعادة التشغيل...")
                print("===================================================\n")
                
                # Sleep a moment to ensure output is printed
                time.sleep(2)
                
                # Exit the process. The batch file loop will pull the updates and restart the bot.
                os._exit(0)
                
        except subprocess.CalledProcessError:
            # Git command failed (e.g., temporary internet disconnect or no upstream configured yet)
            pass
        except Exception as e:
            # Any other exception
            print(f"⚠️ خطأ أثناء فحص التحديثات: {e}")
            
        time.sleep(interval_seconds)

def start_updater(interval_seconds=30):
    updater_thread = threading.Thread(target=check_updates_loop, args=(interval_seconds,), daemon=True)
    updater_thread.start()
