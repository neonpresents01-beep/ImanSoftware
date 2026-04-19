import sqlite3
from datetime import datetime
from contextlib import contextmanager

DB_NAME = "accounting.db"

# تنظیم timeout برای جلوگیری از قفل شدن (5 ثانیه)
@contextmanager
def get_db():
    """مدیریت اتصال به پایگاه داده با timeout"""
    conn = sqlite3.connect(DB_NAME, timeout=10.0)  # 10 ثانیه صبر کنه
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class DatabaseManager:
    @staticmethod
    def init_db():
        """ایجاد تمام جداول"""
        with get_db() as conn:
            c = conn.cursor()
            
            # ============== حساب‌های کل ==============
            c.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    parent_code TEXT,
                    balance REAL DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # ============== اسناد حسابداری ==============
            c.execute('''
                CREATE TABLE IF NOT EXISTS vouchers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voucher_no INTEGER UNIQUE,
                    date TEXT NOT NULL,
                    description TEXT,
                    type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS voucher_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voucher_id INTEGER,
                    account_code TEXT,
                    debit REAL DEFAULT 0,
                    credit REAL DEFAULT 0,
                    description TEXT,
                    FOREIGN KEY(voucher_id) REFERENCES vouchers(id),
                    FOREIGN KEY(account_code) REFERENCES accounts(code)
                )
            ''')
            
            # ============== انبارداری ==============
            c.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    unit TEXT DEFAULT 'عدد',
                    stock REAL DEFAULT 0,
                    purchase_price REAL DEFAULT 0,
                    sale_price REAL DEFAULT 0,
                    min_stock REAL DEFAULT 0,
                    category TEXT
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS stock_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    product_id INTEGER,
                    type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    unit_price REAL,
                    total_price REAL,
                    ref_no TEXT,
                    description TEXT,
                    FOREIGN KEY(product_id) REFERENCES products(id)
                )
            ''')
            
            # ============== حقوق دستمزد ==============
            c.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    national_code TEXT,
                    position TEXT,
                    base_salary REAL DEFAULT 0,
                    overtime_rate REAL DEFAULT 0,
                    insurance_premium REAL DEFAULT 0,
                    hire_date TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS payrolls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER,
                    year INTEGER,
                    month INTEGER,
                    work_days INTEGER DEFAULT 30,
                    overtime_hours REAL DEFAULT 0,
                    bonus REAL DEFAULT 0,
                    deduction REAL DEFAULT 0,
                    insurance REAL DEFAULT 0,
                    tax REAL DEFAULT 0,
                    net_salary REAL,
                    payment_status TEXT DEFAULT 'pending',
                    payment_date TEXT,
                    FOREIGN KEY(employee_id) REFERENCES employees(id),
                    UNIQUE(employee_id, year, month)
                )
            ''')
            
            # ============== تنظیمات ==============
            c.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # درج حساب‌های پیش‌فرض
            DatabaseManager._insert_default_accounts(c)
            DatabaseManager._insert_default_settings(c)
    
    @staticmethod
    def _insert_default_accounts(cursor):
        accounts = [
            ('1101', 'صندوق', 'asset', None),
            ('1102', 'بانک', 'asset', None),
            ('1103', 'حساب‌های دریافتنی', 'asset', None),
            ('1104', 'موجودی کالا', 'asset', None),
            ('1105', 'دارایی ثابت', 'asset', None),
            ('2101', 'حساب‌های پرداختنی', 'liability', None),
            ('2102', 'وام‌های دریافتی', 'liability', None),
            ('3101', 'سرمایه', 'equity', None),
            ('3102', 'سود و زیان جاری', 'equity', None),
            ('4101', 'فروش کالا', 'income', None),
            ('4102', 'درآمد خدمات', 'income', None),
            ('5101', 'خرید کالا', 'expense', None),
            ('5102', 'هزینه حقوق', 'expense', None),
            ('5103', 'هزینه اجاره', 'expense', None),
            ('5104', 'هزینه آب و برق', 'expense', None),
            ('5105', 'هزینه استهلاک', 'expense', None),
        ]
        
        for acc in accounts:
            cursor.execute('''
                INSERT OR IGNORE INTO accounts (code, name, type, parent_code)
                VALUES (?, ?, ?, ?)
            ''', acc)
    
    @staticmethod
    def _insert_default_settings(cursor):
        settings = [
            ('company_name', 'شرکت حسابداری پارسه'),
            ('fiscal_year_start', '1403/01/01'),
            ('fiscal_year_end', '1403/12/29'),
            ('currency', 'ریال'),
            ('inventory_method', 'FIFO'),
        ]
        
        for key, value in settings:
            cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
            ''', (key, value))


class AccountingHelper:
    @staticmethod
    def get_account_balance(account_code, from_date=None, to_date=None):
        """محاسبه مانده حساب"""
        with get_db() as conn:
            c = conn.cursor()
            
            query = '''
                SELECT 
                    SUM(debit) as total_debit,
                    SUM(credit) as total_credit
                FROM voucher_items vi
                JOIN vouchers v ON vi.voucher_id = v.id
                WHERE vi.account_code = ?
            '''
            params = [account_code]
            
            if from_date:
                query += " AND v.date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND v.date <= ?"
                params.append(to_date)
            
            c.execute(query, params)
            row = c.fetchone()
            
            debit = row['total_debit'] or 0
            credit = row['total_credit'] or 0
            
            c.execute("SELECT type FROM accounts WHERE code = ?", [account_code])
            acc_type = c.fetchone()
            
            if acc_type:
                acc_type = acc_type['type']
                if acc_type in ['asset', 'expense']:
                    return debit - credit
                else:
                    return credit - debit
            return debit - credit
    
    @staticmethod
    def get_trial_balance(date):
        """تراز آزمایشی"""
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
            
            return c.fetchall()


class InventoryHelper:
    @staticmethod
    def update_stock(product_id, quantity, transaction_type):
        """بروزرسانی موجودی انبار"""
        with get_db() as conn:
            c = conn.cursor()
            
            if transaction_type == 'in':
                c.execute('''
                    UPDATE products 
                    SET stock = stock + ? 
                    WHERE id = ?
                ''', [quantity, product_id])
            else:
                c.execute('''
                    UPDATE products 
                    SET stock = stock - ? 
                    WHERE id = ?
                ''', [quantity, product_id])
    
    @staticmethod
    def get_low_stock_products():
        """کالاهای زیر حداقل موجودی"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM products 
                WHERE stock <= min_stock AND min_stock > 0
                ORDER BY stock ASC
            ''')
            return c.fetchall()


class PayrollHelper:
    @staticmethod
    def calculate_salary(employee_id, year, month):
        """محاسبه حقوق خالص"""
        with get_db() as conn:
            c = conn.cursor()
            
            c.execute('SELECT * FROM employees WHERE id = ?', [employee_id])
            emp = c.fetchone()
            
            if not emp:
                return 0
            
            c.execute('''
                SELECT * FROM payrolls 
                WHERE employee_id = ? AND year = ? AND month = ?
            ''', [employee_id, year, month])
            
            payroll = c.fetchone()
            
            if not payroll:
                return 0
            
            base_salary = emp['base_salary']
            work_days = payroll['work_days']
            overtime_hours = payroll['overtime_hours']
            
            daily_salary = base_salary / 30
            work_salary = daily_salary * work_days
            
            overtime_rate = emp['overtime_rate'] or 1.5
            overtime_salary = (base_salary / 220) * overtime_hours * overtime_rate
            
            bonus = payroll['bonus'] or 0
            deduction = payroll['deduction'] or 0
            
            gross_salary = work_salary + overtime_salary + bonus
            
            insurance = gross_salary * (emp['insurance_premium'] or 0.07)
            tax = PayrollHelper._calculate_tax(gross_salary)
            
            net_salary = gross_salary - insurance - tax - deduction
            
            c.execute('''
                UPDATE payrolls 
                SET insurance = ?, tax = ?, net_salary = ?
                WHERE id = ?
            ''', [insurance, tax, net_salary, payroll['id']])
            
            return net_salary
    
    @staticmethod
    def _calculate_tax(gross_salary):
        """محاسبه مالیات (فرمول ساده)"""
        if gross_salary <= 100000000:
            return 0
        elif gross_salary <= 150000000:
            return (gross_salary - 100000000) * 0.10
        else:
            return (50000000 * 0.10) + ((gross_salary - 150000000) * 0.15)
