#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ویجت انبارداری - مدیریت کالاها و رسید/حواله
با قابلیت‌های: تعریف، ویرایش، حذف کالا - MoneyLineEdit - رسید/حواله
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from database import get_db, InventoryHelper


# ============================================================
# کلاس کمکی - فیلد ورودی مبالغ ریالی
# ============================================================
class MoneyLineEdit(QLineEdit):
    """فیلد ورودی مخصوص مبالغ ریالی با فرمت خودکار جداکننده هزارگان"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignRight)
        self.setPlaceholderText("مبلغ به ریال")
        self.textChanged.connect(self._format_text)
        self._current_value = 0
        
    def _format_text(self):
        """فرمت کردن متن به صورت جداکننده هزارگان"""
        text = self.text().strip()
        if not text:
            self._current_value = 0
            return
            
        # حذف کاراکترهای غیر عددی
        digits = ''.join(filter(str.isdigit, text))
        if not digits:
            self._current_value = 0
            self.blockSignals(True)
            self.setText("")
            self.blockSignals(False)
            return
            
        # ذخیره مقدار واقعی
        self._current_value = int(digits)
        
        # فرمت با جداکننده
        formatted = f"{self._current_value:,}"
        
        # جلوگیری از حلقه بی‌نهایت
        self.blockSignals(True)
        self.setText(formatted)
        self.blockSignals(False)
        
    def value(self) -> int:
        """دریافت مقدار عددی"""
        return self._current_value
        
    def setValue(self, value: int):
        """تنظیم مقدار عددی"""
        self._current_value = value if value else 0
        self.blockSignals(True)
        self.setText(f"{self._current_value:,}" if self._current_value > 0 else "")
        self.blockSignals(False)


# ============================================================
# ویجت اصلی انبارداری
# ============================================================
class InventoryWidget(QWidget):
    """ویجت اصلی مدیریت انبار"""
    
    def __init__(self):
        super().__init__()
        self.products_data = []
        self.init_ui()
        self.load_products()
        self.check_low_stock()
    
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # ========== پنل سمت راست (لیست کالاها) ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # عنوان
        title = QLabel("📦 مدیریت انبار")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px; color: #2C3E50;")
        right_layout.addWidget(title)
        
        # نوار ابزار
        toolbar = QHBoxLayout()
        
        new_btn = QPushButton("➕ کالای جدید")
        new_btn.setObjectName("successBtn")
        new_btn.clicked.connect(self.new_product)
        toolbar.addWidget(new_btn)
        
        edit_btn = QPushButton("✏️ ویرایش کالا")
        edit_btn.clicked.connect(self.edit_product)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ حذف کالا")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.clicked.connect(self.delete_product)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        # دکمه‌های رسید/حواله
        stock_in_btn = QPushButton("📥 رسید انبار")
        stock_in_btn.setObjectName("successBtn")
        stock_in_btn.clicked.connect(lambda: self.stock_transaction('in'))
        toolbar.addWidget(stock_in_btn)
        
        stock_out_btn = QPushButton("📤 حواله انبار")
        stock_out_btn.setStyleSheet("background-color: #e1b12c;")
        stock_out_btn.clicked.connect(lambda: self.stock_transaction('out'))
        toolbar.addWidget(stock_out_btn)
        
        right_layout.addLayout(toolbar)
        
        # جستجو
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 جستجو:")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("کد یا نام کالا...")
        self.search_input.textChanged.connect(self.filter_products)
        search_layout.addWidget(self.search_input)
        right_layout.addLayout(search_layout)
        
        # جدول کالاها
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(7)
        self.products_table.setHorizontalHeaderLabels([
            "کد کالا", "نام کالا", "واحد", "موجودی", 
            "قیمت خرید", "قیمت فروش", "ارزش موجودی"
        ])
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.products_table.horizontalHeader().setStretchLastSection(True)
        self.products_table.clicked.connect(self.on_product_selected)
        self.products_table.doubleClicked.connect(self.edit_product)  # دابل کلیک = ویرایش
        right_layout.addWidget(self.products_table)
        
        # هشدار موجودی کم
        self.warning_label = QLabel()
        self.warning_label.setObjectName("warningLabel")
        self.warning_label.setWordWrap(True)
        right_layout.addWidget(self.warning_label)
        
        # ========== پنل سمت چپ (جزئیات و گردش کالا) ==========
        left_panel = QWidget()
        left_panel.setMaximumWidth(450)
        left_layout = QVBoxLayout(left_panel)
        
        # اطلاعات کالا
        info_group = QGroupBox("📋 اطلاعات کالا")
        info_layout = QFormLayout()
        
        self.product_code = QLineEdit()
        self.product_code.setReadOnly(True)
        info_layout.addRow("کد کالا:", self.product_code)
        
        self.product_name = QLineEdit()
        self.product_name.setReadOnly(True)
        info_layout.addRow("نام کالا:", self.product_name)
        
        self.product_unit = QLineEdit()
        self.product_unit.setReadOnly(True)
        info_layout.addRow("واحد:", self.product_unit)
        
        self.product_stock = QLineEdit()
        self.product_stock.setReadOnly(True)
        self.product_stock.setStyleSheet("font-weight: bold; font-size: 14px; color: #273c75;")
        info_layout.addRow("موجودی فعلی:", self.product_stock)
        
        self.product_purchase = QLineEdit()
        self.product_purchase.setReadOnly(True)
        info_layout.addRow("قیمت خرید:", self.product_purchase)
        
        self.product_sale = QLineEdit()
        self.product_sale.setReadOnly(True)
        info_layout.addRow("قیمت فروش:", self.product_sale)
        
        info_group.setLayout(info_layout)
        left_layout.addWidget(info_group)
        
        # دکمه‌های سریع
        quick_btn_layout = QHBoxLayout()
        
        quick_in_btn = QPushButton("📥 رسید")
        quick_in_btn.setObjectName("successBtn")
        quick_in_btn.clicked.connect(lambda: self.stock_transaction('in'))
        quick_btn_layout.addWidget(quick_in_btn)
        
        quick_out_btn = QPushButton("📤 حواله")
        quick_out_btn.setStyleSheet("background-color: #e1b12c;")
        quick_out_btn.clicked.connect(lambda: self.stock_transaction('out'))
        quick_btn_layout.addWidget(quick_out_btn)
        
        left_layout.addLayout(quick_btn_layout)
        
        # گردش کالا
        history_group = QGroupBox("🔄 گردش کالا")
        history_layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "تاریخ", "نوع", "مقدار", "فی", "مبلغ کل"
        ])
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        history_layout.addWidget(self.history_table)
        
        history_group.setLayout(history_layout)
        left_layout.addWidget(history_group)
        
        # افزودن پنل‌ها به layout اصلی
        main_layout.addWidget(right_panel, 2)
        main_layout.addWidget(left_panel, 1)
    
    # ========== عملیات اصلی ==========
    
    def load_products(self):
        """بارگذاری لیست کالاها"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM products ORDER BY code')
            self.products_data = c.fetchall()
            self.display_products(self.products_data)
    
    def display_products(self, products):
        """نمایش کالاها در جدول"""
        self.products_table.setRowCount(len(products))
        
        for i, p in enumerate(products):
            self.products_table.setItem(i, 0, QTableWidgetItem(p['code']))
            self.products_table.setItem(i, 1, QTableWidgetItem(p['name']))
            self.products_table.setItem(i, 2, QTableWidgetItem(p['unit'] or 'عدد'))
            
            # موجودی با رنگ
            stock = p['stock'] or 0
            stock_item = QTableWidgetItem(f"{stock:,.2f}")
            if stock <= (p['min_stock'] or 0):
                stock_item.setForeground(QColor('#e84118'))
                stock_item.setFont(QFont('', -1, QFont.Bold))
            else:
                stock_item.setForeground(QColor('#4cd137'))
            self.products_table.setItem(i, 3, stock_item)
            
            self.products_table.setItem(i, 4, QTableWidgetItem(f"{p['purchase_price']:,.0f}"))
            self.products_table.setItem(i, 5, QTableWidgetItem(f"{p['sale_price']:,.0f}"))
            
            # ارزش موجودی
            value = stock * (p['purchase_price'] or 0)
            self.products_table.setItem(i, 6, QTableWidgetItem(f"{value:,.0f}"))
    
    def filter_products(self):
        """فیلتر کالاها"""
        search_text = self.search_input.text().strip()
        if not search_text:
            self.display_products(self.products_data)
            return
        
        filtered = []
        for p in self.products_data:
            if (search_text.lower() in p['code'].lower() or
                search_text.lower() in p['name'].lower()):
                filtered.append(p)
        
        self.display_products(filtered)
    
    def check_low_stock(self):
        """بررسی کالاهای با موجودی کم"""
        low_stock = InventoryHelper.get_low_stock_products()
        
        if low_stock:
            warning_text = "⚠️ هشدار: کالاهای زیر به حداقل موجودی رسیده‌اند:\n"
            for p in low_stock[:5]:
                warning_text += f"• {p['name']}: {p['stock']:,.2f} {p['unit']}\n"
            self.warning_label.setText(warning_text)
            self.warning_label.setStyleSheet("""
                color: #e84118;
                font-weight: bold;
                background-color: #FADBD8;
                padding: 10px;
                border-radius: 6px;
                border-left: 4px solid #e84118;
            """)
        else:
            self.warning_label.setText("✅ تمام کالاها موجودی کافی دارند")
            self.warning_label.setStyleSheet("""
                color: #27ae60;
                font-weight: bold;
                background-color: #D5F5E3;
                padding: 10px;
                border-radius: 6px;
                border-left: 4px solid #27ae60;
            """)
    
    def on_product_selected(self):
        """انتخاب کالا - نمایش جزئیات"""
        current_row = self.products_table.currentRow()
        if current_row >= 0:
            # پیدا کردن کالای انتخاب شده با توجه به فیلتر
            code = self.products_table.item(current_row, 0).text()
            for p in self.products_data:
                if p['code'] == code:
                    self.show_product_details(p['id'])
                    break
    
    def show_product_details(self, product_id):
        """نمایش جزئیات کالا در پنل سمت چپ"""
        with get_db() as conn:
            c = conn.cursor()
            
            # اطلاعات کالا
            c.execute('SELECT * FROM products WHERE id = ?', [product_id])
            product = c.fetchone()
            
            if not product:
                return
            
            self.current_product = product
            
            self.product_code.setText(product['code'])
            self.product_name.setText(product['name'])
            self.product_unit.setText(product['unit'] or 'عدد')
            self.product_stock.setText(f"{product['stock']:,.2f}")
            self.product_purchase.setText(f"{product['purchase_price']:,.0f} ریال")
            self.product_sale.setText(f"{product['sale_price']:,.0f} ریال")
            
            # گردش کالا
            c.execute('''
                SELECT date, type, quantity, unit_price, total_price
                FROM stock_transactions
                WHERE product_id = ?
                ORDER BY date DESC, id DESC
                LIMIT 50
            ''', [product_id])
            
            transactions = c.fetchall()
            self.history_table.setRowCount(len(transactions))
            
            for i, t in enumerate(transactions):
                self.history_table.setItem(i, 0, QTableWidgetItem(t['date']))
                
                type_text = "📥 ورود" if t['type'] == 'in' else "📤 خروج"
                type_item = QTableWidgetItem(type_text)
                if t['type'] == 'in':
                    type_item.setForeground(QColor('#4cd137'))
                else:
                    type_item.setForeground(QColor('#e84118'))
                self.history_table.setItem(i, 1, type_item)
                
                self.history_table.setItem(i, 2, QTableWidgetItem(f"{t['quantity']:,.2f}"))
                self.history_table.setItem(i, 3, QTableWidgetItem(f"{t['unit_price']:,.0f}"))
                self.history_table.setItem(i, 4, QTableWidgetItem(f"{t['total_price']:,.0f}"))
    
    def new_product(self):
        """ایجاد کالای جدید"""
        dialog = ProductDialog()
        if dialog.exec_():
            self.load_products()
            self.check_low_stock()
            QMessageBox.information(self, "موفق", "✅ کالای جدید با موفقیت ایجاد شد!")
    
    def edit_product(self):
        """ویرایش کالای انتخاب شده"""
        current_row = self.products_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک کالا را انتخاب کنید!")
            return
        
        # پیدا کردن کالای انتخاب شده
        code = self.products_table.item(current_row, 0).text()
        for p in self.products_data:
            if p['code'] == code:
                dialog = ProductDialog(p['id'])
                if dialog.exec_():
                    self.load_products()
                    self.check_low_stock()
                    self.show_product_details(p['id'])
                    QMessageBox.information(self, "موفق", "✅ کالا با موفقیت ویرایش شد!")
                break
    
    def delete_product(self):
        """حذف کالای انتخاب شده"""
        current_row = self.products_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک کالا را انتخاب کنید!")
            return
        
        # پیدا کردن کالا
        code = self.products_table.item(current_row, 0).text()
        name = self.products_table.item(current_row, 1).text()
        
        for p in self.products_data:
            if p['code'] == code:
                # بررسی وجود تراکنش
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute('SELECT COUNT(*) FROM stock_transactions WHERE product_id = ?', [p['id']])
                    trans_count = c.fetchone()[0]
                
                warning = ""
                if trans_count > 0:
                    warning = f"\n⚠️ این کالا {trans_count} تراکنش ثبت شده دارد که همراه با آن حذف خواهند شد!"
                
                reply = QMessageBox.question(
                    self, "تأیید حذف",
                    f"آیا از حذف کالای '{name}' اطمینان دارید؟{warning}",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    with get_db() as conn:
                        c = conn.cursor()
                        c.execute('DELETE FROM stock_transactions WHERE product_id = ?', [p['id']])
                        c.execute('DELETE FROM products WHERE id = ?', [p['id']])
                    
                    self.load_products()
                    self.check_low_stock()
                    
                    # پاک کردن جزئیات
                    self.product_code.clear()
                    self.product_name.clear()
                    self.product_unit.clear()
                    self.product_stock.clear()
                    self.product_purchase.clear()
                    self.product_sale.clear()
                    self.history_table.setRowCount(0)
                    
                    QMessageBox.information(self, "موفق", "✅ کالا با موفقیت حذف شد!")
                break
    
    def stock_transaction(self, trans_type):
        """رسید/حواله انبار"""
        current_row = self.products_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک کالا انتخاب کنید!")
            return
        
        # پیدا کردن کالا
        code = self.products_table.item(current_row, 0).text()
        for p in self.products_data:
            if p['code'] == code:
                dialog = StockTransactionDialog(p, trans_type)
                if dialog.exec_():
                    self.load_products()
                    self.show_product_details(p['id'])
                    self.check_low_stock()
                    QMessageBox.information(self, "موفق", 
                        "✅ رسید انبار با موفقیت ثبت شد!" if trans_type == 'in' else "✅ حواله انبار با موفقیت ثبت شد!")
                break


# ============================================================
# دیالوگ تعریف/ویرایش کالا
# ============================================================
class ProductDialog(QDialog):
    """دیالوگ ایجاد/ویرایش کالا"""
    
    def __init__(self, product_id=None):
        super().__init__()
        self.product_id = product_id
        self.setWindowTitle("✏️ ویرایش کالا" if product_id else "➕ تعریف کالای جدید")
        self.setGeometry(300, 200, 500, 450)
        self.init_ui()
        
        if product_id:
            self.load_product_data()
    
    def init_ui(self):
        layout = QFormLayout(self)
        
        # کد کالا
        self.code = QLineEdit()
        self.code.setPlaceholderText("مثال: KALA-001")
        layout.addRow("کد کالا *:", self.code)
        
        # نام کالا
        self.name = QLineEdit()
        self.name.setPlaceholderText("نام کالا")
        layout.addRow("نام کالا *:", self.name)
        
        # واحد اندازه‌گیری
        self.unit = QComboBox()
        self.unit.addItems(["عدد", "کیلوگرم", "متر", "لیتر", "بسته", "کارتن"])
        self.unit.setEditable(True)
        layout.addRow("واحد:", self.unit)
        
        # قیمت خرید
        self.purchase_price = MoneyLineEdit()
        layout.addRow("قیمت خرید (ریال):", self.purchase_price)
        
        # قیمت فروش
        self.sale_price = MoneyLineEdit()
        layout.addRow("قیمت فروش (ریال):", self.sale_price)
        
        # حداقل موجودی
        self.min_stock = QDoubleSpinBox()
        self.min_stock.setRange(0, 999999)
        self.min_stock.setSingleStep(1)
        self.min_stock.setDecimals(2)
        self.min_stock.setSuffix(" " + self.unit.currentText())
        layout.addRow("حداقل موجودی:", self.min_stock)
        
        # بروزرسانی واحد حداقل موجودی
        self.unit.currentTextChanged.connect(
            lambda text: self.min_stock.setSuffix(f" {text}")
        )
        
        # راهنما
        hint_label = QLabel("💡 قیمت‌ها را می‌توانید با جداکننده هزارگان یا بدون آن وارد کنید.")
        hint_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addRow("", hint_label)
        
        # دکمه‌ها
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def load_product_data(self):
        """بارگذاری اطلاعات کالا برای ویرایش"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM products WHERE id = ?', [self.product_id])
            product = c.fetchone()
            
            if product:
                self.code.setText(product['code'])
                self.name.setText(product['name'])
                self.unit.setCurrentText(product['unit'] or 'عدد')
                self.purchase_price.setValue(product['purchase_price'] or 0)
                self.sale_price.setValue(product['sale_price'] or 0)
                self.min_stock.setValue(product['min_stock'] or 0)
    
    def accept(self):
        """ذخیره کالا"""
        # اعتبارسنجی
        if not self.code.text().strip():
            QMessageBox.warning(self, "خطا", "کد کالا الزامی است!")
            return
            
        if not self.name.text().strip():
            QMessageBox.warning(self, "خطا", "نام کالا الزامی است!")
            return
        
        with get_db() as conn:
            c = conn.cursor()
            
            data = [
                self.code.text().strip(),
                self.name.text().strip(),
                self.unit.currentText(),
                self.purchase_price.value(),
                self.sale_price.value(),
                self.min_stock.value()
            ]
            
            if self.product_id:
                # ویرایش
                data.append(self.product_id)
                try:
                    c.execute('''
                        UPDATE products 
                        SET code=?, name=?, unit=?, purchase_price=?, sale_price=?, min_stock=?
                        WHERE id=?
                    ''', data)
                except sqlite3.IntegrityError:
                    QMessageBox.warning(self, "خطا", "کد کالا تکراری است!")
                    return
            else:
                # ایجاد جدید
                try:
                    c.execute('''
                        INSERT INTO products (code, name, unit, purchase_price, sale_price, min_stock)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', data)
                except sqlite3.IntegrityError:
                    QMessageBox.warning(self, "خطا", "کد کالا تکراری است!")
                    return
        
        super().accept()


# ============================================================
# دیالوگ رسید/حواله انبار
# ============================================================
class StockTransactionDialog(QDialog):
    """دیالوگ رسید/حواله انبار"""
    
    def __init__(self, product, trans_type):
        super().__init__()
        self.product = product
        self.trans_type = trans_type
        self.setWindowTitle("📥 رسید انبار" if trans_type == 'in' else "📤 حواله انبار")
        self.setGeometry(350, 250, 450, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout(self)
        
        # عنوان
        title = QLabel(f"<h3>{self.product['name']}</h3>")
        title.setAlignment(Qt.AlignCenter)
        layout.addRow(title)
        
        # اطلاعات کالا
        stock_info = QLabel(f"موجودی فعلی: {self.product['stock']:,.2f} {self.product['unit']}")
        stock_info.setStyleSheet("font-weight: bold; color: #273c75;")
        layout.addRow(stock_info)
        
        # خط جداکننده
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addRow(line)
        
        # تاریخ
        self.date = QDateEdit()
        self.date.setDate(QDate.currentDate())
        self.date.setCalendarPopup(True)
        layout.addRow("تاریخ:", self.date)
        
        # مقدار
        self.quantity = QDoubleSpinBox()
        self.quantity.setRange(0.01, 999999)
        self.quantity.setSingleStep(1)
        self.quantity.setDecimals(2)
        self.quantity.setSuffix(f" {self.product['unit']}")
        self.quantity.valueChanged.connect(self.calculate_total)
        layout.addRow("مقدار *:", self.quantity)
        
        # قیمت واحد
        self.unit_price = MoneyLineEdit()
        if self.trans_type == 'in':
            self.unit_price.setValue(self.product['purchase_price'] or 0)
        else:
            self.unit_price.setValue(self.product['sale_price'] or 0)
        self.unit_price.textChanged.connect(self.calculate_total)
        layout.addRow("فی (ریال) *:", self.unit_price)
        
        # مبلغ کل
        self.total_price_label = QLabel("۰ ریال")
        self.total_price_label.setStyleSheet("font-weight: bold; color: #27ae60; font-size: 12pt;")
        layout.addRow("مبلغ کل:", self.total_price_label)
        
        # شماره مرجع
        self.ref_no = QLineEdit()
        self.ref_no.setPlaceholderText("شماره فاکتور/رسید (اختیاری)")
        layout.addRow("شماره مرجع:", self.ref_no)
        
        # شرح
        self.description = QTextEdit()
        self.description.setPlaceholderText("توضیحات (اختیاری)")
        self.description.setMaximumHeight(80)
        layout.addRow("شرح:", self.description)
        
        # راهنما
        hint_label = QLabel("💡 قیمت واحد را می‌توانید با جداکننده هزارگان یا بدون آن وارد کنید.")
        hint_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addRow("", hint_label)
        
        # دکمه‌ها
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.calculate_total()
    
    def calculate_total(self):
        """محاسبه مبلغ کل"""
        try:
            quantity = self.quantity.value()
            unit_price = self.unit_price.value()
            total = quantity * unit_price
            self.total_price_label.setText(f"{total:,.0f} ریال")
            self._total_value = total
        except:
            self.total_price_label.setText("۰ ریال")
            self._total_value = 0
    
    def accept(self):
        """ثبت تراکنش"""
        # اعتبارسنجی
        if self.quantity.value() == 0:
            QMessageBox.warning(self, "خطا", "مقدار باید بیشتر از صفر باشد!")
            return
        
        if self.unit_price.value() == 0:
            QMessageBox.warning(self, "خطا", "قیمت واحد باید بیشتر از صفر باشد!")
            return
        
        if self.trans_type == 'out' and self.quantity.value() > self.product['stock']:
            QMessageBox.warning(self, "خطا", f"موجودی کافی نیست! (موجودی: {self.product['stock']:,.2f})")
            return
        
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO stock_transactions 
                (date, product_id, type, quantity, unit_price, total_price, ref_no, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                self.date.date().toString("yyyy-MM-dd"),
                self.product['id'],
                self.trans_type,
                self.quantity.value(),
                self.unit_price.value(),
                self._total_value,
                self.ref_no.text(),
                self.description.toPlainText()
            ])
            
            InventoryHelper.update_stock(
                self.product['id'],
                self.quantity.value(),
                self.trans_type
            )
        
        super().accept()
