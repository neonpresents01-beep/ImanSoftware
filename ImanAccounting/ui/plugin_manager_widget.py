"""
ویجت مدیریت پلاگین‌ها
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import os
from plugins import PluginManager

class PluginManagerWidget(QWidget):
    """ویجت نمایش و مدیریت پلاگین‌ها"""
    
    def __init__(self):
        super().__init__()
        self.plugin_manager = PluginManager()
        self.init_ui()
        self.load_plugins_list()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # عنوان
        title = QLabel("🧩 مدیریت پلاگین‌ها")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # نوار ابزار
        toolbar = QHBoxLayout()
        
        install_btn = QPushButton("📦 نصب پلاگین جدید")
        install_btn.clicked.connect(self.install_plugin)
        toolbar.addWidget(install_btn)
        
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.clicked.connect(self.refresh_plugins)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # جدول پلاگین‌ها
        self.plugins_table = QTableWidget()
        self.plugins_table.setColumnCount(6)
        self.plugins_table.setHorizontalHeaderLabels([
            "نام", "نسخه", "شناسه", "توضیحات", "نویسنده", "وضعیت"
        ])
        self.plugins_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.plugins_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.plugins_table.horizontalHeader().setStretchLastSection(True)
        self.plugins_table.setAlternatingRowColors(True)
        layout.addWidget(self.plugins_table)
        
        # دکمه‌های عملیات
        btn_layout = QHBoxLayout()
        
        self.enable_btn = QPushButton("✅ فعال‌سازی")
        self.enable_btn.clicked.connect(self.enable_plugin)
        btn_layout.addWidget(self.enable_btn)
        
        self.disable_btn = QPushButton("⛔ غیرفعال‌سازی")
        self.disable_btn.clicked.connect(self.disable_plugin)
        btn_layout.addWidget(self.disable_btn)
        
        uninstall_btn = QPushButton("🗑️ حذف پلاگین")
        uninstall_btn.setObjectName("deleteBtn")
        uninstall_btn.clicked.connect(self.uninstall_plugin)
        btn_layout.addWidget(uninstall_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # اطلاعات بیشتر
        info_group = QGroupBox("اطلاعات پلاگین")
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        info_layout.addWidget(self.info_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # اتصال رویداد انتخاب
        self.plugins_table.clicked.connect(self.on_plugin_selected)
    
    def load_plugins_list(self):
        """بارگذاری لیست پلاگین‌ها"""
        plugins = self.plugin_manager.get_all_plugins()
        
        self.plugins_table.setRowCount(len(plugins))
        
        for i, plugin in enumerate(plugins):
            self.plugins_table.setItem(i, 0, QTableWidgetItem(plugin.get('name', '-')))
            self.plugins_table.setItem(i, 1, QTableWidgetItem(plugin.get('version', '-')))
            self.plugins_table.setItem(i, 2, QTableWidgetItem(plugin.get('id', '-')))
            self.plugins_table.setItem(i, 3, QTableWidgetItem(plugin.get('description', '-')))
            self.plugins_table.setItem(i, 4, QTableWidgetItem(plugin.get('author', '-')))
            
            status_item = QTableWidgetItem("✅ فعال")
            status_item.setForeground(QColor('#4CAF50'))
            self.plugins_table.setItem(i, 5, status_item)
    
    def on_plugin_selected(self):
        """رویداد انتخاب پلاگین"""
        current_row = self.plugins_table.currentRow()
        if current_row >= 0:
            plugin_id = self.plugins_table.item(current_row, 2).text()
            self.show_plugin_info(plugin_id)
    
    def show_plugin_info(self, plugin_id: str):
        """نمایش اطلاعات پلاگین"""
        plugins = self.plugin_manager.get_all_plugins()
        
        for plugin in plugins:
            if plugin['id'] == plugin_id:
                manifest = plugin.get('manifest', {})
                info = f"""
                <h3>{plugin.get('name', '-')}</h3>
                <p><b>شناسه:</b> {plugin.get('id', '-')}</p>
                <p><b>نسخه:</b> {plugin.get('version', '-')}</p>
                <p><b>توضیحات:</b> {plugin.get('description', '-')}</p>
                <p><b>نویسنده:</b> {plugin.get('author', '-')}</p>
                <p><b>مسیر:</b> {plugin.get('path', '-')}</p>
                <p><b>مجوزها:</b> {', '.join(manifest.get('permissions', []))}</p>
                """
                self.info_text.setHtml(info)
                break
    
    def install_plugin(self):
        """نصب پلاگین جدید"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل پلاگین", "", "Plugin Files (*.plugin);;All Files (*.*)"
        )
        
        if file_path:
            if self.plugin_manager.install_plugin(file_path):
                QMessageBox.information(self, "موفق", "پلاگین با موفقیت نصب شد!")
                self.refresh_plugins()
            else:
                QMessageBox.warning(self, "خطا", "خطا در نصب پلاگین!")
    
    def uninstall_plugin(self):
        """حذف پلاگین"""
        current_row = self.plugins_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "خطا", "یک پلاگین انتخاب کنید!")
            return
        
        plugin_name = self.plugins_table.item(current_row, 0).text()
        plugin_id = self.plugins_table.item(current_row, 2).text()
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف پلاگین '{plugin_name}' اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.plugin_manager.uninstall_plugin(plugin_id):
                QMessageBox.information(self, "موفق", "پلاگین با موفقیت حذف شد!")
                self.refresh_plugins()
                self.info_text.clear()
            else:
                QMessageBox.warning(self, "خطا", "خطا در حذف پلاگین!")
    
    def enable_plugin(self):
        """فعال‌سازی پلاگین"""
        QMessageBox.information(self, "فعال‌سازی", "این قابلیت به زودی اضافه می‌شود!")
    
    def disable_plugin(self):
        """غیرفعال‌سازی پلاگین"""
        QMessageBox.information(self, "غیرفعال‌سازی", "این قابلیت به زودی اضافه می‌شود!")
    
    def refresh_plugins(self):
        """بروزرسانی لیست پلاگین‌ها"""
        self.plugin_manager.reload_plugins()
        self.load_plugins_list()
        self.info_text.clear()
