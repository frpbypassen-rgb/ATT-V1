@echo off
:: السطر السحري لدعم اللغة العربية في التيرمينال
chcp 65001 > nul
title Al-Ahram Bot System - المهندس لخدمات المحمول (مُفعل التحديث التلقائي)
color 0b

:loop
cls
echo ===================================================
echo   WELCOME MUHAMMED ALI - شركة الأهرام للاتصالات
echo ===================================================
echo.

echo [1/3] جاري التحقق وجلب التحديثات الجديدة من GitHub...
git fetch origin main
git reset --hard origin/main

echo [2/3] جاري تفعيل البيئة الوهمية وتحديث المكتبات...
call .venv\Scripts\activate
python -m pip install -r requirements.txt

echo [3/3] جاري تشغيل النظام الموحد (الإدارة + العملاء)...
echo ---------------------------------------------------
set PYTHONIOENCODING=utf-8
python main.py

echo.
echo ⚠️ تم إيقاف البوت أو تم العثور على تحديثات جديدة.
echo 🔄 سيتم التحقق من التحديثات وإعادة التشغيل تلقائياً بعد 5 ثوانٍ...
timeout /t 5
goto loop