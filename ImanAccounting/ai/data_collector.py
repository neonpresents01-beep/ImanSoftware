"""
جمع‌آوری داده‌های آموزشی از اسناد حسابداری موجود
"""

import sqlite3
import numpy as np
import re
from typing import List, Tuple, Dict
from pathlib import Path
import json
from datetime import datetime

class AccountingDataCollector:
    """جمع‌آوری داده‌های آموزشی از دیتابیس حسابداری"""
    
    # نگاشت کد حساب به کلاس
    ACCOUNT_TO_CLASS = {
        "1101": 0,  # صندوق
        "1102": 1,  # بانک
        "4101": 2,  # فروش کالا
        "5101": 3,  # خرید کالا
        "5102": 4,  # هزینه حقوق
        "5103": 5,  # هزینه اجاره
        "5104": 6,  # هزینه آب و برق
        "5105": 7,  # هزینه تعمیرات
    }
    
    def __init__(self, db_path: str = "accounting.db"):
        self.db_path = db_path
        self.training_data = []
    
    def collect_transaction_data(self) -> List[Tuple[str, int]]:
        """
        جمع‌آوری داده‌های تراکنش از دیتابیس
        
        Returns:
            List of (description, class_label)
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # دریافت تمام اقلام سند با حساب‌های مشخص
        c.execute('''
            SELECT vi.description, vi.account_code, v.description as voucher_desc
            FROM voucher_items vi
            JOIN vouchers v ON vi.voucher_id = v.id
            WHERE vi.account_code IN ('1101', '1102', '4101', '5101', '5102', '5103', '5104', '5105')
            AND (vi.description IS NOT NULL OR v.description IS NOT NULL)
            ORDER BY v.date DESC
            LIMIT 10000
        ''')
        
        data = []
        for row in c.fetchall():
            item_desc = row[0] or ""
            account_code = row[1]
            voucher_desc = row[2] or ""
            
            # ترکیب شرح سند و شرح ردیف
            full_desc = f"{voucher_desc} {item_desc}".strip()
            
            if full_desc and account_code in self.ACCOUNT_TO_CLASS:
                class_label = self.ACCOUNT_TO_CLASS[account_code]
                data.append((self._clean_text(full_desc), class_label))
        
        conn.close()
        
        print(f"✅ {len(data)} تراکنش از دیتابیس جمع‌آوری شد")
        self.training_data = data
        return data
    
    def collect_cashflow_data(self) -> List[float]:
        """
        جمع‌آوری داده‌های جریان نقدی (موجودی حساب بانک در طول زمان)
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # محاسبه موجودی ماهانه حساب بانک
        c.execute('''
            SELECT 
                strftime('%Y-%m', v.date) as month,
                SUM(CASE WHEN vi.account_code = '1102' THEN vi.debit - vi.credit ELSE 0 END) as balance_change
            FROM voucher_items vi
            JOIN vouchers v ON vi.voucher_id = v.id
            GROUP BY strftime('%Y-%m', v.date)
            ORDER BY month
        ''')
        
        balances = []
        running_balance = 0
        
        for row in c.fetchall():
            running_balance += row[1] or 0
            balances.append(running_balance)
        
        conn.close()
        
        print(f"✅ داده‌های جریان نقدی برای {len(balances)} ماه جمع‌آوری شد")
        return balances
    
    def collect_anomaly_data(self) -> List[Dict]:
        """
        جمع‌آوری داده‌های ناهنجاری برای آموزش مدل تشخیص خطا
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # اسناد ناموزون (بدهکار != بستانکار) - اینها ناهنجاری هستند
        c.execute('''
            SELECT 
                v.id,
                v.description,
                SUM(vi.debit) as total_debit,
                SUM(vi.credit) as total_credit,
                ABS(SUM(vi.debit) - SUM(vi.credit)) as diff
            FROM vouchers v
            JOIN voucher_items vi ON v.id = vi.voucher_id
            GROUP BY v.id
            HAVING diff > 0
        ''')
        
        anomalies = []
        for row in c.fetchall():
            anomalies.append({
                "voucher_id": row[0],
                "description": row[1],
                "total_debit": row[2],
                "total_credit": row[3],
                "difference": row[4],
                "is_anomaly": True
            })
        
        conn.close()
        
        print(f"✅ {len(anomalies)} ناهنجاری شناسایی شد")
        return anomalies
    
    def _clean_text(self, text: str) -> str:
        """پاکسازی متن فارسی"""
        if not text:
            return ""
        
        # حذف اعداد
        text = re.sub(r'\d+', '', text)
        # حذف علائم نگارشی
        text = re.sub(r'[،,\.\/\\\-_:;()\[\]{}«»""\'\']', ' ', text)
        # نرمال‌سازی فاصله
        text = ' '.join(text.split())
        return text.lower()
    
    def save_training_data(self, output_dir: str = "ai/training_data"):
        """ذخیره داده‌های آموزشی برای استفاده بعدی"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # ذخیره داده‌های تراکنش
        if self.training_data:
            with open(output_path / "transactions.json", "w", encoding="utf-8") as f:
                json.dump([
                    {"text": text, "label": label} 
                    for text, label in self.training_data
                ], f, ensure_ascii=False, indent=2)
        
        # ذخیره داده‌های جریان نقدی
        cashflow = self.collect_cashflow_data()
        if cashflow:
            with open(output_path / "cashflow.json", "w", encoding="utf-8") as f:
                json.dump(cashflow, f, indent=2)
        
        print(f"💾 داده‌های آموزشی در {output_dir} ذخیره شدند")
    
    def load_training_data(self, input_dir: str = "ai/training_data"):
        """بارگذاری داده‌های آموزشی ذخیره شده"""
        input_path = Path(input_dir)
        
        # بارگذاری تراکنش‌ها
        trans_file = input_path / "transactions.json"
        if trans_file.exists():
            with open(trans_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.training_data = [(d["text"], d["label"]) for d in data]
                print(f"📂 {len(self.training_data)} تراکنش بارگذاری شد")
        
        # بارگذاری جریان نقدی
        cashflow_file = input_path / "cashflow.json"
        if cashflow_file.exists():
            with open(cashflow_file, "r", encoding="utf-8") as f:
                self.cashflow_data = json.load(f)
                print(f"📂 {len(self.cashflow_data)} ماه داده جریان نقدی بارگذاری شد")
        
        return self.training_data
