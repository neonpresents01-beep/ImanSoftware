#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ویجت حسابداری - ثبت اسناد و دفتر روزنامه
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
from database import get_db, AccountingHelper


class AccountingWidget(QWidget):
    """ویجت اصلی حسابداری"""
    
    def __init__(self):
        super().__init__()
        self.vouchers_data = []
        self.accounts = []
        self.init_ui()
        self.load_vouchers()
        self.load_accounts()
    
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # پنل سمت راست (لیست اسناد)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # عنوان
        title = QLabel("اسناد حسابداری")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px; color: #2C3E50;")
        right_layout.addWidget(title)
        
        # نوار ابزار
        toolbar = QHBoxLayout()
        
        new_btn = QPushButton("➕ سند جدید")
        new_btn.clicked.connect(self.new_voucher)
        toolbar.addWidget(new_btn)
        
        edit_btn = QPushButton("✏️ ویرایش")
        edit_btn.clicked.connect(self.edit_voucher)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ حذف")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.clicked.connect(self.delete_voucher)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        # جستجو
        search_label = QLabel("🔍 جستجو:")
        toolbar.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("شماره سند یا شرح...")
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self.filter_vouchers)
        toolbar.addWidget(self.search_input)
        
        right_layout.addLayout(toolbar)
        
        # جدول اسناد
        self.vouchers_table = QTableWidget()
        self.vouchers_table.setColumnCount(6)
        self.vouchers_table.setHorizontalHeaderLabels([
            "شماره سند", "تاریخ", "شرح", "نوع", "بدهکار", "بستانکار"
        ])
        self.vouchers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.vouchers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.vouchers_table.horizontalHeader().setStretchLastSection(True)
        self.vouchers_table.clicked.connect(self.on_voucher_selected)
        right_layout.addWidget(self.vouchers_table)
        
        # پنل سمت چپ (جزئیات سند)
        left_panel = QWidget()
        left_panel.setMaximumWidth(500)
        left_layout = QVBoxLayout(left_panel)
        
        # جزئیات سند
        details_group = QGroupBox("جزئیات سند")
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        left_layout.addWidget(details_group)
        
        # تراز آزمایشی
        trial_group = QGroupBox("تراز آزمایشی")
        trial_layout = QVBoxLayout()
        
        trial_layout.addWidget(QLabel("تاریخ:"))
        self.trial_date = QDateEdit()
        self.trial_date.setDate(QDate.currentDate())
        self.trial_date.setCalendarPopup(True)
        trial_layout.addWidget(self.trial_date)
        
        show_trial_btn = QPushButton("📊 نمایش تراز")
        show_trial_btn.clicked.connect(self.show_trial_balance)
        trial_layout.addWidget(show_trial_btn)
        
        self.trial_text = QTextEdit()
        self.trial_text.setReadOnly(True)
        trial_layout.addWidget(self.trial_text)
        
        trial_group.setLayout(trial_layout)
        left_layout.addWidget(trial_group)
        
        # افزودن پنل‌ها
        main_layout.addWidget(right_panel, 2)
        main_layout.addWidget(left_panel, 1)
    
    def load_accounts(self):
        """بارگذاری لیست حساب‌ها"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT code, name, type FROM accounts WHERE is_active = 1 ORDER BY code")
            self.accounts = c.fetchall()
    
    def load_vouchers(self):
        """بارگذاری لیست اسناد"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT 
                    v.id,
                    v.voucher_no,
                    v.date,
                    v.description,
                    v.type,
                    COALESCE(SUM(vi.debit), 0) as total_debit,
                    COALESCE(SUM(vi.credit), 0) as total_credit
                FROM vouchers v
                LEFT JOIN voucher_items vi ON v.id = vi.voucher_id
                GROUP BY v.id, v.voucher_no, v.date, v.description, v.type
                ORDER BY v.date DESC, v.voucher_no DESC
            ''')
            
            self.vouchers_data = c.fetchall()
            self.display_vouchers(self.vouchers_data)
    
    def display_vouchers(self, vouchers):
        """نمایش اسناد در جدول"""
        self.vouchers_table.setRowCount(len(vouchers))
        
        for i, v in enumerate(vouchers):
            self.vouchers_table.setItem(i, 0, QTableWidgetItem(str(v['voucher_no'] or '')))
            self.vouchers_table.setItem(i, 1, QTableWidgetItem(v['date'] or ''))
            self.vouchers_table.setItem(i, 2, QTableWidgetItem(v['description'] or ''))
            self.vouchers_table.setItem(i, 3, QTableWidgetItem(v['type'] or 'عادی'))
            
            debit_item = QTableWidgetItem(f"{v['total_debit']:,.0f}")
            debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.vouchers_table.setItem(i, 4, debit_item)
            
            credit_item = QTableWidgetItem(f"{v['total_credit']:,.0f}")
            credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.vouchers_table.setItem(i, 5, credit_item)
    
    def filter_vouchers(self):
        """فیلتر اسناد بر اساس جستجو"""
        search_text = self.search_input.text().strip()
        if not search_text:
            self.display_vouchers(self.vouchers_data)
            return
        
        filtered = []
        for v in self.vouchers_data:
            if (search_text.lower() in str(v['voucher_no']).lower() or
                search_text.lower() in str(v['description']).lower()):
                filtered.append(v)
        
        self.display_vouchers(filtered)
    
    def on_voucher_selected(self):
        """رویداد انتخاب سند"""
        current_row = self.vouchers_table.currentRow()
        if current_row >= 0 and current_row < len(self.vouchers_data):
            voucher_id = self.vouchers_data[current_row]['id']
            self.show_voucher_details(voucher_id)
    
    def show_voucher_details(self, voucher_id):
        """نمایش جزئیات سند"""
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('SELECT * FROM vouchers WHERE id = ?', [voucher_id])
            voucher = c.fetchone()
            
            c.execute('''
                SELECT vi.*, a.name as account_name
                FROM voucher_items vi
                JOIN accounts a ON vi.account_code = a.code
                WHERE vi.voucher_id = ?
            ''', [voucher_id])
            items = c.fetchall()
            
            details = f"""
            <h3>سند شماره: {voucher['voucher_no']}</h3>
            <p><b>تاریخ:</b> {voucher['date']}</p>
            <p><b>شرح:</b> {voucher['description']}</p>
            <hr>
            <h4>اقلام سند:</h4>
            <table width='100%' border='1' style='border-collapse: collapse;'>
            <tr><th>کد حساب</th><th>نام حساب</th><th>بدهکار</th><th>بستانکار</th></tr>
            """
            
            total_debit = 0
            total_credit = 0
            
            for item in items:
                details += f"""
                <tr>
                    <td>{item['account_code']}</td>
                    <td>{item['account_name']}</td>
                    <td style='text-align: right;'>{item['debit']:,.0f}</td>
                    <td style='text-align: right;'>{item['credit']:,.0f}</td>
                </tr>
                """
                total_debit += item['debit'] or 0
                total_credit += item['credit'] or 0
            
            details += f"""
            <tr style='font-weight: bold; background-color: #f0f0f0;'>
                <td colspan='2'>جمع</td>
                <td style='text-align: right;'>{total_debit:,.0f}</td>
                <td style='text-align: right;'>{total_credit:,.0f}</td>
            </tr>
            </table>
            """
            
            if total_debit == total_credit:
                details += "<p style='color: green; font-weight: bold;'>✅ سند موازنه است</p>"
            else:
                diff = abs(total_debit - total_credit)
                details += f"<p style='color: red; font-weight: bold;'>⚠️ عدم موازنه: {diff:,.0f}</p>"
            
            self.details_text.setHtml(details)
    
    def new_voucher(self):
        """ایجاد سند جدید"""
        dialog = VoucherDialog(self.accounts)
        if dialog.exec_():
            self.load_vouchers()
    
    def edit_voucher(self):
        """ویرایش سند"""
        current_row = self.vouchers_table.currentRow()
        if current_row < 0 or current_row >= len(self.vouchers_data):
            QMessageBox.warning(self, "خطا", "لطفاً یک سند انتخاب کنید!")
            return
        
        voucher_id = self.vouchers_data[current_row]['id']
        dialog = VoucherDialog(self.accounts, voucher_id)
        if dialog.exec_():
            self.load_vouchers()
            self.show_voucher_details(voucher_id)
    
    def delete_voucher(self):
        """حذف سند"""
        current_row = self.vouchers_table.currentRow()
        if current_row < 0 or current_row >= len(self.vouchers_data):
            QMessageBox.warning(self, "خطا", "لطفاً یک سند انتخاب کنید!")
            return
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            "آیا از حذف این سند اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            voucher_id = self.vouchers_data[current_row]['id']
            with get_db() as conn:
                c = conn.cursor()
                c.execute('DELETE FROM voucher_items WHERE voucher_id = ?', [voucher_id])
                c.execute('DELETE FROM vouchers WHERE id = ?', [voucher_id])
            
            self.load_vouchers()
            self.details_text.clear()
            QMessageBox.information(self, "موفق", "سند با موفقیت حذف شد!")
    
    def show_trial_balance(self):
        """نمایش تراز آزمایشی"""
        date = self.trial_date.date().toString("yyyy-MM-dd")
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT 
                    a.code,
                    a.name,
                    a.type,
                    COALESCE(SUM(vi.debit), 0) as debit,
                    COALESCE(SUM(vi.credit), 0) as credit
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE v.date <= ? OR v.date IS NULL
                GROUP BY a.code, a.name, a.type
                ORDER BY a.code
            ''', [date])
            
            trial_data = c.fetchall()
        
        html = f"""
        <h3>تراز آزمایشی - {date}</h3>
        <table width='100%' border='1' style='border-collapse: collapse; font-size: 11px;'>
        <tr>
            <th>کد</th><th>نام حساب</th><th>بدهکار</th><th>بستانکار</th>
            <th>مانده بدهکار</th><th>مانده بستانکار</th>
        </tr>
        """
        
        total_debit = 0
        total_credit = 0
        total_balance_debit = 0
        total_balance_credit = 0
        
        for row in trial_data:
            code = row['code']
            name = row['name']
            acc_type = row['type']
            debit = row['debit'] or 0
            credit = row['credit'] or 0
            
            if acc_type in ['asset', 'expense']:
                balance = debit - credit
                balance_debit = balance if balance > 0 else 0
                balance_credit = -balance if balance < 0 else 0
            else:
                balance = credit - debit
                balance_debit = -balance if balance < 0 else 0
                balance_credit = balance if balance > 0 else 0
            
            if debit > 0 or credit > 0:
                html += f"""
                <tr>
                    <td>{code}</td><td>{name}</td>
                    <td style='text-align: right;'>{debit:,.0f}</td>
                    <td style='text-align: right;'>{credit:,.0f}</td>
                    <td style='text-align: right;'>{balance_debit:,.0f}</td>
                    <td style='text-align: right;'>{balance_credit:,.0f}</td>
                </tr>
                """
                
                total_debit += debit
                total_credit += credit
                total_balance_debit += balance_debit
                total_balance_credit += balance_credit
        
        html += f"""
        <tr style='font-weight: bold; background-color: #f0f0f0;'>
            <td colspan='2'>جمع</td>
            <td style='text-align: right;'>{total_debit:,.0f}</td>
            <td style='text-align: right;'>{total_credit:,.0f}</td>
            <td style='text-align: right;'>{total_balance_debit:,.0f}</td>
            <td style='text-align: right;'>{total_balance_credit:,.0f}</td>
        </tr>
        </table>
        """
        
        self.trial_text.setHtml(html)


class VoucherDialog(QDialog):
    """دیالوگ ایجاد/ویرایش سند حسابداری"""
    
    def __init__(self, accounts, voucher_id=None):
        super().__init__()
        self.accounts = accounts
        self.voucher_id = voucher_id
        self.setWindowTitle("سند حسابداری")
        self.setGeometry(200, 200, 800, 600)
        self.init_ui()
        
        if voucher_id:
            self.load_voucher_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # اطلاعات اصلی سند
        info_group = QGroupBox("اطلاعات سند")
        info_layout = QFormLayout()
        
        self.voucher_no = QSpinBox()
        self.voucher_no.setRange(1, 999999)
        if not self.voucher_id:
            self.voucher_no.setValue(self.get_next_voucher_no())
        info_layout.addRow("شماره سند:", self.voucher_no)
        
        self.date = QDateEdit()
        self.date.setDate(QDate.currentDate())
        self.date.setCalendarPopup(True)
        info_layout.addRow("تاریخ:", self.date)
        
        self.description = QLineEdit()
        info_layout.addRow("شرح:", self.description)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["عادی", "افتتاحیه", "اختتامیه", "اصلاحی"])
        info_layout.addRow("نوع سند:", self.type_combo)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # اقلام سند
        items_group = QGroupBox("اقلام سند")
        items_layout = QVBoxLayout()
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels([
            "کد حساب", "نام حساب", "شرح", "بدهکار", "بستانکار"
        ])
        self.items_table.horizontalHeader().setStretchLastSection(True)
        items_layout.addWidget(self.items_table)
        
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ افزودن ردیف")
        add_btn.clicked.connect(self.add_item_row)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("➖ حذف ردیف")
        remove_btn.clicked.connect(self.remove_item_row)
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        
        self.total_label = QLabel("جمع بدهکار: ۰ | جمع بستانکار: ۰")
        self.total_label.setStyleSheet("font-weight: bold; padding: 5px;")
        btn_layout.addWidget(self.total_label)
        
        items_layout.addLayout(btn_layout)
        items_group.setLayout(items_layout)
        layout.addWidget(items_group)
        
        # دکمه‌ها
        dialog_btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog_btns.accepted.connect(self.accept)
        dialog_btns.rejected.connect(self.reject)
        layout.addWidget(dialog_btns)
        
        self.items_table.cellChanged.connect(self.update_totals)
    
    def get_next_voucher_no(self):
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT MAX(voucher_no) FROM vouchers')
            max_no = c.fetchone()[0]
            return (max_no or 0) + 1
    
    def add_item_row(self):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        
        account_combo = QComboBox()
        for acc in self.accounts:
            account_combo.addItem(f"{acc['code']} - {acc['name']}", acc['code'])
        account_combo.currentIndexChanged.connect(lambda: self.on_account_changed(row))
        self.items_table.setCellWidget(row, 0, account_combo)
        
        name_item = QTableWidgetItem("")
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.items_table.setItem(row, 1, name_item)
        
        self.items_table.setItem(row, 2, QTableWidgetItem(""))
        self.items_table.setItem(row, 3, QTableWidgetItem("0"))
        self.items_table.setItem(row, 4, QTableWidgetItem("0"))
        
        if account_combo.count() > 0:
            self.on_account_changed(row)
    
    def on_account_changed(self, row):
        combo = self.items_table.cellWidget(row, 0)
        if combo:
            selected_text = combo.currentText()
            self.items_table.item(row, 1).setText(selected_text.split(" - ")[1])
    
    def remove_item_row(self):
        current_row = self.items_table.currentRow()
        if current_row >= 0:
            self.items_table.removeRow(current_row)
            self.update_totals()
    
    def update_totals(self):
        total_debit = 0
        total_credit = 0
        
        for row in range(self.items_table.rowCount()):
            debit_item = self.items_table.item(row, 3)
            credit_item = self.items_table.item(row, 4)
            
            if debit_item:
                try:
                    total_debit += float(debit_item.text() or 0)
                except:
                    pass
            
            if credit_item:
                try:
                    total_credit += float(credit_item.text() or 0)
                except:
                    pass
        
        self.total_label.setText(f"جمع بدهکار: {total_debit:,.0f} | جمع بستانکار: {total_credit:,.0f}")
        
        if total_debit == total_credit:
            self.total_label.setStyleSheet("font-weight: bold; padding: 5px; color: green;")
        else:
            self.total_label.setStyleSheet("font-weight: bold; padding: 5px; color: red;")
    
    def load_voucher_data(self):
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('SELECT * FROM vouchers WHERE id = ?', [self.voucher_id])
            voucher = c.fetchone()
            
            self.voucher_no.setValue(voucher['voucher_no'])
            self.date.setDate(QDate.fromString(voucher['date'], "yyyy-MM-dd"))
            self.description.setText(voucher['description'])
            
            index = self.type_combo.findText(voucher['type'] or "عادی")
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            
            c.execute('SELECT * FROM voucher_items WHERE voucher_id = ? ORDER BY id', [self.voucher_id])
            items = c.fetchall()
            
            for item in items:
                row = self.items_table.rowCount()
                self.add_item_row()
                
                combo = self.items_table.cellWidget(row, 0)
                for i in range(combo.count()):
                    if combo.itemData(i) == item['account_code']:
                        combo.setCurrentIndex(i)
                        break
                
                self.items_table.item(row, 2).setText(item['description'] or "")
                self.items_table.item(row, 3).setText(str(item['debit']))
                self.items_table.item(row, 4).setText(str(item['credit']))
            
            self.update_totals()
    
    def accept(self):
        if not self.description.text():
            QMessageBox.warning(self, "خطا", "شرح سند را وارد کنید!")
            return
        
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "خطا", "حداقل یک ردیف به سند اضافه کنید!")
            return
        
        total_debit = 0
        total_credit = 0
        items_data = []
        
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 0)
            if not combo:
                continue
            
            account_code = combo.currentData()
            description = self.items_table.item(row, 2).text()
            
            try:
                debit = float(self.items_table.item(row, 3).text() or 0)
                credit = float(self.items_table.item(row, 4).text() or 0)
            except:
                QMessageBox.warning(self, "خطا", f"مقادیر ردیف {row+1} نامعتبر است!")
                return
            
            if debit == 0 and credit == 0:
                QMessageBox.warning(self, "خطا", f"ردیف {row+1} مبلغ ندارد!")
                return
            
            total_debit += debit
            total_credit += credit
            
            items_data.append({
                'account_code': account_code,
                'description': description,
                'debit': debit,
                'credit': credit
            })
        
        if total_debit != total_credit:
            QMessageBox.warning(self, "خطا", f"سند موازنه نیست!\nاختلاف: {abs(total_debit - total_credit):,.0f}")
            return
        
        with get_db() as conn:
            c = conn.cursor()
            
            voucher_data = {
                'voucher_no': self.voucher_no.value(),
                'date': self.date.date().toString("yyyy-MM-dd"),
                'description': self.description.text(),
                'type': self.type_combo.currentText()
            }
            
            if self.voucher_id:
                c.execute('''
                    UPDATE vouchers 
                    SET voucher_no=?, date=?, description=?, type=?
                    WHERE id=?
                ''', [voucher_data['voucher_no'], voucher_data['date'], 
                      voucher_data['description'], voucher_data['type'], self.voucher_id])
                
                c.execute('DELETE FROM voucher_items WHERE voucher_id = ?', [self.voucher_id])
                voucher_id = self.voucher_id
            else:
                c.execute('''
                    INSERT INTO vouchers (voucher_no, date, description, type)
                    VALUES (?, ?, ?, ?)
                ''', [voucher_data['voucher_no'], voucher_data['date'], 
                      voucher_data['description'], voucher_data['type']])
                voucher_id = c.lastrowid
            
            for item in items_data:
                c.execute('''
                    INSERT INTO voucher_items (voucher_id, account_code, description, debit, credit)
                    VALUES (?, ?, ?, ?, ?)
                ''', [voucher_id, item['account_code'], item['description'], 
                      item['debit'], item['credit']])
        
        QMessageBox.information(self, "موفق", "سند با موفقیت ذخیره شد!")
        super().accept()
