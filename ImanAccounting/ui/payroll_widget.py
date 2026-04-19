#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ویجت حقوق و دستمزد - مدیریت پرسنل و محاسبه حقوق
با قابلیت‌های: تعریف، ویرایش، حذف پرسنل - MoneyLineEdit - فیش حقوقی
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
from database import get_db, PayrollHelper


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
# ویجت اصلی حقوق دستمزد
# ============================================================
class PayrollWidget(QWidget):
    """ویجت اصلی مدیریت حقوق و دستمزد"""
    
    def __init__(self):
        super().__init__()
        self.employees_data = []
        self.current_employee = None
        self.init_ui()
        self.load_employees()
    
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # ========== پنل سمت راست (لیست پرسنل) ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # عنوان
        title = QLabel("💰 مدیریت حقوق و دستمزد")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px; color: #2C3E50;")
        right_layout.addWidget(title)
        
        # نوار ابزار
        toolbar = QHBoxLayout()
        
        new_btn = QPushButton("➕ پرسنل جدید")
        new_btn.setObjectName("successBtn")
        new_btn.clicked.connect(self.new_employee)
        toolbar.addWidget(new_btn)
        
        edit_btn = QPushButton("✏️ ویرایش پرسنل")
        edit_btn.clicked.connect(self.edit_employee)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ حذف پرسنل")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.clicked.connect(self.delete_employee)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        right_layout.addLayout(toolbar)
        
        # انتخاب دوره
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("دوره:"))
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1390, 1450)
        self.year_spin.setValue(datetime.now().year if datetime.now().year > 1400 else 1403)
        self.year_spin.valueChanged.connect(self.load_payroll)
        period_layout.addWidget(self.year_spin)
        
        self.month_combo = QComboBox()
        self.month_combo.addItems([
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ])
        self.month_combo.setCurrentIndex(datetime.now().month - 1 if datetime.now().month <= 12 else 0)
        self.month_combo.currentIndexChanged.connect(self.load_payroll)
        period_layout.addWidget(self.month_combo)
        
        period_layout.addStretch()
        right_layout.addLayout(period_layout)
        
        # جدول پرسنل و حقوق
        self.payroll_table = QTableWidget()
        self.payroll_table.setColumnCount(9)
        self.payroll_table.setHorizontalHeaderLabels([
            "کد", "نام", "حقوق پایه", "روز کارکرد", "اضافه کاری",
            "پاداش", "کسورات", "خالص پرداختی", "وضعیت"
        ])
        self.payroll_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.payroll_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.payroll_table.horizontalHeader().setStretchLastSection(True)
        self.payroll_table.clicked.connect(self.on_employee_selected)
        self.payroll_table.doubleClicked.connect(self.calculate_payroll_for_selected)
        right_layout.addWidget(self.payroll_table)
        
        # دکمه‌های عملیات حقوق
        action_layout = QHBoxLayout()
        
        calc_btn = QPushButton("🧮 محاسبه حقوق")
        calc_btn.setObjectName("successBtn")
        calc_btn.clicked.connect(self.calculate_payroll_for_selected)
        action_layout.addWidget(calc_btn)
        
        payment_btn = QPushButton("💳 ثبت پرداخت")
        payment_btn.clicked.connect(self.register_payment)
        action_layout.addWidget(payment_btn)
        
        action_layout.addStretch()
        right_layout.addLayout(action_layout)
        
        # ========== پنل سمت چپ (جزئیات) ==========
        left_panel = QWidget()
        left_panel.setMaximumWidth(450)
        left_layout = QVBoxLayout(left_panel)
        
        # اطلاعات پرسنل
        info_group = QGroupBox("📋 اطلاعات پرسنل")
        info_layout = QFormLayout()
        
        self.emp_code = QLineEdit()
        self.emp_code.setReadOnly(True)
        info_layout.addRow("کد پرسنلی:", self.emp_code)
        
        self.emp_name = QLineEdit()
        self.emp_name.setReadOnly(True)
        info_layout.addRow("نام:", self.emp_name)
        
        self.emp_national = QLineEdit()
        self.emp_national.setReadOnly(True)
        info_layout.addRow("کد ملی:", self.emp_national)
        
        self.emp_position = QLineEdit()
        self.emp_position.setReadOnly(True)
        info_layout.addRow("سمت:", self.emp_position)
        
        self.emp_salary = QLineEdit()
        self.emp_salary.setReadOnly(True)
        self.emp_salary.setStyleSheet("font-weight: bold; color: #273c75;")
        info_layout.addRow("حقوق پایه:", self.emp_salary)
        
        self.emp_overtime = QLineEdit()
        self.emp_overtime.setReadOnly(True)
        info_layout.addRow("ضریب اضافه کاری:", self.emp_overtime)
        
        self.emp_hire_date = QLineEdit()
        self.emp_hire_date.setReadOnly(True)
        info_layout.addRow("تاریخ استخدام:", self.emp_hire_date)
        
        info_group.setLayout(info_layout)
        left_layout.addWidget(info_group)
        
        # دکمه‌های سریع
        quick_btn_layout = QHBoxLayout()
        
        quick_calc_btn = QPushButton("🧮 محاسبه حقوق")
        quick_calc_btn.setObjectName("successBtn")
        quick_calc_btn.clicked.connect(self.calculate_payroll_for_selected)
        quick_btn_layout.addWidget(quick_calc_btn)
        
        quick_pay_btn = QPushButton("💳 پرداخت")
        quick_pay_btn.clicked.connect(self.register_payment)
        quick_btn_layout.addWidget(quick_pay_btn)
        
        left_layout.addLayout(quick_btn_layout)
        
        # فیش حقوقی
        payslip_group = QGroupBox("📄 فیش حقوقی")
        payslip_layout = QVBoxLayout()
        
        self.payslip_text = QTextEdit()
        self.payslip_text.setReadOnly(True)
        self.payslip_text.setPlaceholderText("برای مشاهده فیش حقوقی، یک پرسنل را انتخاب کنید...")
        payslip_layout.addWidget(self.payslip_text)
        
        payslip_group.setLayout(payslip_layout)
        left_layout.addWidget(payslip_group)
        
        # افزودن پنل‌ها
        main_layout.addWidget(right_panel, 2)
        main_layout.addWidget(left_panel, 1)
    
    # ========== عملیات اصلی ==========
    
    def load_employees(self):
        """بارگذاری لیست پرسنل فعال"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM employees WHERE is_active = 1 ORDER BY code')
            self.employees_data = c.fetchall()
        
        self.load_payroll()
    
    def load_payroll(self):
        """بارگذاری اطلاعات حقوق دوره انتخاب شده"""
        year = self.year_spin.value()
        month = self.month_combo.currentIndex() + 1
        
        self.payroll_table.setRowCount(len(self.employees_data))
        
        for i, emp in enumerate(self.employees_data):
            # اطلاعات پایه
            self.payroll_table.setItem(i, 0, QTableWidgetItem(emp['code']))
            self.payroll_table.setItem(i, 1, QTableWidgetItem(emp['name']))
            
            salary_item = QTableWidgetItem(f"{emp['base_salary']:,.0f}")
            salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.payroll_table.setItem(i, 2, salary_item)
            
            # اطلاعات فیش حقوقی این دوره
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT * FROM payrolls 
                    WHERE employee_id = ? AND year = ? AND month = ?
                ''', [emp['id'], year, month])
                payroll = c.fetchone()
            
            if payroll:
                self.payroll_table.setItem(i, 3, QTableWidgetItem(str(payroll['work_days'])))
                self.payroll_table.setItem(i, 4, QTableWidgetItem(f"{payroll['overtime_hours']:.1f}"))
                
                bonus_item = QTableWidgetItem(f"{payroll['bonus']:,.0f}")
                bonus_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.payroll_table.setItem(i, 5, bonus_item)
                
                ded_item = QTableWidgetItem(f"{payroll['deduction']:,.0f}")
                ded_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.payroll_table.setItem(i, 6, ded_item)
                
                net_item = QTableWidgetItem(f"{payroll['net_salary']:,.0f}")
                net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                net_item.setForeground(QColor('#27ae60'))
                net_item.setFont(QFont('', -1, QFont.Bold))
                self.payroll_table.setItem(i, 7, net_item)
                
                status = payroll['payment_status']
                status_text = {
                    'pending': '⏳ در انتظار',
                    'paid': '✅ پرداخت شده',
                    'cancelled': '❌ لغو شده'
                }.get(status, status)
                
                status_item = QTableWidgetItem(status_text)
                if status == 'paid':
                    status_item.setForeground(QColor('#27ae60'))
                elif status == 'pending':
                    status_item.setForeground(QColor('#f39c12'))
                else:
                    status_item.setForeground(QColor('#e84118'))
                
                self.payroll_table.setItem(i, 8, status_item)
            else:
                for col in range(3, 9):
                    self.payroll_table.setItem(i, col, QTableWidgetItem("-"))
    
    def on_employee_selected(self):
        """انتخاب پرسنل - نمایش جزئیات"""
        current_row = self.payroll_table.currentRow()
        if current_row >= 0 and current_row < len(self.employees_data):
            emp = self.employees_data[current_row]
            self.current_employee = emp
            self.show_employee_details(emp['id'])
    
    def show_employee_details(self, employee_id):
        """نمایش جزئیات پرسنل و فیش حقوقی"""
        year = self.year_spin.value()
        month = self.month_combo.currentIndex() + 1
        
        with get_db() as conn:
            c = conn.cursor()
            
            # اطلاعات پرسنل
            c.execute('SELECT * FROM employees WHERE id = ?', [employee_id])
            emp = c.fetchone()
            
            if not emp:
                return
            
            self.current_employee = emp
            
            self.emp_code.setText(emp['code'])
            self.emp_name.setText(emp['name'])
            self.emp_national.setText(emp['national_code'] or '-')
            self.emp_position.setText(emp['position'] or '-')
            self.emp_salary.setText(f"{emp['base_salary']:,.0f} ریال")
            self.emp_overtime.setText(f"{emp['overtime_rate'] or 1.5:.1f}x")
            self.emp_hire_date.setText(emp['hire_date'] or '-')
            
            # فیش حقوقی
            c.execute('''
                SELECT * FROM payrolls 
                WHERE employee_id = ? AND year = ? AND month = ?
            ''', [employee_id, year, month])
            
            payroll = c.fetchone()
            
            if payroll:
                self.display_payslip(emp, payroll)
            else:
                self.payslip_text.setHtml("""
                <div style='text-align: center; padding: 20px; color: #666;'>
                    <p>📄 فیش حقوقی برای این دوره ثبت نشده است.</p>
                    <p>برای محاسبه حقوق، روی دکمه "محاسبه حقوق" کلیک کنید.</p>
                </div>
                """)
    
    def display_payslip(self, emp, payroll):
        """نمایش فیش حقوقی"""
        month_names = [
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ]
        month_name = month_names[self.month_combo.currentIndex()]
        year = self.year_spin.value()
        
        # محاسبات
        base_salary = emp['base_salary']
        work_days = payroll['work_days']
        daily_salary = base_salary / 30
        work_salary = daily_salary * work_days
        
        overtime_hours = payroll['overtime_hours']
        overtime_rate = emp['overtime_rate'] or 1.5
        overtime_salary = (base_salary / 220) * overtime_hours * overtime_rate
        
        bonus = payroll['bonus'] or 0
        total_earnings = work_salary + overtime_salary + bonus
        
        deduction = payroll['deduction'] or 0
        insurance = payroll['insurance'] or 0
        tax = payroll['tax'] or 0
        total_deductions = deduction + insurance + tax
        
        net_salary = payroll['net_salary'] or 0
        
        status = payroll['payment_status']
        status_text = {
            'pending': '⏳ در انتظار پرداخت',
            'paid': '✅ پرداخت شده',
            'cancelled': '❌ لغو شده'
        }.get(status, status)
        
        status_color = {
            'pending': '#f39c12',
            'paid': '#27ae60',
            'cancelled': '#e84118'
        }.get(status, '#666')
        
        html = f"""
        <div style='font-family: Tahoma;'>
            <h3 style='text-align: center; color: #2C3E50;'>فیش حقوقی</h3>
            <h4 style='text-align: center; color: #666;'>{month_name} {year}</h4>
            <hr>
            
            <p><b>👤 نام:</b> {emp['name']}</p>
            <p><b>🆔 کد پرسنلی:</b> {emp['code']}</p>
            <p><b>💼 سمت:</b> {emp['position'] or '-'}</p>
            
            <hr>
            <h4 style='color: #27ae60;'>💰 حقوق و مزایا:</h4>
            <table width='100%' style='border-collapse: collapse;'>
                <tr><td>حقوق پایه (۳۰ روز)</td><td style='text-align: right;'>{base_salary:,.0f}</td></tr>
                <tr><td>حقوق کارکرد ({work_days} روز)</td><td style='text-align: right;'>{work_salary:,.0f}</td></tr>
                <tr><td>اضافه کاری ({overtime_hours:.1f} ساعت)</td><td style='text-align: right;'>{overtime_salary:,.0f}</td></tr>
                <tr><td>پاداش</td><td style='text-align: right;'>{bonus:,.0f}</td></tr>
                <tr style='font-weight: bold;'><td>جمع حقوق و مزایا</td><td style='text-align: right;'>{total_earnings:,.0f}</td></tr>
            </table>
            
            <h4 style='color: #e84118;'>📉 کسورات:</h4>
            <table width='100%' style='border-collapse: collapse;'>
                <tr><td>بیمه (۷٪)</td><td style='text-align: right;'>{insurance:,.0f}</td></tr>
                <tr><td>مالیات</td><td style='text-align: right;'>{tax:,.0f}</td></tr>
                <tr><td>سایر کسورات</td><td style='text-align: right;'>{deduction:,.0f}</td></tr>
                <tr style='font-weight: bold;'><td>جمع کسورات</td><td style='text-align: right;'>{total_deductions:,.0f}</td></tr>
            </table>
            
            <hr>
            <h3 style='text-align: center; color: #273c75;'>
                💵 خالص پرداختی: {net_salary:,.0f} ریال
            </h3>
            
            <p style='text-align: center; color: {status_color}; font-weight: bold;'>
                {status_text}
            </p>
            
            <p style='color: #999; font-size: 9pt; text-align: center;'>
                تاریخ محاسبه: {datetime.now().strftime('%Y/%m/%d %H:%M')}
            </p>
        </div>
        """
        
        self.payslip_text.setHtml(html)
    
    def new_employee(self):
        """ایجاد پرسنل جدید"""
        dialog = EmployeeDialog()
        if dialog.exec_():
            self.load_employees()
            QMessageBox.information(self, "موفق", "✅ پرسنل جدید با موفقیت ایجاد شد!")
    
    def edit_employee(self):
        """ویرایش پرسنل انتخاب شده"""
        current_row = self.payroll_table.currentRow()
        if current_row < 0 or current_row >= len(self.employees_data):
            QMessageBox.warning(self, "خطا", "لطفاً یک پرسنل را انتخاب کنید!")
            return
        
        emp = self.employees_data[current_row]
        dialog = EmployeeDialog(emp['id'])
        if dialog.exec_():
            self.load_employees()
            self.show_employee_details(emp['id'])
            QMessageBox.information(self, "موفق", "✅ پرسنل با موفقیت ویرایش شد!")
    
    def delete_employee(self):
        """حذف پرسنل انتخاب شده"""
        current_row = self.payroll_table.currentRow()
        if current_row < 0 or current_row >= len(self.employees_data):
            QMessageBox.warning(self, "خطا", "لطفاً یک پرسنل را انتخاب کنید!")
            return
        
        emp = self.employees_data[current_row]
        
        # بررسی وجود فیش حقوقی
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM payrolls WHERE employee_id = ?', [emp['id']])
            payroll_count = c.fetchone()[0]
        
        warning = ""
        if payroll_count > 0:
            warning = f"\n⚠️ این پرسنل {payroll_count} فیش حقوقی ثبت شده دارد که همراه با آن حذف خواهند شد!"
        
        reply = QMessageBox.question(
            self, "تأیید حذف",
            f"آیا از حذف پرسنل '{emp['name']}' اطمینان دارید؟{warning}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('DELETE FROM payrolls WHERE employee_id = ?', [emp['id']])
                c.execute('DELETE FROM employees WHERE id = ?', [emp['id']])
            
            self.load_employees()
            
            # پاک کردن جزئیات
            self.emp_code.clear()
            self.emp_name.clear()
            self.emp_national.clear()
            self.emp_position.clear()
            self.emp_salary.clear()
            self.emp_overtime.clear()
            self.emp_hire_date.clear()
            self.payslip_text.clear()
            self.current_employee = None
            
            QMessageBox.information(self, "موفق", "✅ پرسنل با موفقیت حذف شد!")
    
    def calculate_payroll_for_selected(self):
        """محاسبه حقوق برای پرسنل انتخاب شده"""
        current_row = self.payroll_table.currentRow()
        if current_row < 0 or current_row >= len(self.employees_data):
            QMessageBox.warning(self, "خطا", "لطفاً یک پرسنل را انتخاب کنید!")
            return
        
        emp = self.employees_data[current_row]
        year = self.year_spin.value()
        month = self.month_combo.currentIndex() + 1
        
        dialog = PayrollDialog(emp, year, month)
        if dialog.exec_():
            self.load_payroll()
            self.show_employee_details(emp['id'])
            QMessageBox.information(self, "موفق", "✅ حقوق با موفقیت محاسبه و ذخیره شد!")
    
    def register_payment(self):
        """ثبت پرداخت حقوق"""
        current_row = self.payroll_table.currentRow()
        if current_row < 0 or current_row >= len(self.employees_data):
            QMessageBox.warning(self, "خطا", "لطفاً یک پرسنل را انتخاب کنید!")
            return
        
        emp = self.employees_data[current_row]
        year = self.year_spin.value()
        month = self.month_combo.currentIndex() + 1
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM payrolls 
                WHERE employee_id = ? AND year = ? AND month = ?
            ''', [emp['id'], year, month])
            
            payroll = c.fetchone()
            
            if not payroll:
                QMessageBox.warning(self, "خطا", "ابتدا باید فیش حقوقی محاسبه شود!")
                return
            
            if payroll['payment_status'] == 'paid':
                QMessageBox.information(self, "توجه", "این فیش قبلاً پرداخت شده است!")
                return
            
            net_salary = payroll['net_salary'] or 0
            
            reply = QMessageBox.question(
                self, "تأیید پرداخت",
                f"آیا پرداخت حقوق {emp['name']} به مبلغ {net_salary:,.0f} ریال تأیید می‌شود؟",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                c.execute('''
                    UPDATE payrolls 
                    SET payment_status = 'paid', payment_date = ?
                    WHERE id = ?
                ''', [datetime.now().strftime("%Y-%m-%d"), payroll['id']])
                
                self.load_payroll()
                self.show_employee_details(emp['id'])
                QMessageBox.information(self, "موفق", "✅ پرداخت با موفقیت ثبت شد!")


# ============================================================
# دیالوگ تعریف/ویرایش پرسنل
# ============================================================
class EmployeeDialog(QDialog):
    """دیالوگ ایجاد/ویرایش پرسنل"""
    
    def __init__(self, employee_id=None):
        super().__init__()
        self.employee_id = employee_id
        self.setWindowTitle("✏️ ویرایش پرسنل" if employee_id else "➕ تعریف پرسنل جدید")
        self.setGeometry(300, 200, 500, 500)
        self.init_ui()
        
        if employee_id:
            self.load_employee_data()
    
    def init_ui(self):
        layout = QFormLayout(self)
        
        # کد پرسنلی
        self.code = QLineEdit()
        self.code.setPlaceholderText("مثال: EMP-001")
        layout.addRow("کد پرسنلی *:", self.code)
        
        # نام
        self.name = QLineEdit()
        self.name.setPlaceholderText("نام و نام خانوادگی")
        layout.addRow("نام *:", self.name)
        
        # کد ملی
        self.national_code = QLineEdit()
        self.national_code.setPlaceholderText("کد ملی (اختیاری)")
        layout.addRow("کد ملی:", self.national_code)
        
        # سمت
        self.position = QLineEdit()
        self.position.setPlaceholderText("سمت سازمانی")
        layout.addRow("سمت:", self.position)
        
        # حقوق پایه
        self.base_salary = MoneyLineEdit()
        layout.addRow("حقوق پایه (ریال) *:", self.base_salary)
        
        # نرخ اضافه کاری
        self.overtime_rate = QDoubleSpinBox()
        self.overtime_rate.setRange(1, 3)
        self.overtime_rate.setSingleStep(0.1)
        self.overtime_rate.setValue(1.5)
        self.overtime_rate.setSuffix(" برابر")
        layout.addRow("ضریب اضافه کاری:", self.overtime_rate)
        
        # حق بیمه
        self.insurance_premium = QDoubleSpinBox()
        self.insurance_premium.setRange(0, 0.3)
        self.insurance_premium.setSingleStep(0.01)
        self.insurance_premium.setValue(0.07)
        self.insurance_premium.setSuffix(" (۷٪)")
        layout.addRow("حق بیمه:", self.insurance_premium)
        
        # تاریخ استخدام
        self.hire_date = QDateEdit()
        self.hire_date.setDate(QDate.currentDate())
        self.hire_date.setCalendarPopup(True)
        layout.addRow("تاریخ استخدام:", self.hire_date)
        
        # وضعیت فعال
        self.is_active = QCheckBox("فعال")
        self.is_active.setChecked(True)
        layout.addRow("", self.is_active)
        
        # راهنما
        hint_label = QLabel("💡 حقوق پایه را می‌توانید با جداکننده هزارگان یا بدون آن وارد کنید.")
        hint_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addRow("", hint_label)
        
        # دکمه‌ها
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def load_employee_data(self):
        """بارگذاری اطلاعات پرسنل برای ویرایش"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM employees WHERE id = ?', [self.employee_id])
            emp = c.fetchone()
            
            if emp:
                self.code.setText(emp['code'])
                self.name.setText(emp['name'])
                self.national_code.setText(emp['national_code'] or '')
                self.position.setText(emp['position'] or '')
                self.base_salary.setValue(emp['base_salary'] or 0)
                self.overtime_rate.setValue(emp['overtime_rate'] or 1.5)
                self.insurance_premium.setValue(emp['insurance_premium'] or 0.07)
                if emp['hire_date']:
                    self.hire_date.setDate(QDate.fromString(emp['hire_date'], "yyyy-MM-dd"))
                self.is_active.setChecked(emp['is_active'] == 1)
    
    def accept(self):
        """ذخیره پرسنل"""
        if not self.code.text().strip():
            QMessageBox.warning(self, "خطا", "کد پرسنلی الزامی است!")
            return
        
        if not self.name.text().strip():
            QMessageBox.warning(self, "خطا", "نام پرسنل الزامی است!")
            return
        
        if self.base_salary.value() <= 0:
            QMessageBox.warning(self, "خطا", "حقوق پایه باید بیشتر از صفر باشد!")
            return
        
        with get_db() as conn:
            c = conn.cursor()
            
            data = [
                self.code.text().strip(),
                self.name.text().strip(),
                self.national_code.text().strip() or None,
                self.position.text().strip() or None,
                self.base_salary.value(),
                self.overtime_rate.value(),
                self.insurance_premium.value(),
                self.hire_date.date().toString("yyyy-MM-dd"),
                1 if self.is_active.isChecked() else 0
            ]
            
            if self.employee_id:
                # ویرایش
                data.append(self.employee_id)
                try:
                    c.execute('''
                        UPDATE employees 
                        SET code=?, name=?, national_code=?, position=?, 
                            base_salary=?, overtime_rate=?, insurance_premium=?, 
                            hire_date=?, is_active=?
                        WHERE id=?
                    ''', data)
                except sqlite3.IntegrityError:
                    QMessageBox.warning(self, "خطا", "کد پرسنلی تکراری است!")
                    return
            else:
                # ایجاد جدید
                try:
                    c.execute('''
                        INSERT INTO employees 
                        (code, name, national_code, position, base_salary, 
                         overtime_rate, insurance_premium, hire_date, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', data)
                except sqlite3.IntegrityError:
                    QMessageBox.warning(self, "خطا", "کد پرسنلی تکراری است!")
                    return
        
        super().accept()


# ============================================================
# دیالوگ محاسبه حقوق
# ============================================================
class PayrollDialog(QDialog):
    """دیالوگ محاسبه حقوق ماهانه"""
    
    def __init__(self, employee, year, month):
        super().__init__()
        self.employee = employee
        self.year = year
        self.month = month
        self.setWindowTitle(f"🧮 محاسبه حقوق {employee['name']}")
        self.setGeometry(350, 250, 500, 500)
        self.init_ui()
        self.load_existing_data()
    
    def init_ui(self):
        layout = QFormLayout(self)
        
        # عنوان
        month_names = [
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ]
        title = QLabel(f"<h3>{self.employee['name']} - {month_names[self.month-1]} {self.year}</h3>")
        title.setAlignment(Qt.AlignCenter)
        layout.addRow(title)
        
        # خط جداکننده
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addRow(line)
        
        # روز کارکرد
        self.work_days = QSpinBox()
        self.work_days.setRange(0, 31)
        self.work_days.setValue(30)
        self.work_days.setSuffix(" روز")
        self.work_days.valueChanged.connect(self.calculate_preview)
        layout.addRow("روز کارکرد:", self.work_days)
        
        # اضافه کاری
        self.overtime_hours = QDoubleSpinBox()
        self.overtime_hours.setRange(0, 300)
        self.overtime_hours.setSingleStep(1)
        self.overtime_hours.setDecimals(1)
        self.overtime_hours.setSuffix(" ساعت")
        self.overtime_hours.valueChanged.connect(self.calculate_preview)
        layout.addRow("اضافه کاری:", self.overtime_hours)
        
        # پاداش
        self.bonus = MoneyLineEdit()
        self.bonus.textChanged.connect(self.calculate_preview)
        layout.addRow("پاداش (ریال):", self.bonus)
        
        # کسورات
        self.deduction = MoneyLineEdit()
        self.deduction.textChanged.connect(self.calculate_preview)
        layout.addRow("سایر کسورات (ریال):", self.deduction)
        
        # خط جداکننده
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addRow(line2)
        
        # پیش‌نمایش
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("""
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 11pt;
        """)
        self.preview_label.setWordWrap(True)
        layout.addRow("📊 پیش‌نمایش:", self.preview_label)
        
        # دکمه‌ها
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def load_existing_data(self):
        """بارگذاری داده‌های موجود"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM payrolls 
                WHERE employee_id = ? AND year = ? AND month = ?
            ''', [self.employee['id'], self.year, self.month])
            
            payroll = c.fetchone()
            
            if payroll:
                self.work_days.setValue(payroll['work_days'])
                self.overtime_hours.setValue(payroll['overtime_hours'] or 0)
                self.bonus.setValue(payroll['bonus'] or 0)
                self.deduction.setValue(payroll['deduction'] or 0)
        
        self.calculate_preview()
    
    def calculate_preview(self):
        """محاسبه پیش‌نمایش حقوق"""
        base_salary = self.employee['base_salary']
        work_days = self.work_days.value()
        overtime_hours = self.overtime_hours.value()
        bonus = self.bonus.value()
        deduction = self.deduction.value()
        
        # محاسبات
        daily_salary = base_salary / 30
        work_salary = daily_salary * work_days
        
        overtime_rate = self.employee['overtime_rate'] or 1.5
        overtime_salary = (base_salary / 220) * overtime_hours * overtime_rate
        
        gross_salary = work_salary + overtime_salary + bonus
        
        insurance = gross_salary * (self.employee['insurance_premium'] or 0.07)
        tax = PayrollHelper._calculate_tax(gross_salary)
        
        net_salary = gross_salary - insurance - tax - deduction
        
        preview_text = f"""
        💰 حقوق پایه روزانه: {daily_salary:,.0f} ریال
        
        📈 **حقوق و مزایا:**
        • حقوق کارکرد ({work_days} روز): {work_salary:,.0f} ریال
        • اضافه کاری ({overtime_hours:.1f} ساعت): {overtime_salary:,.0f} ریال
        • پاداش: {bonus:,.0f} ریال
        ────────────────────────────────
        جمع حقوق و مزایا: {gross_salary:,.0f} ریال
        
        📉 **کسورات:**
        • بیمه ({(self.employee['insurance_premium'] or 0.07)*100:.0f}٪): {insurance:,.0f} ریال
        • مالیات: {tax:,.0f} ریال
        • سایر کسورات: {deduction:,.0f} ریال
        ────────────────────────────────
        جمع کسورات: {insurance + tax + deduction:,.0f} ریال
        
        💵 **خالص پرداختی: {net_salary:,.0f} ریال**
        """
        
        self.preview_label.setText(preview_text)
        self._net_salary = net_salary
        self._insurance = insurance
        self._tax = tax
    
    def accept(self):
        """ذخیره فیش حقوقی"""
        self.calculate_preview()
        
        with get_db() as conn:
            c = conn.cursor()
            
            data = [
                self.work_days.value(),
                self.overtime_hours.value(),
                self.bonus.value(),
                self.deduction.value(),
                self._insurance,
                self._tax,
                self._net_salary
            ]
            
            # بررسی وجود رکورد
            c.execute('''
                SELECT id FROM payrolls 
                WHERE employee_id = ? AND year = ? AND month = ?
            ''', [self.employee['id'], self.year, self.month])
            
            existing = c.fetchone()
            
            if existing:
                data.append(existing['id'])
                c.execute('''
                    UPDATE payrolls 
                    SET work_days=?, overtime_hours=?, bonus=?, deduction=?,
                        insurance=?, tax=?, net_salary=?
                    WHERE id=?
                ''', data)
            else:
                data = [
                    self.employee['id'], self.year, self.month,
                    self.work_days.value(), self.overtime_hours.value(),
                    self.bonus.value(), self.deduction.value(),
                    self._insurance, self._tax, self._net_salary
                ]
                c.execute('''
                    INSERT INTO payrolls 
                    (employee_id, year, month, work_days, overtime_hours, 
                     bonus, deduction, insurance, tax, net_salary, payment_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                ''', data)
        
        super().accept()
