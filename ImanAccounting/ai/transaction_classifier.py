#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
دسته‌بندی هوشمند تراکنش‌های حسابداری با ImanAI Core v6.2
قابلیت‌ها:
- آموزش با داده‌های واقعی
- بارگذاری مدل آموزش دیده
- پیش‌بینی با اطمینان
- Fallback به روش کلمات کلیدی
- ذخیره و بازیابی مدل
"""

import re
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter
from datetime import datetime

# کتابخونه AI خودمون
from imanai import ImanAI, Sequential, Dense, Dropout, to_categorical


class TransactionClassifier:
    """
    دسته‌بندی هوشمند تراکنش‌های حسابداری
    
    استفاده:
        classifier = TransactionClassifier()
        result = classifier.predict("خرید از دیجیکالا ۲ میلیون تومان")
        print(result['account_name'])  # خرید کالا
    """
    
    # نگاشت کلاس به حساب
    CLASS_TO_ACCOUNT = {
        0: {"code": "1101", "name": "صندوق", "type": "asset"},
        1: {"code": "1102", "name": "بانک", "type": "asset"},
        2: {"code": "4101", "name": "فروش کالا", "type": "income"},
        3: {"code": "5101", "name": "خرید کالا", "type": "expense"},
        4: {"code": "5102", "name": "هزینه حقوق", "type": "expense"},
        5: {"code": "5103", "name": "هزینه اجاره", "type": "expense"},
        6: {"code": "5104", "name": "هزینه آب و برق", "type": "expense"},
        7: {"code": "5105", "name": "هزینه تعمیرات", "type": "expense"},
    }
    
    # کلمات کلیدی برای Fallback
    KEYWORDS = {
        "1101": ["صندوق", "نقد", "دریافت نقدی", "پرداخت نقدی"],
        "1102": ["بانک", "واریز", "برداشت", "کارت", "شبا", "ساتنا", "پایا", "atm"],
        "4101": ["فروش", "درآمد", "فاکتور فروش", "مشتری", "رسید فروش"],
        "5101": ["خرید", "کالا", "جنس", "محصول", "دیجیکالا", "ترب", "بازار", "فاکتور خرید"],
        "5102": ["حقوق", "دستمزد", "پرسنل", "کارمند", "عیدی", "پاداش", "سنوات"],
        "5103": ["اجاره", "رهن", "ساختمان", "دفتر", "مغازه"],
        "5104": ["آب", "برق", "گاز", "تلفن", "اینترنت", "قبض", "شارژ", "بسته اینترنت"],
        "5105": ["تعمیر", "سرویس", "نگهداری", "تعمیرات", "بازسازی"],
    }
    
    def __init__(self, model_dir: str = None):
        """
        Args:
            model_dir: مسیر پوشه مدل‌ها (پیش‌فرض: ai/models)
        """
        self.model = None
        self.vocab = []
        self.vocab_size = 0
        self.num_classes = len(self.CLASS_TO_ACCOUNT)
        self.is_trained = False
        self.training_history = []
        
        # تنظیم مسیر مدل
        if model_dir is None:
            model_dir = Path(__file__).parent / "models"
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_path = self.model_dir / "transaction_classifier.pkl"
        self.vocab_path = self.model_dir / "vocabulary.json"
        self.meta_path = self.model_dir / "classifier_meta.json"
        
        # تلاش برای بارگذاری مدل آموزش دیده
        if self.model_path.exists() and self.vocab_path.exists():
            self._load_model()
        else:
            print("ℹ️ مدل آموزش دیده یافت نشد. از روش کلمات کلیدی استفاده می‌شود.")
            print("   برای آموزش مدل: classifier.train(descriptions, labels)")
            self._init_default_vocab()
    
    def _init_default_vocab(self):
        """دایره لغات پیش‌فرض"""
        default_words = set()
        for keywords in self.KEYWORDS.values():
            for kw in keywords:
                default_words.update(kw.split())
        self.vocab = sorted(list(default_words))
        self.vocab_size = len(self.vocab)
    
    def _build_model(self, input_dim: int = None):
        """ساخت معماری شبکه عصبی"""
        if input_dim is None:
            input_dim = self.vocab_size
        
        self.ai = ImanAI()
        self.model = self.ai.create_model("TransactionClassifier_v2")
        
        # معماری بهینه برای دسته‌بندی متن
        self.model.add(Dense(input_dim, 128, 'relu'))
        self.model.add(Dropout(0.3))
        self.model.add(Dense(128, 64, 'relu'))
        self.model.add(Dropout(0.2))
        self.model.add(Dense(64, 32, 'relu'))
        self.model.add(Dense(32, self.num_classes, 'softmax'))
        
        self.model.compile(lr=0.001)
        
        print(f"✅ مدل با {input_dim} ویژگی ورودی ساخته شد")
    
    def _clean_text(self, text: str) -> str:
        """پاکسازی و نرمال‌سازی متن فارسی"""
        if not text:
            return ""
        
        # حذف اعداد
        text = re.sub(r'\d+', ' ', text)
        # حذف علائم نگارشی
        text = re.sub(r'[،,\.\/\\\-_:;()\[\]{}«»""\'\'؟!٪٬]', ' ', text)
        # نرمال‌سازی کاراکترهای فارسی
        text = text.replace('ي', 'ی').replace('ك', 'ک')
        # حذف فاصله‌های اضافی
        text = ' '.join(text.split())
        
        return text.lower()
    
    def _vectorize(self, text: str) -> np.ndarray:
        """تبدیل متن به بردار ویژگی"""
        vec = np.zeros(self.vocab_size, dtype=np.float32)
        words = self._clean_text(text).split()
        
        for i, word in enumerate(self.vocab):
            if word in words:
                vec[i] = 1.0
            # بررسی تطابق جزئی
            elif any(word in w or w in word for w in words):
                vec[i] = 0.5
        
        return vec
    
    def _keyword_predict(self, text: str) -> Dict:
        """پیش‌بینی بر اساس کلمات کلیدی (Fallback)"""
        text = self._clean_text(text)
        scores = {code: 0.0 for code in self.KEYWORDS.keys()}
        
        for code, keywords in self.KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[code] += 1.0
                # بررسی کلمات تشکیل‌دهنده
                kw_words = kw.split()
                if len(kw_words) > 1:
                    matches = sum(1 for w in kw_words if w in text)
                    scores[code] += matches * 0.5
        
        # پیدا کردن بهترین حساب
        max_score = max(scores.values()) if scores else 0
        
        if max_score > 0:
            best_code = max(scores, key=scores.get)
            confidence = min(max_score / 3, 0.8)  # حداکثر ۸۰٪
            account = next(v for v in self.CLASS_TO_ACCOUNT.values() if v["code"] == best_code)
            
            return {
                "account_code": best_code,
                "account_name": account["name"],
                "account_type": account["type"],
                "confidence": round(confidence, 3),
                "method": "keyword_matching",
                "all_scores": scores
            }
        
        # پیش‌فرض: خرید کالا
        return {
            "account_code": "5101",
            "account_name": "خرید کالا",
            "account_type": "expense",
            "confidence": 0.3,
            "method": "default",
            "all_scores": scores
        }
    
    def _nn_predict(self, text: str) -> Dict:
        """پیش‌بینی با شبکه عصبی"""
        vec = self._vectorize(text).reshape(1, -1)
        
        try:
            probs = self.model.predict(vec)[0]
            pred_class = int(np.argmax(probs))
            confidence = float(probs[pred_class])
            
            account = self.CLASS_TO_ACCOUNT[pred_class]
            
            # محاسبه ۳ پیشنهاد برتر
            top3_indices = np.argsort(probs)[-3:][::-1]
            top3_suggestions = []
            for idx in top3_indices:
                acc = self.CLASS_TO_ACCOUNT[idx]
                top3_suggestions.append({
                    "code": acc["code"],
                    "name": acc["name"],
                    "confidence": float(probs[idx])
                })
            
            return {
                "account_code": account["code"],
                "account_name": account["name"],
                "account_type": account["type"],
                "confidence": round(confidence, 3),
                "method": "neural_network",
                "class_id": pred_class,
                "suggestions": top3_suggestions
            }
            
        except Exception as e:
            print(f"⚠️ خطا در پیش‌بینی شبکه عصبی: {e}")
            return self._keyword_predict(text)
    
    def predict(self, description: str) -> Dict:
        """
        پیش‌بینی حساب مناسب برای یک شرح تراکنش
        
        Args:
            description: شرح تراکنش (مثال: "خرید از دیجیکالا")
        
        Returns:
            Dict شامل:
                - account_code: کد حساب
                - account_name: نام حساب
                - account_type: نوع حساب
                - confidence: میزان اطمینان (۰ تا ۱)
                - method: روش پیش‌بینی
                - suggestions: پیشنهادات دیگر (در صورت استفاده از NN)
        """
        if not description or not description.strip():
            return {
                "account_code": "5101",
                "account_name": "خرید کالا",
                "account_type": "expense",
                "confidence": 0.0,
                "method": "empty_input",
                "error": "شرح تراکنش خالی است"
            }
        
        # اگر مدل آموزش دیده موجوده، از NN استفاده کن
        if self.model is not None and self.is_trained:
            return self._nn_predict(description)
        else:
            return self._keyword_predict(description)
    
    def predict_batch(self, descriptions: List[str]) -> List[Dict]:
        """پیش‌بینی برای چند تراکنش"""
        return [self.predict(desc) for desc in descriptions]
    
    def train(self, texts: List[str], labels: List[int], 
              epochs: int = 100, validation_split: float = 0.2,
              save: bool = True) -> Dict:
        """
        آموزش مدل با داده‌های واقعی
        
        Args:
            texts: لیست شرح تراکنش‌ها
            labels: لیست برچسب‌ها (۰ تا ۷)
            epochs: تعداد دوره‌های آموزش
            validation_split: نسبت داده‌های اعتبارسنجی
            save: ذخیره مدل بعد از آموزش
        
        Returns:
            Dict شامل تاریخچه آموزش و معیارهای ارزیابی
        """
        print("\n" + "="*60)
        print("🧠 آموزش مدل دسته‌بندی تراکنش")
        print("="*60)
        
        if len(texts) == 0:
            raise ValueError("داده‌ای برای آموزش وجود ندارد")
        
        # ساخت دایره لغات از داده‌ها
        self._build_vocabulary(texts)
        print(f"📚 دایره لغات: {self.vocab_size} کلمه")
        
        # تبدیل داده‌ها
        X = np.array([self._vectorize(t) for t in texts], dtype=np.float32)
        y = to_categorical(labels, self.num_classes)
        
        # تقسیم داده‌ها
        n_val = int(len(X) * validation_split)
        indices = np.random.permutation(len(X))
        
        X_train = X[indices[n_val:]]
        y_train = y[indices[n_val:]]
        X_val = X[indices[:n_val]] if n_val > 0 else None
        y_val = y[indices[:n_val]] if n_val > 0 else None
        
        print(f"📊 داده‌های آموزش: {len(X_train)} نمونه")
        if X_val is not None:
            print(f"📊 داده‌های اعتبارسنجی: {len(X_val)} نمونه")
        
        # توزیع کلاس‌ها
        unique, counts = np.unique(labels, return_counts=True)
        print(f"📊 توزیع کلاس‌ها: {dict(zip(unique, counts))}")
        
        # ساخت و آموزش مدل
        self._build_model()
        self.model.summary()
        
        print(f"\n🚀 شروع آموزش - {epochs} دوره...")
        history = self.model.fit(X_train, y_train, epochs=epochs, batch_size=32, verbose=1)
        
        self.training_history = history
        self.is_trained = True
        
        # ارزیابی روی داده‌های اعتبارسنجی
        metrics = {"train_loss": history[-1]}
        
        if X_val is not None:
            val_pred = self.model.predict(X_val)
            val_pred_class = np.argmax(val_pred, axis=1)
            val_true = np.argmax(y_val, axis=1)
            accuracy = np.mean(val_pred_class == val_true)
            metrics["val_accuracy"] = float(accuracy)
            print(f"\n📊 دقت روی داده‌های اعتبارسنجی: {accuracy*100:.2f}%")
        
        # ذخیره مدل
        if save:
            self.save()
        
        print(f"\n✅ آموزش با موفقیت به پایان رسید!")
        
        return {
            "history": history,
            "metrics": metrics,
            "vocab_size": self.vocab_size,
            "samples": len(texts)
        }
    
    def _build_vocabulary(self, texts: List[str], min_freq: int = 2):
        """ساخت دایره لغات از داده‌های آموزشی"""
        all_words = []
        for text in texts:
            cleaned = self._clean_text(text)
            all_words.extend(cleaned.split())
        
        word_counts = Counter(all_words)
        
        # کلمات با تکرار کافی
        vocab = [word for word, count in word_counts.items() if count >= min_freq]
        
        # اضافه کردن کلمات کلیدی مهم
        for keywords in self.KEYWORDS.values():
            for kw in keywords:
                for word in kw.split():
                    if word not in vocab:
                        vocab.append(word)
        
        self.vocab = sorted(set(vocab))
        self.vocab_size = len(self.vocab)
        
        print(f"✅ دایره لغات با {self.vocab_size} کلمه ساخته شد")
    
    def save(self, path: str = None):
        """ذخیره مدل و دایره لغات"""
        if path:
            model_path = Path(path)
            model_dir = model_path.parent
            model_dir.mkdir(parents=True, exist_ok=True)
            vocab_path = model_dir / "vocabulary.json"
            meta_path = model_dir / "classifier_meta.json"
        else:
            model_path = self.model_path
            vocab_path = self.vocab_path
            meta_path = self.meta_path
        
        # ذخیره مدل
        if self.model:
            self.model.save(str(model_path))
        
        # ذخیره دایره لغات
        with open(vocab_path, "w", encoding="utf-8") as f:
            json.dump({
                "vocab": self.vocab,
                "vocab_size": self.vocab_size,
                "class_mapping": self.CLASS_TO_ACCOUNT
            }, f, ensure_ascii=False, indent=2)
        
        # ذخیره متادیتا
        meta = {
            "trained_at": datetime.now().isoformat(),
            "num_classes": self.num_classes,
            "is_trained": self.is_trained,
            "history": self.training_history[-1] if self.training_history else None
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        print(f"💾 مدل در {model_path} ذخیره شد")
    
    def _load_model(self):
        """بارگذاری مدل آموزش دیده"""
        try:
            # بارگذاری دایره لغات
            with open(self.vocab_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.vocab = data["vocab"]
                self.vocab_size = data["vocab_size"]
            
            # ساخت و بارگذاری مدل
            self._build_model()
            self.model.load(str(self.model_path))
            self.is_trained = True
            
            # بارگذاری متادیتا
            if self.meta_path.exists():
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    print(f"📂 مدل آموزش دیده در {meta.get('trained_at', 'نامشخص')}")
            
            print(f"✅ مدل آموزش دیده بارگذاری شد ({self.vocab_size} کلمه)")
            
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری مدل: {e}")
            self.is_trained = False
            self._init_default_vocab()
    
    def get_model_info(self) -> Dict:
        """دریافت اطلاعات مدل"""
        info = {
            "is_trained": self.is_trained,
            "vocab_size": self.vocab_size,
            "num_classes": self.num_classes,
            "classes": self.CLASS_TO_ACCOUNT,
            "model_path": str(self.model_path) if self.model_path.exists() else None
        }
        
        if self.meta_path.exists():
            with open(self.meta_path, "r", encoding="utf-8") as f:
                info["meta"] = json.load(f)
        
        return info
    
    def evaluate(self, texts: List[str], true_labels: List[int]) -> Dict:
        """
        ارزیابی مدل روی داده‌های تست
        
        Returns:
            Dict شامل accuracy, precision, recall, confusion_matrix
        """
        if not self.is_trained:
            raise ValueError("مدل هنوز آموزش ندیده است")
        
        predictions = []
        for text in texts:
            result = self.predict(text)
            pred_class = result.get("class_id", 3)  # پیش‌فرض: خرید کالا
            predictions.append(pred_class)
        
        predictions = np.array(predictions)
        true_labels = np.array(true_labels)
        
        # محاسبه معیارها
        accuracy = np.mean(predictions == true_labels)
        
        # ماتریس درهم‌ریختگی
        confusion = np.zeros((self.num_classes, self.num_classes), dtype=int)
        for t, p in zip(true_labels, predictions):
            confusion[t][p] += 1
        
        # محاسبه precision و recall برای هر کلاس
        precision = []
        recall = []
        for i in range(self.num_classes):
            tp = confusion[i][i]
            fp = confusion[:, i].sum() - tp
            fn = confusion[i, :].sum() - tp
            
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            
            precision.append(float(prec))
            recall.append(float(rec))
        
        return {
            "accuracy": float(accuracy),
            "precision": precision,
            "recall": recall,
            "confusion_matrix": confusion.tolist(),
            "class_names": [self.CLASS_TO_ACCOUNT[i]["name"] for i in range(self.num_classes)]
        }


# ============================================================
# نمونه استفاده
# ============================================================
if __name__ == "__main__":
    print("🧠 تست TransactionClassifier")
    print("="*60)
    
    # ایجاد نمونه
    classifier = TransactionClassifier()
    
    # نمایش اطلاعات مدل
    info = classifier.get_model_info()
    print(f"\n📊 اطلاعات مدل:")
    print(f"   • آموزش دیده: {info['is_trained']}")
    print(f"   • تعداد کلمات: {info['vocab_size']}")
    
    # تست پیش‌بینی
    test_texts = [
        "خرید از دیجیکالا ۲,۵۰۰,۰۰۰ تومان",
        "پرداخت حقوق پرسنل ماه جاری",
        "فروش کالا به مشتری شماره ۱۲۳",
        "پرداخت قبض برق دوره ۴",
        "واریز به حساب بانک تجارت",
        "برداشت از صندوق برای خرید ملزومات",
        "پرداخت اجاره دفتر ماهانه",
        "سرویس و تعمیر کولر گازی",
    ]
    
    print("\n📊 نتایج پیش‌بینی:")
    print("-"*60)
    
    for text in test_texts:
        result = classifier.predict(text)
        print(f"\n📝 شرح: {text[:40]}...")
        print(f"   ✅ حساب: {result['account_name']} ({result['account_code']})")
        print(f"   📊 اطمینان: {result['confidence']*100:.1f}%")
        print(f"   🔧 روش: {result['method']}")
        
        if "suggestions" in result:
            print(f"   💡 پیشنهادات دیگر:")
            for sug in result["suggestions"][:2]:
                print(f"      - {sug['name']}: {sug['confidence']*100:.1f}%")
