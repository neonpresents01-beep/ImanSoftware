"""
پیش‌بینی جریان نقدی با LSTM - ImanAI
"""

import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta

from imanai import ImanAI, Sequential, LightLSTM, Dense


class IntelligentCashFlowPredictor:
    """پیش‌بینی هوشمند جریان نقدی با LSTM"""
    
    def __init__(self, sequence_length: int = 6):
        self.sequence_length = sequence_length
        self.model = None
        self._build_model()
    
    def _build_model(self):
        """ساخت مدل LSTM"""
        self.ai = ImanAI()
        self.model = self.ai.create_model("CashFlowLSTM")
        
        # LSTM برای سری زمانی
        self.model.add(LightLSTM(input_dim=1, hidden_dim=32, return_sequences=True))
        self.model.add(LightLSTM(input_dim=32, hidden_dim=16, return_sequences=False))
        self.model.add(Dense(16, 8, 'relu'))
        self.model.add(Dense(8, 1, 'linear'))
        
        self.model.compile(lr=0.001)
        print(f"✅ مدل LSTM برای پیش‌بینی جریان نقدی ساخته شد")
    
    def prepare_sequences(self, data: List[float]) -> tuple:
        """آماده‌سازی داده‌ها برای LSTM"""
        X, y = [], []
        
        for i in range(len(data) - self.sequence_length):
            seq = data[i:i + self.sequence_length]
            target = data[i + self.sequence_length]
            X.append(seq)
            y.append(target)
        
        if not X:
            return None, None
        
        X = np.array(X, dtype=np.float32).reshape(-1, self.sequence_length, 1)
        y = np.array(y, dtype=np.float32).reshape(-1, 1)
        
        return X, y
    
    def train(self, historical_data: List[float], epochs: int = 100):
        """آموزش مدل با داده‌های تاریخی"""
        X, y = self.prepare_sequences(historical_data)
        
        if X is None:
            print("❌ داده کافی برای آموزش نیست")
            return
        
        print(f"🚀 آموزش LSTM با {len(X)} نمونه...")
        history = self.model.fit(X, y, epochs=epochs, batch_size=8, verbose=1)
        
        return history
    
    def predict_next(self, recent_data: List[float], steps: int = 3) -> List[Dict]:
        """پیش‌بینی قدم‌های بعدی"""
        if len(recent_data) < self.sequence_length:
            # پیش‌بینی ساده با میانگین متحرک
            return self._simple_predict(recent_data, steps)
        
        predictions = []
        current_seq = recent_data[-self.sequence_length:].copy()
        
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        current_month = datetime.now().month - 1
        
        for i in range(steps):
            X = np.array(current_seq, dtype=np.float32).reshape(1, self.sequence_length, 1)
            
            try:
                pred = self.model.predict(X)[0][0]
            except:
                # Fallback به میانگین متحرک
                pred = np.mean(current_seq[-3:])
            
            predictions.append({
                "month": month_names[(current_month + i + 1) % 12],
                "predicted_balance": round(float(pred), -3),
                "confidence": max(0.5, 0.9 - (i * 0.1))
            })
            
            # بروزرسانی sequence
            current_seq = current_seq[1:] + [pred]
        
        return predictions
    
    def _simple_predict(self, data: List[float], steps: int) -> List[Dict]:
        """پیش‌بینی ساده با میانگین متحرک"""
        if not data:
            return []
        
        avg_change = (data[-1] - data[0]) / max(len(data) - 1, 1) if len(data) > 1 else 0
        
        predictions = []
        last = data[-1]
        month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        current_month = datetime.now().month - 1
        
        for i in range(steps):
            pred = last + (avg_change * (i + 1))
            predictions.append({
                "month": month_names[(current_month + i + 1) % 12],
                "predicted_balance": round(pred, -3),
                "confidence": 0.6
            })
        
        return predictions
