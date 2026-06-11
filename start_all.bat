@echo off
:: السطر السحري لدعم اللغة العربية في التيرمينال
chcp 65001 > nul
title Al-Ahram Bot System - المهندس لخدمات المحمول
color 0b

echo ===================================================
echo   WELCOME MUHAMMED ALI - شركة الأهرام للاتصالات
echo ===================================================
echo.

echo [1/2] جاري تفعيل البيئة الوهمية وتحديث المكتبات...
call .venv\Scripts\activate
python -m pip install -r requirements.txt

echo [2/2] جاري تشغيل النظام الموحد (الإدارة + العملاء)...
echo ---------------------------------------------------
set PYTHONIOENCODING=utf-8
python main.py

pause