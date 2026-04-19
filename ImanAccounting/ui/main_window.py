from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
import sys
import os

from ui.accounting_widget import AccountingWidget
from ui.inventory_widget import InventoryWidget
from ui.payroll_widget import PayrollWidget
from ui.reports_widget import ReportsWidget
from ui.plugin_manager_widget import PluginManagerWidget
from database import DatabaseManager
from plugins import PluginManager


class MainWindow(QMainWindow):
    def __init__(self, license_info):
        super().__init__()
        self.license_info = license_info
        
        # راه‌اندازی Plugin Manager
        print("🔌 در حال بارگذاری پلاگین‌ها...")
        self.plugin_manager = PluginManager()
        loaded_plugins = self.plugin_manager.get_all_plugins()
        print(f"✅ {len(loaded_plugins)} پلاگین بارگذاری شد")
        
        # تنظیمات پنجره
        self.setWindowTitle(f"سیستم حسابداری پارسه | نسخه حرفه‌ای | کاربر: {license_info.get('customer', '')}")
        self.setGeometry(100, 50, 1400, 800)
        
        # راه‌اندازی پایگاه داده
        DatabaseManager.init_db()
        
        # تنظیم استایل
        self.setStyleSheet(self.get_stylesheet())
        
        # ایجاد رابط کاربری
        self.init_ui()
        
        # نمایش اطلاعات لایسنس در نوار وضعیت
        self.update_status_bar()
    
    def get_stylesheet(self):
        """استایل پایه (در صورت نبود فایل qss)"""
        return """
            QMainWindow {
                background-color: #f5f6fa;
            }
            
            QTabWidget::pane {
                border: 1px solid #dcdde1;
                background-color: white;
                border-radius: 5px;
            }
            
            QTabBar::tab {
                background-color: #f5f6fa;
                color: #2f3640;
                padding: 10px 25px;
                margin-right: 2px;
                font-size: 13px;
                font-weight: bold;
            }
            
            QTabBar::tab:selected {
                background-color: white;
                color: #273c75;
                border-bottom: 3px solid #273c75;
            }
            
            QTabBar::tab:hover {
                background-color: #dcdde1;
            }
            
            QPushButton {
                background-color: #273c75;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            
            QPushButton:hover {
                background-color: #192a56;
            }
            
            QPushButton#deleteBtn {
                background-color: #c23616;
            }
            
            QPushButton#deleteBtn:hover {
                background-color: #e84118;
            }
            
            QPushButton#successBtn {
                background-color: #4cd137;
            }
            
            QTableWidget {
                gridline-color: #dcdde1;
                selection-background-color: #273c75;
                selection-color: white;
                border: 1px solid #dcdde1;
                border-radius: 4px;
            }
            
            QHeaderView::section {
                background-color: #f5f6fa;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #dcdde1;
                font-weight: bold;
                color: #2f3640;
            }
            
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {
                border: 1px solid #dcdde1;
                border-radius: 4px;
                padding: 6px;
                background-color: white;
            }
            
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #273c75;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dcdde1;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #273c75;
            }
            
            QLabel#titleLabel {
                font-size: 16px;
                font-weight: bold;
                color: #273c75;
                padding: 10px;
            }
            
            QMenuBar {
                background-color: white;
                border-bottom: 1px solid #dcdde1;
            }
            
            QMenuBar::item {
                padding: 8px 15px;
                background-color: transparent;
            }
            
            QMenuBar::item:selected {
                background-color: #273c75;
                color: white;
            }
            
            QStatusBar {
                background-color: #273c75;
                color: white;
                font-weight: bold;
            }
        """
    
    def init_ui(self):
        """راه‌اندازی رابط کاربری"""
        # منوی اصلی
        self.create_menu_bar()
        
        # ویجت مرکزی
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # هدر
        header = self.create_header()
        main_layout.addWidget(header)
        
        # تب‌ها
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # افزودن تب‌ها بر اساس لایسنس
        available_modules = self.license_info.get('modules', [])
        
        # تب حسابداری
        if 'accounting' in available_modules:
            self.accounting_widget = AccountingWidget()
            self.tab_widget.addTab(self.accounting_widget, "📊 حسابداری")
        
        # تب انبارداری
        if 'inventory' in available_modules:
            self.inventory_widget = InventoryWidget()
            self.tab_widget.addTab(self.inventory_widget, "📦 انبارداری")
        
        # تب حقوق دستمزد
        if 'payroll' in available_modules:
            self.payroll_widget = PayrollWidget()
            self.tab_widget.addTab(self.payroll_widget, "💰 حقوق دستمزد")
        
        # تب گزارشات (همیشه فعال)
        self.reports_widget = ReportsWidget()
        self.tab_widget.addTab(self.reports_widget, "📈 گزارشات")
        
        # ========== تب‌های پلاگین ==========
        self.add_plugin_tabs()
        
        # ========== تب مدیریت پلاگین ==========
        self.plugin_manager_widget = PluginManagerWidget()
        self.tab_widget.addTab(self.plugin_manager_widget, "🧩 مدیریت پلاگین")
        # در init_ui بعد از بقیه تب‌ها:

# تب دستیار هوشمند ImanAI
        from ui.ai_assistant_widget import AIAssistantWidget
        self.ai_assistant = AIAssistantWidget()
        self.tab_widget.addTab(self.ai_assistant, "🤖 دستیار ImanAI")
        # نوار وضعیت
        self.statusBar().showMessage("آماده")
    
    def create_menu_bar(self):
        """ساخت منوی اصلی"""
        menubar = self.menuBar()
        
        # ========== منوی فایل ==========
        file_menu = menubar.addMenu("📁 فایل")
        
        new_action = QAction("📄 سند جدید", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_voucher)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        backup_action = QAction("💾 پشتیبان‌گیری", self)
        backup_action.triggered.connect(self.backup_database)
        file_menu.addAction(backup_action)
        
        restore_action = QAction("📂 بازیابی", self)
        restore_action.triggered.connect(self.restore_database)
        file_menu.addAction(restore_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("🚪 خروج", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ========== منوی ویرایش ==========
        edit_menu = menubar.addMenu("✏️ ویرایش")
        
        # ========== منوی گزارشات ==========
        reports_menu = menubar.addMenu("📊 گزارشات")
        
        trial_balance_action = QAction("📋 تراز آزمایشی", self)
        trial_balance_action.triggered.connect(self.show_trial_balance)
        reports_menu.addAction(trial_balance_action)
        
        profit_loss_action = QAction("💰 سود و زیان", self)
        profit_loss_action.triggered.connect(self.show_profit_loss)
        reports_menu.addAction(profit_loss_action)
        
        # ========== منوی تنظیمات ==========
        settings_menu = menubar.addMenu("⚙️ تنظیمات")
        
        company_action = QAction("🏢 اطلاعات شرکت", self)
        company_action.triggered.connect(self.company_settings)
        settings_menu.addAction(company_action)
        
        fiscal_year_action = QAction("📅 سال مالی", self)
        fiscal_year_action.triggered.connect(self.fiscal_year_settings)
        settings_menu.addAction(fiscal_year_action)
        
        # ========== منوی پلاگین‌ها ==========
        self.add_plugin_menus()
        
        # ========== منوی راهنما ==========
        help_menu = menubar.addMenu("❓ راهنما")
        
        about_action = QAction("ℹ️ درباره", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        license_action = QAction("🔑 اطلاعات لایسنس", self)
        license_action.triggered.connect(self.show_license_info)
        help_menu.addAction(license_action)
    
    def create_header(self):
        """ساخت هدر برنامه"""
        widget = QWidget()
        widget.setMaximumHeight(80)
        layout = QHBoxLayout(widget)
        
        # عنوان
        title = QLabel("سیستم جامع حسابداری پارسه")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 18px;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # تاریخ امروز
        today = QLabel(datetime.now().strftime("%Y/%m/%d"))
        today.setStyleSheet("font-size: 14px; font-weight: bold; color: #273c75;")
        layout.addWidget(today)
        
        # روزهای باقیمانده لایسنس
        days_left = self.license_info.get('days_left', 0)
        self.days_label = QLabel(f"⏰ {days_left} روز تا پایان لایسنس")
        
        # رنگ بر اساس روزهای باقیمانده
        if days_left <= 7:
            bg_color = "#e84118"  # قرمز
        elif days_left <= 30:
            bg_color = "#fbc531"  # زرد
        else:
            bg_color = "#4cd137"  # سبز
        
        self.days_label.setStyleSheet(f"""
            font-size: 12px;
            padding: 5px 10px;
            background-color: {bg_color};
            color: white;
            border-radius: 15px;
            font-weight: bold;
        """)
        layout.addWidget(self.days_label)
        
        return widget
    
    def add_plugin_tabs(self):
        """افزودن تب‌های پلاگین"""
        plugin_tabs = self.plugin_manager.get_plugin_tabs()
        
        for tab_info in plugin_tabs:
            try:
                plugin_id = tab_info.get('plugin_id', 'unknown')
                tab_title = tab_info.get('title', 'پلاگین')
                
                # روش ۱: اگر ویجت مستقیم داده شده
                if 'widget' in tab_info:
                    widget_class = tab_info['widget']
                    widget = widget_class()
                    self.tab_widget.addTab(widget, tab_title)
                
                # روش ۲: اگر شناسه ویجت داده شده
                elif 'widget_id' in tab_info:
                    widget = self.plugin_manager.get_plugin_widget(plugin_id, tab_info['widget_id'])
                    if widget:
                        self.tab_widget.addTab(widget, tab_title)
                
                print(f"  ✅ تب پلاگین '{tab_title}' اضافه شد")
                
            except Exception as e:
                print(f"  ❌ خطا در بارگذاری تب پلاگین: {e}")
    
    def add_plugin_menus(self):
        """افزودن منوهای پلاگین"""
        plugin_menus = self.plugin_manager.get_plugin_menus()
        
        if not plugin_menus:
            return
        
        # ایجاد منوی پلاگین‌ها
        plugins_menu = self.menuBar().addMenu("🧩 پلاگین‌ها")
        
        # گروه‌بندی منوها بر اساس parent
        menu_groups = {}
        
        for menu_info in plugin_menus:
            parent = menu_info.get('parent', 'main')
            if parent not in menu_groups:
                menu_groups[parent] = []
            menu_groups[parent].append(menu_info)
        
        # ایجاد منوها
        for parent, menus in menu_groups.items():
            if parent == 'main':
                target_menu = plugins_menu
            else:
                # می‌تونیم submenu بسازیم
                target_menu = plugins_menu.addMenu(parent)
            
            for menu_info in menus:
                action = QAction(menu_info.get('title', 'پلاگین'), self)
                
                # آیکون (اگر وجود داشته باشد)
                if 'icon' in menu_info:
                    action.setIcon(QIcon(menu_info['icon']))
                
                action.setData({
                    'plugin_id': menu_info['plugin_id'],
                    'action_id': menu_info.get('id', 'default')
                })
                action.triggered.connect(self.on_plugin_action)
                target_menu.addAction(action)
    
    def on_plugin_action(self):
        """اجرای اکشن پلاگین"""
        action = self.sender()
        data = action.data()
        
        result = self.plugin_manager.execute_action(
            data['plugin_id'],
            data['action_id'],
            main_window=self
        )
        
        if result:
            print(f"✅ اکشن {data['action_id']} از {data['plugin_id']} اجرا شد")
    
    def update_status_bar(self):
        """بروزرسانی نوار وضعیت با اطلاعات لایسنس"""
        plugins_count = len(self.plugin_manager.get_all_plugins())
        
        self.statusBar().showMessage(
            f"👤 کاربر: {self.license_info.get('customer', 'N/A')} | "
            f"📅 انقضا: {self.license_info.get('expire_date', 'N/A')} | "
            f"🔑 شناسه: {self.license_info.get('license_id', 'N/A')} | "
            f"🧩 پلاگین‌ها: {plugins_count}"
        )
    
    # ========== متدهای منو ==========
    
    def new_voucher(self):
        """ایجاد سند جدید"""
        # اگر تب حسابداری فعال است
        if hasattr(self, 'accounting_widget'):
            self.tab_widget.setCurrentWidget(self.accounting_widget)
            self.accounting_widget.new_voucher()
        else:
            QMessageBox.information(self, "سند جدید", "ماژول حسابداری فعال نیست!")
    
    def backup_database(self):
        """پشتیبان‌گیری از دیتابیس"""
        from database import DB_NAME
        import shutil
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره پشتیبان", 
            f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db", 
            "Database (*.db)"
        )
        
        if file_name:
            shutil.copy2(DB_NAME, file_name)
            QMessageBox.information(self, "موفق", "پشتیبان‌گیری با موفقیت انجام شد!")
    
    def restore_database(self):
        """بازیابی دیتابیس"""
        from database import DB_NAME
        import shutil
        
        reply = QMessageBox.question(
            self, "تأیید", 
            "آیا از بازیابی فایل پشتیبان اطمینان دارید؟\nاطلاعات فعلی از دست خواهند رفت!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            file_name, _ = QFileDialog.getOpenFileName(
                self, "انتخاب فایل پشتیبان", "", "Database (*.db)"
            )
            if file_name:
                shutil.copy2(file_name, DB_NAME)
                QMessageBox.information(self, "موفق", "بازیابی با موفقیت انجام شد!\nلطفاً برنامه را مجدداً اجرا کنید.")
    
    def show_trial_balance(self):
        """نمایش تراز آزمایشی"""
        if hasattr(self, 'reports_widget'):
            self.tab_widget.setCurrentWidget(self.reports_widget)
            # فراخوانی متد مربوطه در reports_widget
        else:
            QMessageBox.information(self, "تراز آزمایشی", "ماژول گزارشات فعال نیست!")
    
    def show_profit_loss(self):
        """نمایش سود و زیان"""
        if hasattr(self, 'reports_widget'):
            self.tab_widget.setCurrentWidget(self.reports_widget)
        else:
            QMessageBox.information(self, "سود و زیان", "ماژول گزارشات فعال نیست!")
    
    def company_settings(self):
        """تنظیمات شرکت"""
        QMessageBox.information(self, "تنظیمات", "اطلاعات شرکت\n\nاین بخش در نسخه‌های بعدی تکمیل می‌شود.")
    
    def fiscal_year_settings(self):
        """تنظیمات سال مالی"""
        QMessageBox.information(self, "سال مالی", "تنظیمات سال مالی\n\nاین بخش در نسخه‌های بعدی تکمیل می‌شود.")
    
    def show_about(self):
        """نمایش درباره برنامه"""
        plugins_count = len(self.plugin_manager.get_all_plugins())
        
        QMessageBox.about(
            self, "درباره نرم‌افزار",
            f"""
            <h2>📊 سیستم حسابداری پارسه</h2>
            <p>نسخه ۱.۰.۰</p>
            <p>نرم‌افزار جامع حسابداری، انبارداری و حقوق دستمزد</p>
            <hr>
            <p><b>🧩 پلاگین‌های فعال:</b> {plugins_count}</p>
            <hr>
            <p>توسعه‌دهنده: تیم پارسه</p>
            <p>📧 info@parseh-accounting.ir</p>
            <p>🌐 www.parseh-accounting.ir</p>
            """
        )
    
    def show_license_info(self):
        """نمایش اطلاعات لایسنس"""
        info = self.license_info
        modules = ', '.join(info.get('modules', []))
        plugins = len(self.plugin_manager.get_all_plugins())
        
        msg = f"""
        <h3>🔑 اطلاعات لایسنس</h3>
        <table>
        <tr><td><b>👤 مشتری:</b></td><td>{info.get('customer', 'N/A')}</td></tr>
        <tr><td><b>🆔 شناسه لایسنس:</b></td><td>{info.get('license_id', 'N/A')}</td></tr>
        <tr><td><b>📅 تاریخ انقضا:</b></td><td>{info.get('expire_date', 'N/A')}</td></tr>
        <tr><td><b>⏰ روزهای باقیمانده:</b></td><td>{info.get('days_left', 0)} روز</td></tr>
        <tr><td><b>📦 ماژول‌های فعال:</b></td><td>{modules}</td></tr>
        <tr><td><b>🧩 پلاگین‌های فعال:</b></td><td>{plugins}</td></tr>
        </table>
        """
        QMessageBox.information(self, "اطلاعات لایسنس", msg)
    
    # ========== رویدادهای پنجره ==========
    
    def closeEvent(self, event):
        """رویداد بستن پنجره"""
        reply = QMessageBox.question(
            self, "تأیید خروج",
            "آیا مطمئن هستید که می‌خواهید خارج شوید؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # پاک‌سازی پلاگین‌ها قبل از خروج
            for plugin in self.plugin_manager.get_all_plugins():
                plugin_id = plugin['id']
                # فراخوانی cleanup اگر وجود داشته باشد
                self.plugin_manager.execute_action(plugin_id, 'cleanup')
            
            event.accept()
        else:
            event.ignore()
