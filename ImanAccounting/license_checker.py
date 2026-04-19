import hashlib
import base64
import json
import os
import platform
import subprocess
import uuid
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

# باید دقیقاً مشابه کلید توی license_generator باشه
MASTER_KEY = b"YOUR_ULTRA_SECRET_KEY_2024_CHANGE_THIS!#$%"
SALT = b"AccountingSalt2024"

class LicenseChecker:
    def __init__(self):
        self.license_file = "license.key"
        self.fernet = self._get_fernet()
    
    def _get_fernet(self):
        """تولید کلید رمزنگاری"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=SALT,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(MASTER_KEY))
        return Fernet(key)
    
    def get_hwid(self):
        """دریافت HWID سیستم کاربر"""
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output("wmic csproduct get uuid", shell=True).decode()
                hwid = output.split('\n')[1].strip()
                if not hwid or "00000000" in hwid:
                    output = subprocess.check_output("wmic diskdrive get serialnumber", shell=True).decode()
                    hwid = output.split('\n')[1].strip()
            elif platform.system() == "Darwin":
                output = subprocess.check_output("ioreg -l | grep IOPlatformSerialNumber", shell=True).decode()
                hwid = output.split('"')[-2]
            else:
                hwid = subprocess.check_output("cat /etc/machine-id", shell=True).decode().strip()
            
            return hashlib.sha256(hwid.encode()).hexdigest()[:16]
        except:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)][::-1])
            return hashlib.sha256(mac.encode()).hexdigest()[:16]
    
    def check_license(self):
        """بررسی اعتبار لایسنس"""
        if not os.path.exists(self.license_file):
            return {
                "valid": False,
                "hwid": self.get_hwid(),
                "message": "فایل license.key یافت نشد!"
            }
        
        try:
            with open(self.license_file, 'r') as f:
                license_key = f.read().strip().replace("-", "")
            
            # رمزگشایی
            encrypted = base64.b64decode(license_key)
            decrypted = self.fernet.decrypt(encrypted)
            payload = json.loads(decrypted.decode())
            
            # بررسی HWID
            current_hwid = self.get_hwid()
            if payload["hwid"] != current_hwid:
                return {
                    "valid": False,
                    "hwid": current_hwid,
                    "message": "لایسنس برای این سیستم معتبر نیست!"
                }
            
            # بررسی تاریخ انقضا
            expire_date = datetime.strptime(payload["expire"], "%Y-%m-%d")
            if datetime.now() > expire_date:
                days_passed = (datetime.now() - expire_date).days
                return {
                    "valid": False,
                    "hwid": current_hwid,
                    "message": f"لایسنس {days_passed} روز منقضی شده است!"
                }
            
            # محاسبه روزهای باقیمانده
            days_left = (expire_date - datetime.now()).days
            
            return {
                "valid": True,
                "customer": payload.get("customer", "Unknown"),
                "expire_date": payload["expire"],
                "days_left": days_left,
                "modules": payload["modules"],
                "license_id": payload.get("license_id", "N/A"),
                "message": "لایسنس معتبر است"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "hwid": self.get_hwid(),
                "message": f"خطا در اعتبارسنجی: {str(e)}"
            }
