#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ویجت گزارشات - شامل تراز آزمایشی، سود و زیان، ترازنامه، گزارش انبار و گزارش حقوق
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
from database import get_db, AccountingHelper


class ReportsWidget(QWidget):
    """ویجت اصلی گزارشات"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # عنوان
        title = QLabel("📊 گزارشات")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; padding: 10px; color: #2C3E50;")
        layout.addWidget(title)
        
        # تب‌های گزارشات
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # تب ۱: تراز آزمایشی
        self.tab_widget.addTab(self.create_trial_balance_tab(), "📋 تراز آزمایشی")
        
        # تب ۲: سود و زیان
        self.tab_widget.addTab(self.create_profit_loss_tab(), "💰 سود و زیان")
        
        # تب ۳: ترازنامه
        self.tab_widget.addTab(self.create_balance_sheet_tab(), "📊 ترازنامه")
        
        # تب ۴: گزارش انبار
        self.tab_widget.addTab(self.create_inventory_report_tab(), "📦 گزارش انبار")
        
        # تب ۵: گزارش حقوق
        self.tab_widget.addTab(self.create_payroll_report_tab(), "💵 گزارش حقوق")
    
    # ============================================================
    # تب ۱: تراز آزمایشی
    # ============================================================
    def create_trial_balance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # کنترل‌ها
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("تاریخ:"))
        self.trial_date = QDateEdit()
        self.trial_date.setDate(QDate.currentDate())
        self.trial_date.setCalendarPopup(True)
        control_layout.addWidget(self.trial_date)
        
        show_btn = QPushButton("📊 نمایش تراز")
        show_btn.setObjectName("successBtn")
        show_btn.clicked.connect(self.show_trial_balance)
        control_layout.addWidget(show_btn)
        
        export_btn = QPushButton("📎 خروجی Excel")
        export_btn.clicked.connect(lambda: self.export_to_excel("trial"))
        control_layout.addWidget(export_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # جدول گزارش
        self.trial_table = QTableWidget()
        self.trial_table.setColumnCount(6)
        self.trial_table.setHorizontalHeaderLabels([
            "کد حساب", "نام حساب", "گردش بدهکار", "گردش بستانکار",
            "مانده بدهکار", "مانده بستانکار"
        ])
        self.trial_table.setAlternatingRowColors(True)
        layout.addWidget(self.trial_table)
        
        # جمع
        self.trial_total_label = QLabel()
        self.trial_total_label.setStyleSheet("font-weight: bold; padding: 10px; background: #f0f0f0; border-radius: 5px;")
        layout.addWidget(self.trial_total_label)
        
        # نمایش اولیه
        QTimer.singleShot(100, self.show_trial_balance)
        
        return widget
    
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
            
            data = c.fetchall()
        
        self.trial_table.setRowCount(len(data))
        
        total_debit = 0
        total_credit = 0
        total_balance_debit = 0
        total_balance_credit = 0
        
        for i, row in enumerate(data):
            self.trial_table.setItem(i, 0, QTableWidgetItem(row['code']))
            self.trial_table.setItem(i, 1, QTableWidgetItem(row['name']))
            
            debit = row['debit'] or 0
            credit = row['credit'] or 0
            
            debit_item = QTableWidgetItem(f"{debit:,.0f}")
            debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trial_table.setItem(i, 2, debit_item)
            
            credit_item = QTableWidgetItem(f"{credit:,.0f}")
            credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trial_table.setItem(i, 3, credit_item)
            
            # محاسبه مانده
            if row['type'] in ['asset', 'expense']:
                balance = debit - credit
                balance_debit = balance if balance > 0 else 0
                balance_credit = -balance if balance < 0 else 0
            else:
                balance = credit - debit
                balance_debit = -balance if balance < 0 else 0
                balance_credit = balance if balance > 0 else 0
            
            bal_debit_item = QTableWidgetItem(f"{balance_debit:,.0f}" if balance_debit > 0 else "-")
            bal_debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trial_table.setItem(i, 4, bal_debit_item)
            
            bal_credit_item = QTableWidgetItem(f"{balance_credit:,.0f}" if balance_credit > 0 else "-")
            bal_credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trial_table.setItem(i, 5, bal_credit_item)
            
            total_debit += debit
            total_credit += credit
            total_balance_debit += balance_debit
            total_balance_credit += balance_credit
        
        self.trial_total_label.setText(
            f"📊 جمع گردش: بدهکار {total_debit:,.0f} | بستانکار {total_credit:,.0f} | "
            f"جمع مانده: بدهکار {total_balance_debit:,.0f} | بستانکار {total_balance_credit:,.0f}"
        )
    
    # ============================================================
    # تب ۲: سود و زیان
    # ============================================================
    def create_profit_loss_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # کنترل‌ها
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("از تاریخ:"))
        self.pl_from_date = QDateEdit()
        self.pl_from_date.setDate(QDate.currentDate().addMonths(-1))
        self.pl_from_date.setCalendarPopup(True)
        control_layout.addWidget(self.pl_from_date)
        
        control_layout.addWidget(QLabel("تا تاریخ:"))
        self.pl_to_date = QDateEdit()
        self.pl_to_date.setDate(QDate.currentDate())
        self.pl_to_date.setCalendarPopup(True)
        control_layout.addWidget(self.pl_to_date)
        
        show_btn = QPushButton("💰 محاسبه سود و زیان")
        show_btn.setObjectName("successBtn")
        show_btn.clicked.connect(self.show_profit_loss)
        control_layout.addWidget(show_btn)
        
        export_btn = QPushButton("📎 خروجی Excel")
        export_btn.clicked.connect(lambda: self.export_to_excel("profit_loss"))
        control_layout.addWidget(export_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # متن گزارش
        self.pl_text = QTextEdit()
        self.pl_text.setReadOnly(True)
        self.pl_text.setStyleSheet("font-family: Tahoma; font-size: 11pt;")
        layout.addWidget(self.pl_text)
        
        # نمایش اولیه
        QTimer.singleShot(100, self.show_profit_loss)
        
        return widget
    
    def show_profit_loss(self):
        """نمایش گزارش سود و زیان"""
        from_date = self.pl_from_date.date().toString("yyyy-MM-dd")
        to_date = self.pl_to_date.date().toString("yyyy-MM-dd")
        
        with get_db() as conn:
            c = conn.cursor()
            
            # درآمدها
            c.execute('''
                SELECT a.code, a.name, COALESCE(SUM(vi.credit - vi.debit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'income' 
                AND (v.date BETWEEN ? AND ? OR v.date IS NULL)
                GROUP BY a.code, a.name
                ORDER BY a.code
            ''', [from_date, to_date])
            incomes = c.fetchall()
            
            # هزینه‌ها
            c.execute('''
                SELECT a.code, a.name, COALESCE(SUM(vi.debit - vi.credit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'expense' 
                AND (v.date BETWEEN ? AND ? OR v.date IS NULL)
                GROUP BY a.code, a.name
                ORDER BY a.code
            ''', [from_date, to_date])
            expenses = c.fetchall()
        
        html = f"""
        <div style='font-family: Tahoma;'>
            <h2 style='text-align: center; color: #2C3E50;'>📊 گزارش سود و زیان</h2>
            <p style='text-align: center; color: #666;'>از تاریخ {from_date} تا {to_date}</p>
            <hr>
            
            <h3 style='color: #27ae60;'>💰 درآمدها:</h3>
            <table width='100%' style='border-collapse: collapse;'>
        """
        
        total_income = 0
        for inc in incomes:
            balance = inc['balance'] or 0
            if balance != 0:
                html += f"""
                <tr>
                    <td>{inc['name']}</td>
                    <td style='text-align: right;'>{balance:,.0f} ریال</td>
                </tr>
                """
                total_income += balance
        
        html += f"""
                <tr style='font-weight: bold; background: #f0f0f0;'>
                    <td>جمع درآمدها</td>
                    <td style='text-align: right;'>{total_income:,.0f} ریال</td>
                </tr>
            </table>
            
            <h3 style='color: #e84118; margin-top: 30px;'>💸 هزینه‌ها:</h3>
            <table width='100%' style='border-collapse: collapse;'>
        """
        
        total_expense = 0
        for exp in expenses:
            balance = exp['balance'] or 0
            if balance != 0:
                html += f"""
                <tr>
                    <td>{exp['name']}</td>
                    <td style='text-align: right;'>{balance:,.0f} ریال</td>
                </tr>
                """
                total_expense += balance
        
        html += f"""
                <tr style='font-weight: bold; background: #f0f0f0;'>
                    <td>جمع هزینه‌ها</td>
                    <td style='text-align: right;'>{total_expense:,.0f} ریال</td>
                </tr>
            </table>
        """
        
        net_profit = total_income - total_expense
        
        if net_profit >= 0:
            html += f"""
            <hr>
            <h2 style='text-align: center; color: #27ae60;'>
                ✅ سود خالص: {net_profit:,.0f} ریال
            </h2>
            """
        else:
            html += f"""
            <hr>
            <h2 style='text-align: center; color: #e84118;'>
                ❌ زیان خالص: {abs(net_profit):,.0f} ریال
            </h2>
            """
        
        html += "</div>"
        self.pl_text.setHtml(html)
    
    # ============================================================
    # تب ۳: ترازنامه
    # ============================================================
    def create_balance_sheet_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # کنترل‌ها
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("تاریخ:"))
        self.bs_date = QDateEdit()
        self.bs_date.setDate(QDate.currentDate())
        self.bs_date.setCalendarPopup(True)
        control_layout.addWidget(self.bs_date)
        
        show_btn = QPushButton("📊 نمایش ترازنامه")
        show_btn.setObjectName("successBtn")
        show_btn.clicked.connect(self.show_balance_sheet)
        control_layout.addWidget(show_btn)
        
        export_btn = QPushButton("📎 خروجی Excel")
        export_btn.clicked.connect(lambda: self.export_to_excel("balance_sheet"))
        control_layout.addWidget(export_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # متن گزارش
        self.bs_text = QTextEdit()
        self.bs_text.setReadOnly(True)
        self.bs_text.setStyleSheet("font-family: Tahoma; font-size: 11pt;")
        layout.addWidget(self.bs_text)
        
        # نمایش اولیه
        QTimer.singleShot(100, self.show_balance_sheet)
        
        return widget
    
    def show_balance_sheet(self):
        """نمایش ترازنامه"""
        date = self.bs_date.date().toString("yyyy-MM-dd")
        
        with get_db() as conn:
            c = conn.cursor()
            
            # دارایی‌ها
            c.execute('''
                SELECT a.code, a.name, 
                       COALESCE(SUM(vi.debit - vi.credit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'asset' AND (v.date <= ? OR v.date IS NULL)
                GROUP BY a.code, a.name
                ORDER BY a.code
            ''', [date])
            assets = c.fetchall()
            
            # بدهی‌ها
            c.execute('''
                SELECT a.code, a.name, 
                       COALESCE(SUM(vi.credit - vi.debit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'liability' AND (v.date <= ? OR v.date IS NULL)
                GROUP BY a.code, a.name
                ORDER BY a.code
            ''', [date])
            liabilities = c.fetchall()
            
            # سرمایه
            c.execute('''
                SELECT a.code, a.name, 
                       COALESCE(SUM(vi.credit - vi.debit), 0) as balance
                FROM accounts a
                LEFT JOIN voucher_items vi ON a.code = vi.account_code
                LEFT JOIN vouchers v ON vi.voucher_id = v.id
                WHERE a.type = 'equity' AND (v.date <= ? OR v.date IS NULL)
                GROUP BY a.code, a.name
                ORDER BY a.code
            ''', [date])
            equity = c.fetchall()
        
        total_assets = sum(a['balance'] or 0 for a in assets)
        total_liabilities = sum(l['balance'] or 0 for l in liabilities)
        total_equity = sum(e['balance'] or 0 for e in equity)
        
        html = f"""
        <div style='font-family: Tahoma;'>
            <h2 style='text-align: center; color: #2C3E50;'>📊 ترازنامه</h2>
            <p style='text-align: center; color: #666;'>تاریخ: {date}</p>
            <hr>
            
            <h3 style='color: #2980b9;'>🏢 دارایی‌ها:</h3>
            <table width='100%' style='border-collapse: collapse;'>
        """
        
        for asset in assets:
            balance = asset['balance'] or 0
            if balance != 0:
                html += f"""
                <tr>
                    <td>{asset['name']}</td>
                    <td style='text-align: right;'>{balance:,.0f} ریال</td>
                </tr>
                """
        
        html += f"""
                <tr style='font-weight: bold; background: #f0f0f0;'>
                    <td>جمع دارایی‌ها</td>
                    <td style='text-align: right;'>{total_assets:,.0f} ریال</td>
                </tr>
            </table>
            
            <h3 style='color: #e67e22; margin-top: 30px;'>📋 بدهی‌ها:</h3>
            <table width='100%' style='border-collapse: collapse;'>
        """
        
        for liability in liabilities:
            balance = liability['balance'] or 0
            if balance != 0:
                html += f"""
                <tr>
                    <td>{liability['name']}</td>
                    <td style='text-align: right;'>{balance:,.0f} ریال</td>
                </tr>
                """
        
        html += f"""
                <tr style='font-weight: bold; background: #f0f0f0;'>
                    <td>جمع بدهی‌ها</td>
                    <td style='text-align: right;'>{total_liabilities:,.0f} ریال</td>
                </tr>
            </table>
            
            <h3 style='color: #8e44ad; margin-top: 30px;'>💰 سرمایه:</h3>
            <table width='100%' style='border-collapse: collapse;'>
        """
        
        for eq in equity:
            balance = eq['balance'] or 0
            if balance != 0:
                html += f"""
                <tr>
                    <td>{eq['name']}</td>
                    <td style='text-align: right;'>{balance:,.0f} ریال</td>
                </tr>
                """
        
        html += f"""
                <tr style='font-weight: bold; background: #f0f0f0;'>
                    <td>جمع سرمایه</td>
                    <td style='text-align: right;'>{total_equity:,.0f} ریال</td>
                </tr>
            </table>
            
            <hr>
            <h3 style='text-align: center; color: #2C3E50;'>
                📊 جمع بدهی‌ها و سرمایه: {(total_liabilities + total_equity):,.0f} ریال
            </h3>
        """
        
        if abs(total_assets - (total_liabilities + total_equity)) < 1:
            html += """
            <h3 style='text-align: center; color: #27ae60;'>
                ✅ ترازنامه موازنه است
            </h3>
            """
        else:
            diff = total_assets - (total_liabilities + total_equity)
            html += f"""
            <h3 style='text-align: center; color: #e84118;'>
                ⚠️ عدم موازنه: {diff:,.0f} ریال
            </h3>
            """
        
        html += "</div>"
        self.bs_text.setHtml(html)
    
    # ============================================================
    # تب ۴: گزارش انبار
    # ============================================================
    def create_inventory_report_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # کنترل‌ها
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("نوع گزارش:"))
        self.inv_report_type = QComboBox()
        self.inv_report_type.addItems([
            "📋 لیست موجودی کالاها",
            "📊 ارزش موجودی انبار",
            "⚠️ کالاهای زیر حداقل",
            "📈 پرگردش‌ترین کالاها"
        ])
        control_layout.addWidget(self.inv_report_type)
        
        show_btn = QPushButton("📊 نمایش گزارش")
        show_btn.setObjectName("successBtn")
        show_btn.clicked.connect(self.show_inventory_report)
        control_layout.addWidget(show_btn)
        
        export_btn = QPushButton("📎 خروجی Excel")
        export_btn.clicked.connect(lambda: self.export_to_excel("inventory"))
        control_layout.addWidget(export_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # جدول گزارش
        self.inv_table = QTableWidget()
        self.inv_table.setAlternatingRowColors(True)
        layout.addWidget(self.inv_table)
        
        # جمع
        self.inv_total_label = QLabel()
        self.inv_total_label.setStyleSheet("font-weight: bold; padding: 10px; background: #f0f0f0; border-radius: 5px;")
        layout.addWidget(self.inv_total_label)
        
        # نمایش اولیه
        QTimer.singleShot(100, self.show_inventory_report)
        
        return widget
    
    def show_inventory_report(self):
        """نمایش گزارش انبار"""
        report_type = self.inv_report_type.currentIndex()
        
        with get_db() as conn:
            c = conn.cursor()
            
            if report_type == 0:  # لیست موجودی
                c.execute('''
                    SELECT code, name, unit, stock, purchase_price, sale_price,
                           (stock * purchase_price) as total_value
                    FROM products
                    ORDER BY code
                ''')
                data = c.fetchall()
                
                self.inv_table.setColumnCount(7)
                self.inv_table.setHorizontalHeaderLabels([
                    "کد", "نام کالا", "واحد", "موجودی", "قیمت خرید", "قیمت فروش", "ارزش موجودی"
                ])
                
            elif report_type == 1:  # ارزش موجودی
                c.execute('''
                    SELECT code, name, unit, stock, purchase_price,
                           (stock * purchase_price) as total_value
                    FROM products
                    WHERE stock > 0
                    ORDER BY total_value DESC
                ''')
                data = c.fetchall()
                
                self.inv_table.setColumnCount(6)
                self.inv_table.setHorizontalHeaderLabels([
                    "کد", "نام کالا", "واحد", "موجودی", "قیمت خرید", "ارزش موجودی"
                ])
                
            elif report_type == 2:  # زیر حداقل
                c.execute('''
                    SELECT code, name, unit, stock, min_stock, (min_stock - stock) as shortage
                    FROM products
                    WHERE stock <= min_stock AND min_stock > 0
                    ORDER BY shortage DESC
                ''')
                data = c.fetchall()
                
                self.inv_table.setColumnCount(6)
                self.inv_table.setHorizontalHeaderLabels([
                    "کد", "نام کالا", "واحد", "موجودی", "حداقل", "کسری"
                ])
                
            else:  # پرگردش‌ترین
                c.execute('''
                    SELECT p.code, p.name, p.unit, p.stock,
                           COUNT(st.id) as trans_count,
                           COALESCE(SUM(CASE WHEN st.type='out' THEN st.quantity ELSE 0 END), 0) as total_out
                    FROM products p
                    LEFT JOIN stock_transactions st ON p.id = st.product_id
                    GROUP BY p.id, p.code, p.name, p.unit, p.stock
                    ORDER BY trans_count DESC, total_out DESC
                    LIMIT 20
                ''')
                data = c.fetchall()
                
                self.inv_table.setColumnCount(6)
                self.inv_table.setHorizontalHeaderLabels([
                    "کد", "نام کالا", "واحد", "موجودی", "تعداد تراکنش", "مقدار خروجی"
                ])
        
        self.inv_table.setRowCount(len(data))
        
        total_value = 0
        for i, row in enumerate(data):
            for j, val in enumerate(row):
                if j >= 3 and report_type != 2:  # ستون‌های عددی
                    if val is not None:
                        item = QTableWidgetItem(f"{val:,.2f}" if isinstance(val, float) else f"{val:,}")
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    else:
                        item = QTableWidgetItem("-")
                else:
                    item = QTableWidgetItem(str(val) if val else "-")
                self.inv_table.setItem(i, j, item)
            
            # محاسبه ارزش کل برای گزارش نوع ۰ و ۱
            if report_type in [0, 1] and len(row) >= 6:
                total_value += row[5] or 0 if report_type == 1 else row[6] or 0
        
        if report_type in [0, 1]:
            self.inv_total_label.setText(f"💰 ارزش کل موجودی انبار: {total_value:,.0f} ریال")
        elif report_type == 2:
            self.inv_total_label.setText(f"⚠️ {len(data)} کالا زیر حداقل موجودی قرار دارند")
        else:
            self.inv_total_label.setText(f"📊 {len(data)} کالا در این گزارش")
    
    # ============================================================
    # تب ۵: گزارش حقوق
    # ============================================================
    def create_payroll_report_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # کنترل‌ها
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("سال:"))
        self.payroll_year = QSpinBox()
        self.payroll_year.setRange(1390, 1450)
        self.payroll_year.setValue(datetime.now().year if datetime.now().year > 1400 else 1403)
        control_layout.addWidget(self.payroll_year)
        
        control_layout.addWidget(QLabel("ماه:"))
        self.payroll_month = QComboBox()
        self.payroll_month.addItems([
            "همه", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ])
        control_layout.addWidget(self.payroll_month)
        
        control_layout.addWidget(QLabel("نوع گزارش:"))
        self.payroll_report_type = QComboBox()
        self.payroll_report_type.addItems([
            "📋 لیست حقوق ماهانه",
            "📊 خلاصه حقوق سالانه",
            "💰 گزارش پرداختی‌ها",
            "⏳ حقوق‌های پرداخت نشده"
        ])
        control_layout.addWidget(self.payroll_report_type)
        
        show_btn = QPushButton("📊 نمایش گزارش")
        show_btn.setObjectName("successBtn")
        show_btn.clicked.connect(self.show_payroll_report)
        control_layout.addWidget(show_btn)
        
        export_btn = QPushButton("📎 خروجی Excel")
        export_btn.clicked.connect(lambda: self.export_to_excel("payroll"))
        control_layout.addWidget(export_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # جدول گزارش
        self.payroll_table = QTableWidget()
        self.payroll_table.setAlternatingRowColors(True)
        layout.addWidget(self.payroll_table)
        
        # جمع
        self.payroll_total_label = QLabel()
        self.payroll_total_label.setStyleSheet("font-weight: bold; padding: 10px; background: #f0f0f0; border-radius: 5px;")
        layout.addWidget(self.payroll_total_label)
        
        # نمایش اولیه
        QTimer.singleShot(100, self.show_payroll_report)
        
        return widget
    
    def show_payroll_report(self):
        """نمایش گزارش حقوق"""
        year = self.payroll_year.value()
        month_idx = self.payroll_month.currentIndex()
        report_type = self.payroll_report_type.currentIndex()
        
        month_names = [
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ]
        
        with get_db() as conn:
            c = conn.cursor()
            
            if report_type == 0:  # لیست حقوق ماهانه
                if month_idx == 0:  # همه ماه‌ها
                    query = '''
                        SELECT e.code, e.name, p.year, p.month, p.work_days, 
                               p.overtime_hours, p.bonus, p.deduction, p.net_salary, p.payment_status
                        FROM payrolls p
                        JOIN employees e ON p.employee_id = e.id
                        WHERE p.year = ?
                        ORDER BY p.month, e.code
                    '''
                    c.execute(query, [year])
                else:
                    query = '''
                        SELECT e.code, e.name, p.year, p.month, p.work_days, 
                               p.overtime_hours, p.bonus, p.deduction, p.net_salary, p.payment_status
                        FROM payrolls p
                        JOIN employees e ON p.employee_id = e.id
                        WHERE p.year = ? AND p.month = ?
                        ORDER BY e.code
                    '''
                    c.execute(query, [year, month_idx])
                
                data = c.fetchall()
                
                self.payroll_table.setColumnCount(10)
                self.payroll_table.setHorizontalHeaderLabels([
                    "کد", "نام", "سال", "ماه", "روز کارکرد", "اضافه کاری",
                    "پاداش", "کسورات", "خالص", "وضعیت"
                ])
                
            elif report_type == 1:  # خلاصه حقوق سالانه
                query = '''
                    SELECT e.code, e.name, 
                           COUNT(p.id) as months_paid,
                           COALESCE(SUM(p.net_salary), 0) as total_paid,
                           COALESCE(AVG(p.net_salary), 0) as avg_salary
                    FROM employees e
                    LEFT JOIN payrolls p ON e.id = p.employee_id AND p.year = ? AND p.payment_status = 'paid'
                    WHERE e.is_active = 1
                    GROUP BY e.id, e.code, e.name
                    ORDER BY e.code
                '''
                c.execute(query, [year])
                data = c.fetchall()
                
                self.payroll_table.setColumnCount(5)
                self.payroll_table.setHorizontalHeaderLabels([
                    "کد", "نام", "ماه‌های پرداخت", "جمع پرداختی", "میانگین ماهانه"
                ])
                
            elif report_type == 2:  # گزارش پرداختی‌ها
                query = '''
                    SELECT e.code, e.name, p.year, p.month, p.net_salary, p.payment_date
                    FROM payrolls p
                    JOIN employees e ON p.employee_id = e.id
                    WHERE p.payment_status = 'paid'
                    ORDER BY p.payment_date DESC, e.code
                    LIMIT 50
                '''
                c.execute(query)
                data = c.fetchall()
                
                self.payroll_table.setColumnCount(6)
                self.payroll_table.setHorizontalHeaderLabels([
                    "کد", "نام", "سال", "ماه", "مبلغ", "تاریخ پرداخت"
                ])
                
            else:  # حقوق‌های پرداخت نشده
                query = '''
                    SELECT e.code, e.name, p.year, p.month, p.net_salary
                    FROM payrolls p
                    JOIN employees e ON p.employee_id = e.id
                    WHERE p.payment_status = 'pending'
                    ORDER BY p.year, p.month, e.code
                '''
                c.execute(query)
                data = c.fetchall()
                
                self.payroll_table.setColumnCount(5)
                self.payroll_table.setHorizontalHeaderLabels([
                    "کد", "نام", "سال", "ماه", "مبلغ قابل پرداخت"
                ])
        
        self.payroll_table.setRowCount(len(data))
        
        total_salary = 0
        for i, row in enumerate(data):
            for j, val in enumerate(row):
                if val is None:
                    item = QTableWidgetItem("-")
                elif isinstance(val, (int, float)):
                    if j >= 4 and report_type == 0:  # ستون‌های عددی در گزارش ماهانه
                        item = QTableWidgetItem(f"{val:,.0f}")
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    elif report_type == 0 and j == 9:  # وضعیت
                        status_text = {
                            'pending': '⏳ در انتظار',
                            'paid': '✅ پرداخت شده',
                            'cancelled': '❌ لغو'
                        }.get(val, val)
                        item = QTableWidgetItem(status_text)
                        if val == 'paid':
                            item.setForeground(QColor('#27ae60'))
                        elif val == 'pending':
                            item.setForeground(QColor('#f39c12'))
                    elif report_type == 1 and j >= 2:  # ستون‌های عددی در گزارش سالانه
                        item = QTableWidgetItem(f"{val:,.0f}")
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    elif report_type == 2 and j == 4:  # مبلغ
                        item = QTableWidgetItem(f"{val:,.0f}")
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        total_salary += val
                    elif report_type == 3 and j == 4:  # مبلغ قابل پرداخت
                        item = QTableWidgetItem(f"{val:,.0f}")
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        total_salary += val
                    else:
                        item = QTableWidgetItem(str(val))
                elif j == 3 and report_type == 0:  # نام ماه
                    item = QTableWidgetItem(month_names[val-1] if 1 <= val <= 12 else str(val))
                elif j == 2 and report_type == 2:  # نام ماه در پرداختی‌ها
                    item = QTableWidgetItem(month_names[val-1] if 1 <= val <= 12 else str(val))
                elif j == 3 and report_type == 3:  # نام ماه در پرداخت نشده
                    item = QTableWidgetItem(month_names[val-1] if 1 <= val <= 12 else str(val))
                else:
                    item = QTableWidgetItem(str(val))
                
                self.payroll_table.setItem(i, j, item)
        
        if report_type == 2:
            self.payroll_total_label.setText(f"💰 جمع پرداختی‌ها: {total_salary:,.0f} ریال")
        elif report_type == 3:
            self.payroll_total_label.setText(f"💰 جمع بدهی حقوق: {total_salary:,.0f} ریال")
        else:
            self.payroll_total_label.setText(f"📊 {len(data)} رکورد در این گزارش")
    
    # ============================================================
    # خروجی Excel
    # ============================================================
    def export_to_excel(self, report_type):
        """خروجی گرفتن به فرمت CSV (قابل باز شدن با Excel)"""
        import csv
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "ذخیره گزارش", f"{report_type}_report_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not file_name:
            return
        
        try:
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                
                if report_type == "trial":
                    # هدر
                    headers = ["کد حساب", "نام حساب", "گردش بدهکار", "گردش بستانکار", "مانده بدهکار", "مانده بستانکار"]
                    writer.writerow(headers)
                    
                    # داده‌ها
                    for row in range(self.trial_table.rowCount()):
                        row_data = []
                        for col in range(self.trial_table.columnCount()):
                            item = self.trial_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
                    
                    # جمع
                    writer.writerow([])
                    writer.writerow(["", "", "", "", "", ""])
                    writer.writerow(["جمع", "", self.trial_total_label.text(), "", "", ""])
                
                elif report_type == "inventory":
                    headers = []
                    for col in range(self.inv_table.columnCount()):
                        headers.append(self.inv_table.horizontalHeaderItem(col).text())
                    writer.writerow(headers)
                    
                    for row in range(self.inv_table.rowCount()):
                        row_data = []
                        for col in range(self.inv_table.columnCount()):
                            item = self.inv_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
                    
                    writer.writerow([])
                    writer.writerow([self.inv_total_label.text(), "", "", "", ""])
                
                elif report_type == "payroll":
                    headers = []
                    for col in range(self.payroll_table.columnCount()):
                        headers.append(self.payroll_table.horizontalHeaderItem(col).text())
                    writer.writerow(headers)
                    
                    for row in range(self.payroll_table.rowCount()):
                        row_data = []
                        for col in range(self.payroll_table.columnCount()):
                            item = self.payroll_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
                    
                    writer.writerow([])
                    writer.writerow([self.payroll_total_label.text(), "", "", "", ""])
                
                elif report_type == "profit_loss":
                    writer.writerow(["گزارش سود و زیان"])
                    writer.writerow(["از تاریخ", self.pl_from_date.date().toString("yyyy-MM-dd")])
                    writer.writerow(["تا تاریخ", self.pl_to_date.date().toString("yyyy-MM-dd")])
                    writer.writerow([])
                    writer.writerow(["متن گزارش:", self.pl_text.toPlainText()])
                
                elif report_type == "balance_sheet":
                    writer.writerow(["ترازنامه"])
                    writer.writerow(["تاریخ", self.bs_date.date().toString("yyyy-MM-dd")])
                    writer.writerow([])
                    writer.writerow(["متن گزارش:", self.bs_text.toPlainText()])
            
            QMessageBox.information(self, "موفق", f"✅ گزارش با موفقیت در مسیر زیر ذخیره شد:\n{file_name}")
            
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"❌ خطا در ذخیره گزارش:\n{str(e)}")
