"""
آموزش مدل‌های ImanAI با داده‌های واقعی
"""

import numpy as np
from pathlib import Path
from datetime import datetime
import json

from imanai import ImanAI, Sequential, Dense, Dropout, LightLSTM, to_categorical
from ai.data_collector import AccountingDataCollector


class ModelTrainer:
    """آموزش و مدیریت مدل‌های ImanAI"""
    
    def __init__(self):
        self.collector = AccountingDataCollector()
        self.models_dir = Path("ai/models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
    
    def train_transaction_classifier(self, epochs: int = 100, force_retrain: bool = False):
        """
        آموزش مدل دسته‌بندی تراکنش با داده‌های واقعی
        """
        print("\n" + "="*60)
        print("🧠 آموزش مدل دسته‌بندی تراکنش")
        print("="*60)
        
        # جمع‌آوری داده‌ها
        data = self.collector.collect_transaction_data()
        
        if len(data) < 10:
            print("⚠️ داده کافی برای آموزش وجود ندارد. از داده‌های نمونه استفاده می‌شود.")
            data = self._get_sample_data()
        
        # آماده‌سازی داده‌ها
        texts, labels = zip(*data)
        
        # ساخت وکتورایزر
        vocab = self._build_vocabulary(texts)
        print(f"📚 دایره لغات: {len(vocab)} کلمه")
        
        # تبدیل متون به بردار
        X = np.array([self._vectorize(t, vocab) for t in texts], dtype=np.float32)
        y = to_categorical(list(labels), num_classes=8)
        
        print(f"📊 داده‌های آموزش: {len(X)} نمونه")
        print(f"📊 توزیع کلاس‌ها: {np.bincount(list(labels))}")
        
        # ساخت مدل
        ai = ImanAI()
        model = ai.create_model("TransactionClassifier_v1")
        
        # معماری شبکه
        model.add(Dense(len(vocab), 128, 'relu'))
        model.add(Dropout(0.3))
        model.add(Dense(128, 64, 'relu'))
        model.add(Dropout(0.2))
        model.add(Dense(64, 32, 'relu'))
        model.add(Dense(32, 8, 'softmax'))
        
        model.compile(lr=0.001)
        model.summary()
        
        # آموزش
        print(f"\n🚀 شروع آموزش - {epochs} دوره...")
        history = model.fit(X, y, epochs=epochs, batch_size=32, verbose=1)
        
        # ذخیره مدل و وکتورایزر
        model_path = self.models_dir / "transaction_classifier.pkl"
        model.save(str(model_path))
        
        vocab_path = self.models_dir / "vocabulary.json"
        with open(vocab_path, "w", encoding="utf-8") as f:
            json.dump(vocab, f, ensure_ascii=False)
        
        # ذخیره گزارش آموزش
        report = {
            "date": datetime.now().isoformat(),
            "samples": len(X),
            "vocab_size": len(vocab),
            "epochs": epochs,
            "final_loss": float(history[-1]),
            "class_distribution": [int(x) for x in np.bincount(list(labels))]
        }
        
        with open(self.models_dir / "training_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ مدل با موفقیت آموزش دید و ذخیره شد!")
        print(f"📁 مسیر: {model_path}")
        print(f"📊 loss نهایی: {history[-1]:.4f}")
        
        return model, history
    
    def train_cashflow_predictor(self, epochs: int = 200):
        """
        آموزش مدل LSTM برای پیش‌بینی جریان نقدی
        """
        print("\n" + "="*60)
        print("📈 آموزش مدل پیش‌بینی جریان نقدی (LSTM)")
        print("="*60)
        
        # جمع‌آوری داده‌ها
        cashflow_data = self.collector.collect_cashflow_data()
        
        if len(cashflow_data) < 12:
            print("⚠️ داده کافی برای آموزش LSTM وجود ندارد. از داده‌های نمونه استفاده می‌شود.")
            cashflow_data = [10000000, 12500000, 11800000, 15000000, 14200000, 16800000,
                           15500000, 18000000, 17200000, 19500000, 18800000, 21000000]
        
        print(f"📊 {len(cashflow_data)} ماه داده جریان نقدی")
        
        # آماده‌سازی sequences برای LSTM
        seq_length = 6
        X, y = [], []
        
        for i in range(len(cashflow_data) - seq_length):
            X.append(cashflow_data[i:i+seq_length])
            y.append(cashflow_data[i+seq_length])
        
        if len(X) == 0:
            print("❌ داده کافی برای ساخت sequence نیست")
            return None
        
        X = np.array(X, dtype=np.float32).reshape(-1, seq_length, 1)
        y = np.array(y, dtype=np.float32).reshape(-1, 1)
        
        # نرمال‌سازی
        X_mean, X_std = np.mean(X), np.std(X)
        y_mean, y_std = np.mean(y), np.std(y)
        
        X_norm = (X - X_mean) / (X_std + 1e-8)
        y_norm = (y - y_mean) / (y_std + 1e-8)
        
        print(f"📊 داده‌های آموزش: {len(X)} sequence")
        
        # ساخت مدل LSTM
        ai = ImanAI()
        model = ai.create_model("CashFlowLSTM_v1")
        
        model.add(LightLSTM(input_dim=1, hidden_dim=32, return_sequences=True))
        model.add(LightLSTM(input_dim=32, hidden_dim=16, return_sequences=False))
        model.add(Dense(16, 8, 'relu'))
        model.add(Dense(8, 1, 'linear'))
        
        model.compile(lr=0.001)
        model.summary()
        
        # آموزش
        print(f"\n🚀 شروع آموزش LSTM - {epochs} دوره...")
        history = model.fit(X_norm, y_norm, epochs=epochs, batch_size=4, verbose=1)
        
        # ذخیره مدل و پارامترهای نرمال‌سازی
        model.save(str(self.models_dir / "cashflow_lstm.pkl"))
        
        norm_params = {
            "X_mean": float(X_mean),
            "X_std": float(X_std),
            "y_mean": float(y_mean),
            "y_std": float(y_std),
            "seq_length": seq_length
        }
        
        with open(self.models_dir / "cashflow_norm.json", "w") as f:
            json.dump(norm_params, f, indent=2)
        
        print(f"\n✅ مدل LSTM با موفقیت آموزش دید!")
        print(f"📊 loss نهایی: {history[-1]:.4f}")
        
        return model, history
    
    def _build_vocabulary(self, texts: List[str], min_freq: int = 2) -> List[str]:
        """ساخت دایره لغات از متون آموزشی"""
        from collections import Counter
        
        # شکستن متون به کلمات
        all_words = []
        for text in texts:
            words = text.split()
            all_words.extend(words)
        
        # شمارش تکرار
        word_counts = Counter(all_words)
        
        # انتخاب کلمات با تکرار کافی
        vocab = [word for word, count in word_counts.items() if count >= min_freq]
        
        # اضافه کردن کلمات کلیدی مهم
        keywords = ["صندوق", "بانک", "فروش", "خرید", "حقوق", "اجاره", "قبض", "واریز", "برداشت"]
        for kw in keywords:
            if kw not in vocab:
                vocab.append(kw)
        
        return sorted(vocab)
    
    def _vectorize(self, text: str, vocab: List[str]) -> np.ndarray:
        """تبدیل متن به بردار ویژگی"""
        vec = np.zeros(len(vocab), dtype=np.float32)
        words = text.split()
        
        for i, word in enumerate(vocab):
            if word in words:
                vec[i] = 1.0
        
        return vec
    
    def _get_sample_data(self) -> List[Tuple[str, int]]:
        """داده‌های نمونه برای آموزش اولیه"""
        return [
            ("واریز به صندوق", 0),
            ("برداشت از صندوق", 0),
            ("دریافت نقدی", 0),
            ("پرداخت نقدی", 0),
            ("واریز به حساب بانک", 1),
            ("برداشت از بانک", 1),
            ("انتقال به حساب بانک", 1),
            ("دریافت از مشتری", 1),
            ("فروش کالا", 2),
            ("فروش محصولات", 2),
            ("درآمد فروش", 2),
            ("فاکتور فروش", 2),
            ("خرید کالا", 3),
            ("خرید ملزومات", 3),
            ("خرید از دیجیکالا", 3),
            ("فاکتور خرید", 3),
            ("پرداخت حقوق", 4),
            ("حقوق پرسنل", 4),
            ("دستمزد کارگران", 4),
            ("عیدی کارمندان", 4),
            ("پرداخت اجاره", 5),
            ("اجاره دفتر", 5),
            ("اجاره ماهانه", 5),
            ("رهن ساختمان", 5),
            ("پرداخت قبض برق", 6),
            ("قبض آب", 6),
            ("هزینه تلفن", 6),
            ("اینترنت", 6),
            ("گاز بها", 6),
            ("تعمیرات ساختمان", 7),
            ("سرویس دستگاه", 7),
            ("تعمیر کولر", 7),
            ("نگهداری تاسیسات", 7),
        ]
