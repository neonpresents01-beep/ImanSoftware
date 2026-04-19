#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
سیستم حسابداری پارسه
نقطه ورود اصلی برنامه
"""

import sys
import os
import traceback
from datetime import datetime
from pathlib import Path

# اضافه کردن مسیرهای مورد نیاز به sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'ui'))
sys.path.insert(0, str(BASE_DIR / 'plugins'))
sys.path.insert(0, str(BASE_DIR / 'ai'))

from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QPen

from license_checker import LicenseChecker
from ui.main_window import MainWindow
from database import DatabaseManager


class SplashScreen(QSplashScreen):
    """صفحه نمایش شروع برنامه"""
    
    def __init__(self):
        # ایجاد یک pixmap برای اسپلش
        pixmap = QPixmap(500, 300)
        pixmap.fill(QColor("#1a1a2e"))
        
        super().__init__(pixmap)
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.message = "در حال بارگذاری..."
        
        # رسم اولیه
        self._draw_contents()
    
    def _draw_contents(self):
        """رسم محتوای اسپلش روی pixmap"""
        pixmap = self.pixmap()
        pixmap.fill(QColor("#1a1a2e"))
        
        painter = QPainter(pixmap)
        
        # عنوان اصلی
        painter.setPen(QColor("#e94560"))
        font = painter.font()
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(250, 120, "سیستم حسابداری پارسه")
        
        # زیرعنوان
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#eee"))
        painter.drawText(250, 160, "نسخه ۱.۰.۰")
        
        # خط جداکننده
        painter.setPen(QPen(QColor("#0f3460"), 1))
        painter.drawLine(100, 200, 400, 200)
        
        # پیام وضعیت
        painter.setPen(QColor("#4CAF50"))
        painter.drawText(250, 240, self.message)
        
        # لوگو یا متن پایین
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor("#666"))
        painter.drawText(250, 280, "🧠 ImanAI Core v6.2")
        
        painter.end()
        self.setPixmap(pixmap)
    
    def showMessage(self, message, *args, **kwargs):
        """نمایش پیام روی اسپلش"""
        self.message = message
        self._draw_contents()
        super().showMessage(message, *args, **kwargs)


def setup_environment():
    """راه‌اندازی محیط برنامه"""
    import logging
    
    # ایجاد پوشه‌های مورد نیاز
    required_dirs = [
        BASE_DIR / 'plugins',
        BASE_DIR / 'plugins' / 'official_plugins',
        BASE_DIR / 'plugins' / 'third_party',
        BASE_DIR / 'backups',
        BASE_DIR / 'logs',
        BASE_DIR / 'ai' / 'models',
        BASE_DIR / 'ai' / 'training_data',
    ]
    
    for dir_path in required_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # تنظیم فایل لاگ
    log_file = BASE_DIR / 'logs' / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def check_dependencies():
    """بررسی پیش‌نیازهای برنامه"""
    missing_deps = []
    
    try:
        import PyQt5
    except ImportError:
        missing_deps.append("PyQt5")
    
    try:
        import cryptography
    except ImportError:
        print("⚠️ cryptography نصب نیست - اعتبارسنجی امضای پلاگین غیرفعال")
    
    try:
        import sqlite3
    except ImportError:
        missing_deps.append("sqlite3")
    
    if missing_deps:
        error_msg = f"""
        <h3>❌ پیش‌نیازهای زیر نصب نیستند:</h3>
        <p>{', '.join(missing_deps)}</p>
        <hr>
        <p>لطفاً دستور زیر را اجرا کنید:</p>
        <pre>pip install {' '.join(missing_deps)}</pre>
        """
        
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        
        msg = QMessageBox()
        msg.setWindowTitle("خطای پیش‌نیاز")
        msg.setIcon(QMessageBox.Critical)
        msg.setTextFormat(1)
        msg.setText(error_msg)
        msg.exec_()
        
        return False
    
    return True


def show_license_error(license_result):
    """نمایش خطای لایسنس"""
    error_msg = f"""
    <h3 style='color: #e74c3c;'>❌ خطای لایسنس</h3>
    <p><b>{license_result.get('message', 'خطای نامشخص')}</b></p>
    <hr>
    <p><b>🖥️ HWID سیستم شما:</b></p>
    <p style='font-family: monospace; background: #f0f0f0; padding: 10px; border-radius: 5px;'>
    {license_result.get('hwid', 'N/A')}
    </p>
    <hr>
    <p style='color: #7f8c8d;'>
    📧 برای دریافت لایسنس با پشتیبانی تماس بگیرید
    </p>
    """
    
    msg = QMessageBox()
    msg.setWindowTitle("❌ خطای لایسنس")
    msg.setIcon(QMessageBox.Critical)
    msg.setTextFormat(1)
    msg.setText(error_msg)
    
    # دکمه کپی HWID
    copy_btn = msg.addButton("📋 کپی HWID", QMessageBox.ActionRole)
    msg.addButton("خروج", QMessageBox.RejectRole)
    
    msg.exec_()
    
    if msg.clickedButton() == copy_btn:
        clipboard = QApplication.clipboard()
        clipboard.setText(license_result.get('hwid', ''))
        QMessageBox.information(None, "کپی شد", "✅ HWID در کلیپبورد کپی شد!")


def show_license_success(license_result):
    """نمایش پیام موفقیت لایسنس"""
    days_left = license_result.get('days_left', 0)
    modules = license_result.get('modules', [])
    
    # تعیین رنگ بر اساس روزهای باقیمانده
    if days_left <= 7:
        days_color = "#e74c3c"
        days_icon = "⚠️"
    elif days_left <= 30:
        days_color = "#f39c12"
        days_icon = "⚡"
    else:
        days_color = "#27ae60"
        days_icon = "✅"
    
    # ترجمه نام ماژول‌ها
    module_names = {
        'accounting': '📊 حسابداری',
        'inventory': '📦 انبارداری',
        'payroll': '💰 حقوق دستمزد',
        'reports': '📈 گزارشات پیشرفته'
    }
    
    modules_text = '\n'.join([f"  • {module_names.get(m, m)}" for m in modules])
    
    success_msg = f"""
    <h3 style='color: #27ae60;'>✅ لایسنس معتبر است</h3>
    <table style='width: 100%;'>
    <tr><td><b>👤 کاربر:</b></td><td>{license_result.get('customer', 'Unknown')}</td></tr>
    <tr><td><b>🆔 شناسه:</b></td><td>{license_result.get('license_id', 'N/A')}</td></tr>
    <tr><td><b>📅 تاریخ انقضا:</b></td><td>{license_result.get('expire_date', 'N/A')}</td></tr>
    <tr><td><b style='color: {days_color};'>{days_icon} روزهای باقیمانده:</b></td>
        <td style='color: {days_color}; font-weight: bold;'>{days_left} روز</td></tr>
    </table>
    <hr>
    <p><b>📦 ماژول‌های فعال:</b></p>
    <p style='background: #f8f9fa; padding: 10px; border-radius: 5px;'>
    {modules_text}
    </p>
    <hr>
    <p style='color: #7f8c8d;'>🚀 در حال بارگذاری برنامه...</p>
    """
    
    msg = QMessageBox()
    msg.setWindowTitle("✅ خوش آمدید")
    msg.setIcon(QMessageBox.Information)
    msg.setTextFormat(1)
    msg.setText(success_msg)
    msg.setStandardButtons(QMessageBox.Ok)
    
    # نمایش خودکار بعد از ۳ ثانیه
    QTimer.singleShot(3000, msg.accept)
    msg.exec_()


def load_stylesheet(app):
    """بارگذاری فایل استایل"""
    style_file = BASE_DIR / "styles.qss"
    
    if style_file.exists():
        try:
            with open(style_file, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            return True
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری styles.qss: {e}")
    
    # استایل پیش‌فرض
    default_style = """
    QMainWindow { background-color: #f5f6fa; }
    QWidget { font-family: "Tahoma", "Segoe UI", sans-serif; font-size: 10pt; color: #2C3E50; }
    QPushButton {
        background-color: #273c75;
        color: white;
        border: none;
        padding: 8px 15px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #192a56; }
    QTableWidget {
        gridline-color: #dcdde1;
        selection-background-color: #273c75;
        border: 1px solid #dcdde1;
    }
    QHeaderView::section {
        background-color: #f5f6fa;
        padding: 8px;
        font-weight: bold;
    }
    QLineEdit, QSpinBox, QComboBox {
        border: 1px solid #dcdde1;
        border-radius: 4px;
        padding: 6px;
    }
    QStatusBar {
        background-color: #273c75;
        color: white;
    }
    """
    app.setStyleSheet(default_style)
    return False


def main():
    """تابع اصلی برنامه"""
    logger = setup_environment()
    logger.info("=" * 60)
    logger.info("سیستم حسابداری پارسه - شروع اجرا")
    logger.info(f"زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # ایجاد QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("سیستم حسابداری پارسه")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ImanAI")
    
    # تنظیم فونت فارسی
    font = QFont("Tahoma", 9)
    app.setFont(font)
    
    # نمایش اسپلش
    splash = SplashScreen()
    splash.show()
    splash.showMessage("🔍 بررسی پیش‌نیازها...")
    app.processEvents()
    
    # بررسی پیش‌نیازها
    if not check_dependencies():
        logger.error("پیش‌نیازها ناقص هستند")
        sys.exit(1)
    
    splash.showMessage("🎨 بارگذاری استایل...")
    app.processEvents()
    
    # بارگذاری استایل
    load_stylesheet(app)
    
    splash.showMessage("🗄️ راه‌اندازی پایگاه داده...")
    app.processEvents()
    
    # راه‌اندازی دیتابیس
    try:
        DatabaseManager.init_db()
        logger.info("پایگاه داده با موفقیت راه‌اندازی شد")
    except Exception as e:
        logger.error(f"خطا در راه‌اندازی پایگاه داده: {e}")
        QMessageBox.critical(None, "خطا", f"خطا در راه‌اندازی پایگاه داده:\n{str(e)}")
        sys.exit(1)
    
    splash.showMessage("🔑 بررسی لایسنس...")
    app.processEvents()
    
    # بررسی لایسنس
    checker = LicenseChecker()
    
    try:
        license_result = checker.check_license()
        logger.info(f"نتیجه بررسی لایسنس: {license_result.get('valid', False)}")
    except Exception as e:
        logger.error(f"خطا در بررسی لایسنس: {e}")
        license_result = {
            "valid": False,
            "hwid": checker.get_hwid(),
            "message": f"خطا در بررسی لایسنس: {str(e)}"
        }
    
    splash.close()
    
    # اگر لایسنس نامعتبر است
    if not license_result.get('valid', False):
        logger.warning(f"لایسنس نامعتبر: {license_result.get('message')}")
        show_license_error(license_result)
        sys.exit(1)
    
    # نمایش پیام موفقیت لایسنس
    show_license_success(license_result)
    logger.info(f"لایسنس معتبر - کاربر: {license_result.get('customer')}")
    
    # راه‌اندازی پنجره اصلی
    try:
        logger.info("در حال راه‌اندازی پنجره اصلی...")
        window = MainWindow(license_result)
        
        # تنظیم آیکون (اگر وجود داشته باشد)
        icon_path = BASE_DIR / "icon.png"
        if icon_path.exists():
            window.setWindowIcon(QIcon(str(icon_path)))
        
        window.show()
        logger.info("پنجره اصلی با موفقیت نمایش داده شد")
        
    except Exception as e:
        logger.error(f"خطا در راه‌اندازی پنجره اصلی: {e}")
        logger.error(traceback.format_exc())
        
        error_msg = f"""
        <h3>❌ خطا در راه‌اندازی برنامه</h3>
        <p>{str(e)}</p>
        <hr>
        <p>لطفاً لاگ فایل را بررسی کنید.</p>
        """
        
        QMessageBox.critical(None, "خطای بحرانی", error_msg)
        sys.exit(1)
    
    # اجرای حلقه اصلی
    exit_code = app.exec_()
    
    logger.info(f"برنامه بسته شد - کد خروج: {exit_code}")
    logger.info("=" * 60)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
