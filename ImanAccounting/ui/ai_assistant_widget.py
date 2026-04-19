"""
ویجت دستیار هوشمند با ImanAI Core v6.2
نسخه بروز شده - سازگار با TransactionClassifier جدید
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
from datetime import datetime
import re

# استفاده از ماژول‌های AI خودمون
from ai.transaction_classifier import TransactionClassifier
from ai.cashflow_predictor import IntelligentCashFlowPredictor
from ai.data_collector import AccountingDataCollector
from database import get_db, AccountingHelper


class AIAssistantWidget(QWidget):
    """دستیار هوشمند ImanAI - نسخه ۲.۰"""
    
    def __init__(self):
        super().__init__()
        
        # راه‌اندازی مدل‌های ImanAI
        print("🧠 در حال بارگذاری مدل‌های ImanAI...")
        self.classifier = TransactionClassifier()
        self.predictor = IntelligentCashFlowPredictor()
        self.collector = AccountingDataCollector()
        
        # وضعیت مدل
        self.model_info = self.classifier.get_model_info()
        
        self.init_ui()
        self.display_model_status()
    
    def display_model_status(self):
        """نمایش وضعیت مدل در کنسول و UI"""
        if self.model_info['is_trained']:
            status = f"✅ مدل آموزش دیده (واژگان: {self.model_info['vocab_size']} کلمه)"
            if 'meta' in self.model_info and self.model_info['meta'].get('trained_at'):
                status += f"\n   📅 آموزش: {self.model_info['meta']['trained_at'][:10]}"
        else:
            status = "⚠️ مدل آموزش ندیده - استفاده از روش کلمات کلیدی"
        
        print(f"📊 وضعیت مدل: {status}")
        
        # اضافه کردن به چت
        self.add_message("assistant", 
            f"👋 سلام! من دستیار هوشمند ImanAI هستم.\n"
            f"🧠 موتور: v6.2 (LSTM + Dense Network)\n"
            f"📊 {status}\n\n"
            f"💡 می‌تونید از من بپرسید:\n"
            f"• موجودی صندوق چقدره؟\n"
            f"• سود این ماه چقدر بود؟\n"
            f"• پیش‌بینی موجودی ۳ ماه آینده\n"
            f"• دسته‌بندی: \"خرید از دیجیکالا\"")
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # ========== هدر ==========
        header = QHBoxLayout()
        
        title = QLabel("🤖 دستیار هوشمند ImanAI")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 16pt; color: #e94560;")
        header.addWidget(title)
        
        version = QLabel("v2.0")
        version.setStyleSheet("color: #4CAF50; font-weight: bold; background: #1a3a1a; padding: 4px 8px; border-radius: 12px;")
        header.addWidget(version)
        
        # نشانگر وضعیت مدل
        if self.model_info['is_trained']:
            status_badge = QLabel("🧠 آموزش دیده")
            status_badge.setStyleSheet("background: #4CAF50; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold;")
        else:
            status_badge = QLabel("📝 کلمات کلیدی")
            status_badge.setStyleSheet("background: #FF9800; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold;")
        header.addWidget(status_badge)
        
        header.addStretch()
        layout.addLayout(header)
        
        # ========== چت ==========
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background: #1a1a2e;
                color: #eee;
                border: 1px solid #0f3460;
                border-radius: 10px;
                padding: 15px;
                font-size: 11pt;
            }
            QScrollBar:vertical {
                background: #0f3460;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #e94560;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.chat_history, 1)
        
        # ========== ورودی ==========
        input_layout = QHBoxLayout()
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("💬 سوال خود را بپرسید... (مثال: موجودی صندوق چقدره؟)")
        self.query_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                font-size: 11pt;
                background: #16213e;
                color: #eee;
                border: 2px solid #0f3460;
                border-radius: 25px;
            }
            QLineEdit:focus {
                border-color: #e94560;
            }
        """)
        self.query_input.returnPressed.connect(self.process_query)
        input_layout.addWidget(self.query_input)
        
        send_btn = QPushButton("📤 ارسال")
        send_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background: #e94560;
                color: white;
                border: none;
                border-radius: 25px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background: #c62a40;
            }
        """)
        send_btn.clicked.connect(self.process_query)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        # ========== دکمه‌های عملیات ==========
        actions = QHBoxLayout()
        
        classify_btn = QPushButton("🏷️ دسته‌بندی تراکنش")
        classify_btn.setToolTip("تشخیص خودکار حساب مناسب برای یک شرح تراکنش")
        classify_btn.clicked.connect(self.classify_demo)
        actions.addWidget(classify_btn)
        
        predict_btn = QPushButton("📈 پیش‌بینی موجودی")
        predict_btn.setToolTip("پیش‌بینی جریان نقدی ۳ ماه آینده با LSTM")
        predict_btn.clicked.connect(self.predict_demo)
        actions.addWidget(predict_btn)
        
        anomaly_btn = QPushButton("🔍 بررسی اسناد")
        anomaly_btn.setToolTip("بررسی اسناد ثبت شده و تشخیص موارد مشکوک")
        anomaly_btn.clicked.connect(self.check_anomalies)
        actions.addWidget(anomaly_btn)
        
        train_btn = QPushButton("🧠 آموزش مدل")
        train_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
            }
            QPushButton:hover {
                background: #388E3C;
            }
        """)
        train_btn.setToolTip("آموزش مدل با اسناد حسابداری موجود")
        train_btn.clicked.connect(self.train_model_dialog)
        actions.addWidget(train_btn)
        
        layout.addLayout(actions)
        
        # ========== پیشنهادات سریع ==========
        quick_layout = QHBoxLayout()
        quick_label = QLabel("💡 پیشنهادات:")
        quick_label.setStyleSheet("color: #888;")
        quick_layout.addWidget(quick_label)
        
        suggestions = ["💰 موجودی صندوق", "📊 سود ماه", "🔮 پیش‌بینی", "🏷️ دسته‌بندی"]
        for text in suggestions:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background: #0f3460;
                    padding: 6px 12px;
                    border-radius: 15px;
                    font-size: 9pt;
                }
                QPushButton:hover {
                    background: #1a4a7a;
                }
            """)
            btn.clicked.connect(lambda checked, t=text: self.quick_query(t))
            quick_layout.addWidget(btn)
        
        quick_layout.addStretch()
        layout.addLayout(quick_layout)
    
    def add_message(self, sender: str, text: str):
        """افزودن پیام به تاریخچه چت"""
        timestamp = datetime.now().strftime("%H:%M")
        
        if sender == "user":
            prefix = "👤 شما"
            color = "#4CAF50"
            bg_color = "#1a3a1a"
        else:
            prefix = "🤖 ImanAI"
            color = "#e94560"
            bg_color = "#3a1a1a"
        
        formatted = f'''
        <div style="margin-bottom: 15px;">
            <span style="color: #888; font-size: 9pt;">[{timestamp}]</span>
            <span style="background: {bg_color}; color: {color}; padding: 2px 8px; border-radius: 12px; font-weight: bold; margin: 0 8px;">{prefix}</span><br>
            <span style="color: #eee; font-size: 11pt; margin-left: 60px;">{text.replace(chr(10), "<br>")}</span>
        </div>
        '''
        
        current = self.chat_history.toHtml()
        self.chat_history.setHtml(current + formatted)
        
        # اسکرول به پایین
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )
    
    def quick_query(self, text: str):
        """اجرای سریع یک کوئری"""
        if text == "💰 موجودی صندوق":
            self.query_input.setText("موجودی صندوق چقدره؟")
        elif text == "📊 سود ماه":
            self.query_input.setText("سود این ماه چقدر بود؟")
        elif text == "🔮 پیش‌بینی":
            self.query_input.setText("پیش‌بینی موجودی ۳ ماه آینده")
        elif text == "🏷️ دسته‌بندی":
            self.query_input.setText('دسته‌بندی: "خرید از دیجیکالا"')
        
        self.process_query()
    
    def process_query(self):
        """پردازش سوال کاربر"""
        query = self.query_input.text().strip()
        if not query:
            return
        
        self.add_message("user", query)
        self.query_input.clear()
        
        # نمایش "در حال تایپ..."
        self.add_message("assistant", "⏳ در حال تحلیل...")
        
        # پردازش
        QTimer.singleShot(500, lambda: self._process_query_async(query))
    
    def _process_query_async(self, query: str):
        """پردازش غیرهمزمان کوئری"""
        # حذف پیام "در حال تایپ"
        current = self.chat_history.toHtml()
        current = current.replace("⏳ در حال تحلیل...", "")
        self.chat_history.setHtml(current)
        
        # دریافت پاسخ
        response = self.get_intelligent_response(query)
        self.add_message("assistant", response)
    
    def get_intelligent_response(self, query: str) -> str:
        """پاسخ هوشمند با استفاده از ImanAI"""
        query_lower = query.lower()
        
        # ========== موجودی حساب ==========
        if "موجودی" in query_lower or "مانده" in query_lower:
            if "صندوق" in query_lower:
                balance = AccountingHelper.get_account_balance("1101")
                return f"💰 موجودی صندوق: **{balance:,.0f}** ریال"
            
            elif "بانک" in query_lower:
                balance = AccountingHelper.get_account_balance("1102")
                return f"🏦 موجودی بانک: **{balance:,.0f}** ریال"
            
            elif "دریافتنی" in query_lower or "طلب" in query_lower:
                balance = AccountingHelper.get_account_balance("1103")
                return f"📥 حساب‌های دریافتنی: **{balance:,.0f}** ریال"
            
            elif "پرداختنی" in query_lower or "بدهی" in query_lower:
                balance = AccountingHelper.get_account_balance("2101")
                return f"📤 حساب‌های پرداختنی: **{balance:,.0f}** ریال"
            
            else:
                return "❓ لطفاً حساب مورد نظر را مشخص کنید:\n• صندوق\n• بانک\n• دریافتنی\n• پرداختنی"
        
        # ========== دسته‌بندی تراکنش ==========
        elif "دسته" in query_lower or "حساب" in query_lower or "طبقه" in query_lower:
            # استخراج شرح
            match = re.search(r'["\'](.+?)["\']|«(.+?)»|"(.+?)"', query)
            if match:
                desc = match.group(1) or match.group(2) or match.group(3)
            else:
                # حذف کلمات کلیدی
                desc = query
                for word in ["دسته‌بندی", "دسته", "حساب", "طبقه", "بندی", ":"]:
                    desc = desc.replace(word, "")
                desc = desc.strip()
            
            if not desc or len(desc) < 3:
                return "❓ لطفاً شرح تراکنش را مشخص کنید.\nمثال: دسته‌بندی: \"خرید از دیجیکالا\""
            
            # پیش‌بینی
            result = self.classifier.predict(desc)
            
            response = f"""
📊 **تحلیل تراکنش با ImanAI**

📝 **شرح:** {desc}

✅ **حساب پیشنهادی:** {result['account_name']} ({result['account_code']})
📊 **نوع حساب:** {result['account_type']}
🎯 **میزان اطمینان:** {result['confidence']*100:.1f}%
🔧 **روش:** {'شبکه عصبی' if result['method'] == 'neural_network' else 'کلمات کلیدی'}
"""
            
            # پیشنهادات دیگر
            if "suggestions" in result and result['method'] == 'neural_network':
                response += "\n💡 **پیشنهادات دیگر:**\n"
                for sug in result['suggestions'][:2]:
                    if sug['code'] != result['account_code']:
                        response += f"   • {sug['name']}: {sug['confidence']*100:.1f}%\n"
            
            return response
        
        # ========== پیش‌بینی ==========
        elif "پیش‌بینی" in query_lower or "پیش بینی" in query_lower:
            return self.predict_cashflow()
        
        # ========== سود و زیان ==========
        elif "سود" in query_lower or "زیان" in query_lower:
            with get_db() as conn:
                c = conn.cursor()
                
                # درآمدها
                c.execute('''
                    SELECT COALESCE(SUM(vi.credit - vi.debit), 0)
                    FROM voucher_items vi
                    JOIN accounts a ON vi.account_code = a.code
                    WHERE a.type = 'income'
                ''')
                income = c.fetchone()[0] or 0
                
                # هزینه‌ها
                c.execute('''
                    SELECT COALESCE(SUM(vi.debit - vi.credit), 0)
                    FROM voucher_items vi
                    JOIN accounts a ON vi.account_code = a.code
                    WHERE a.type = 'expense'
                ''')
                expense = c.fetchone()[0] or 0
            
            profit = income - expense
            
            if profit >= 0:
                return f"""
📈 **گزارش سود و زیان**

💰 **جمع درآمدها:** {income:,.0f} ریال
💸 **جمع هزینه‌ها:** {expense:,.0f} ریال

✅ **سود خالص:** **{profit:,.0f}** ریال
📊 **حاشیه سود:** {(profit/income*100 if income > 0 else 0):.1f}%
"""
            else:
                return f"""
📉 **گزارش سود و زیان**

💰 **جمع درآمدها:** {income:,.0f} ریال
💸 **جمع هزینه‌ها:** {expense:,.0f} ریال

⚠️ **زیان خالص:** **{abs(profit):,.0f}** ریال
"""
        
        # ========== راهنما ==========
        elif "راهنما" in query_lower or "help" in query_lower:
            return """
📚 **راهنمای دستیار ImanAI**

می‌توانید سوالات زیر را بپرسید:

💰 **موجودی حساب:**
• موجودی صندوق چقدره؟
• موجودی بانک چقدره؟

📊 **گزارشات مالی:**
• سود این ماه چقدر بود؟

🔮 **پیش‌بینی:**
• پیش‌بینی موجودی ۳ ماه آینده

🏷️ **دسته‌بندی هوشمند:**
• دسته‌بندی: "خرید از دیجیکالا"
• حساب: "پرداخت قبض برق"

🧠 **آموزش مدل:**
• روی دکمه "آموزش مدل" کلیک کنید تا با داده‌های شما آموزش ببیند.
"""
        
        # ========== سلام و احوالپرسی ==========
        elif any(word in query_lower for word in ["سلام", "خوبی", "چطوری", "hey", "hi"]):
            return f"""
👋 سلام! خوبم، ممنون که می‌پرسی!

من دستیار هوشمند ImanAI هستم.
🧠 نسخه: ۲.۰
📊 وضعیت مدل: {'✅ آموزش دیده' if self.model_info['is_trained'] else '⚠️ کلمات کلیدی'}

چطور می‌تونم کمکت کنم؟
(برای دیدن راهنما، بگو "راهنما")
"""
        
        # ========== درباره ==========
        elif "درباره" in query_lower or "about" in query_lower:
            return f"""
🤖 **دستیار هوشمند ImanAI**

📌 **نسخه:** ۲.۰
🧠 **موتور:** ImanAI Core v6.2
📊 **وضعیت مدل:** {'✅ آموزش دیده' if self.model_info['is_trained'] else '⚠️ کلمات کلیدی'}
📚 **دایره لغات:** {self.model_info['vocab_size']} کلمه

🔧 **قابلیت‌ها:**
• دسته‌بندی هوشمند تراکنش با شبکه عصبی
• پیش‌بینی جریان نقدی با LSTM
• تشخیص اسناد ناموزون
• پاسخ به سوالات مالی به زبان فارسی

👨‍💻 **توسعه:** تیم ImanAI
"""
        
        return "🤔 متوجه نشدم. لطفاً واضح‌تر بپرسید یا بگویید \"راهنما\"."
    
    def classify_demo(self):
        """نمایش دموی دسته‌بندی"""
        dialog = ClassificationDialog(self.classifier, self)
        dialog.exec_()
    
    def predict_demo(self):
        """نمایش دموی پیش‌بینی"""
        response = self.predict_cashflow()
        self.add_message("assistant", response)
    
    def predict_cashflow(self) -> str:
        """پیش‌بینی جریان نقدی"""
        # تلاش برای دریافت داده‌های واقعی
        try:
            cashflow_data = self.collector.collect_cashflow_data()
            if len(cashflow_data) >= 6:
                historical = cashflow_data[-6:]
            else:
                historical = [10000000, 12500000, 11800000, 15000000, 14200000, 16800000]
        except:
            historical = [10000000, 12500000, 11800000, 15000000, 14200000, 16800000]
        
        predictions = self.predictor.predict_next(historical, 3)
        
        response = f"""
🔮 **پیش‌بینی جریان نقدی با ImanAI LSTM**

📊 **۶ ماه گذشته:**
"""
        for i, val in enumerate(historical):
            response += f"   ماه {i+1}: {val:,.0f} ریال\n"
        
        response += "\n📈 **پیش‌بینی ۳ ماه آینده:**\n"
        
        for p in predictions:
            trend = "📈" if p['predicted_balance'] > historical[-1] else "📉"
            response += f"   {trend} **{p['month']}**: {p['predicted_balance']:,.0f} ریال (اطمینان {p['confidence']*100:.0f}%)\n"
        
        # هشدار
        if predictions and predictions[-1]['predicted_balance'] < 0:
            response += f"\n⚠️ **هشدار:** موجودی در {predictions[-1]['month']} منفی می‌شود!"
        elif predictions:
            last_pred = predictions[-1]['predicted_balance']
            if last_pred < historical[-1] * 0.7:
                response += "\n⚠️ **توجه:** روند نزولی قابل توجه است!"
        
        return response
    
    def check_anomalies(self):
        """بررسی اسناد مشکوک"""
        try:
            anomalies = self.collector.collect_anomaly_data()
            
            if not anomalies:
                self.add_message("assistant", "✅ تمام اسناد بررسی شدند و مورد مشکوکی یافت نشد!")
                return
            
            response = f"""
🔍 **بررسی اسناد حسابداری**

📊 **{len(anomalies)}** مورد نیاز به بررسی دارد:

"""
            for a in anomalies[:5]:
                response += f"""
🔸 **سند شماره {a['voucher_id']}**
   📝 شرح: {a['description'][:50]}...
   💰 بدهکار: {a['total_debit']:,.0f} | بستانکار: {a['total_credit']:,.0f}
   ⚠️ اختلاف: {a['difference']:,.0f} ریال
"""
            
            if len(anomalies) > 5:
                response += f"\n... و {len(anomalies) - 5} مورد دیگر"
            
            self.add_message("assistant", response)
            
        except Exception as e:
            self.add_message("assistant", f"❌ خطا در بررسی اسناد: {str(e)}")
    
    def train_model_dialog(self):
        """دیالوگ آموزش مدل"""
        reply = QMessageBox.question(
            self, "آموزش مدل ImanAI",
            "🧠 **آموزش مدل با داده‌های واقعی**\n\n"
            "مدل با استفاده از اسناد حسابداری موجود در سیستم آموزش می‌بیند.\n"
            "این کار ممکن است چند دقیقه طول بکشد.\n\n"
            "آیا مایل به ادامه هستید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.train_model()
    
    def train_model(self):
        """آموزش مدل با داده‌های واقعی"""
        self.add_message("assistant", "🧠 در حال جمع‌آوری داده‌های آموزشی...")
        QApplication.processEvents()
        
        try:
            # جمع‌آوری داده‌ها
            data = self.collector.collect_transaction_data()
            
            if len(data) < 10:
                self.add_message("assistant", 
                    f"⚠️ داده کافی برای آموزش وجود ندارد (فقط {len(data)} نمونه).\n"
                    "حداقل ۱۰ تراکنش با حساب‌های مشخص نیاز است.")
                return
            
            texts = [d[0] for d in data]
            labels = [d[1] for d in data]
            
            self.add_message("assistant", 
                f"📊 **{len(data)}** تراکنش برای آموزش جمع‌آوری شد.\n"
                "🧠 در حال آموزش مدل...")
            QApplication.processEvents()
            
            # آموزش
            result = self.classifier.train(texts, labels, epochs=50, save=True)
            
            # بروزرسانی اطلاعات مدل
            self.model_info = self.classifier.get_model_info()
            
            response = f"""
✅ **آموزش با موفقیت انجام شد!**

📊 **نتایج آموزش:**
• تعداد نمونه: {result['samples']}
• دایره لغات: {result['vocab_size']} کلمه
• loss نهایی: {result['history'][-1]:.4f}
"""
            
            if 'val_accuracy' in result['metrics']:
                response += f"• دقت اعتبارسنجی: {result['metrics']['val_accuracy']*100:.1f}%"
            
            response += "\n\n🎉 مدل آماده استفاده است!"
            
            self.add_message("assistant", response)
            
        except Exception as e:
            self.add_message("assistant", f"❌ خطا در آموزش مدل: {str(e)}")


class ClassificationDialog(QDialog):
    """دیالوگ دسته‌بندی تراکنش"""
    
    def __init__(self, classifier, parent=None):
        super().__init__(parent)
        self.classifier = classifier
        self.setWindowTitle("🏷️ دسته‌بندی هوشمند تراکنش")
        self.setGeometry(300, 300, 600, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # توضیح
        title = QLabel("دسته‌بندی هوشمند تراکنش با ImanAI")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #e94560;")
        layout.addWidget(title)
        
        desc = QLabel("شرح تراکنش را وارد کنید تا حساب مناسب پیشنهاد شود:")
        layout.addWidget(desc)
        
        # ورودی
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("مثال: خرید از دیجیکالا ۲,۵۰۰,۰۰۰ تومان")
        self.input_text.setMaximumHeight(100)
        layout.addWidget(self.input_text)
        
        # دکمه
        classify_btn = QPushButton("🔍 تحلیل تراکنش")
        classify_btn.setStyleSheet("padding: 10px; background: #e94560;")
        classify_btn.clicked.connect(self.classify)
        layout.addWidget(classify_btn)
        
        # نتیجه
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("background: #1a1a2e; color: #eee;")
        layout.addWidget(self.result_text)
        
        # نمونه‌ها
        samples_label = QLabel("نمونه‌های آماده:")
        layout.addWidget(samples_label)
        
        samples_layout = QHBoxLayout()
        samples = ["خرید از دیجیکالا", "پرداخت حقوق", "قبض برق", "فروش کالا"]
        for s in samples:
            btn = QPushButton(s)
            btn.clicked.connect(lambda checked, text=s: self.input_text.setText(text))
            samples_layout.addWidget(btn)
        layout.addLayout(samples_layout)
    
    def classify(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "خطا", "لطفاً شرح تراکنش را وارد کنید!")
            return
        
        result = self.classifier.predict(text)
        
        response = f"""
📊 **نتیجه تحلیل**

📝 **شرح:** {text}

✅ **حساب پیشنهادی:** {result['account_name']} ({result['account_code']})
📊 **نوع:** {result['account_type']}
🎯 **اطمینان:** {result['confidence']*100:.1f}%
🔧 **روش:** {result['method']}
"""
        
        if "suggestions" in result:
            response += "\n💡 **پیشنهادات دیگر:**\n"
            for sug in result['suggestions'][:3]:
                response += f"• {sug['name']}: {sug['confidence']*100:.1f}%\n"
        
        self.result_text.setText(response)
