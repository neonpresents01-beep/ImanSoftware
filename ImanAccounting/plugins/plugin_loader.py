"""
سیستم لود پلاگین با امضای دیجیتال
"""

import os
import json
import hashlib
import importlib.util
import sys
from typing import Dict, List, Any, Optional
import base64
from datetime import datetime
from pathlib import Path

# تلاش برای import cryptography
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ کتابخانه cryptography نصب نیست. اعتبارسنجی امضا غیرفعال است.")
    print("   برای نصب: pip install cryptography")


class PluginLoader:
    """
    سیستم لود پلاگین با اعتبارسنجی امضای دیجیتال
    """
    
    # کلید عمومی توسعه‌دهنده (برای اعتبارسنجی پلاگین‌ها)
    # این کلید باید با کلید عمومی تولید شده توسط plugin_signer جایگزین بشه
    DEVELOPER_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1LfVLPHCYZM6Y2X
nO2PLbPxGxMJNxLPjLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLx
LxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLxLx
... (کلید عمومی واقعی رو اینجا قرار بده)
-----END PUBLIC KEY-----"""
    
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.loaded_plugins: Dict[str, Any] = {}
        self.plugin_info: Dict[str, Dict] = {}
        self.plugin_widgets: Dict[str, Any] = {}
        self.app_version = "1.0.0"
        
        # ساخت پوشه‌های مورد نیاز
        self._create_plugin_directories()
    
    def _create_plugin_directories(self):
        """ساخت پوشه‌های پلاگین"""
        (self.plugin_dir / "official_plugins").mkdir(parents=True, exist_ok=True)
        (self.plugin_dir / "third_party").mkdir(parents=True, exist_ok=True)
    
    def load_plugin(self, plugin_path: str) -> bool:
        """
        بارگذاری یک پلاگین
        
        Args:
            plugin_path: مسیر فایل پلاگین (.plugin)
            
        Returns:
            bool: موفقیت‌آمیز بودن بارگذاری
        """
        plugin_path = Path(plugin_path)
        
        try:
            # ۱. خواندن فایل پلاگین
            with open(plugin_path, 'rb') as f:
                plugin_data = f.read()
            
            # ۲. استخراج بخش‌های پلاگین
            parts = self._parse_plugin(plugin_data)
            if not parts:
                print(f"❌ خطا در تجزیه پلاگین {plugin_path.name}")
                return False
            
            manifest = parts['manifest']
            plugin_id = manifest.get('id', plugin_path.stem)
            
            # ۳. بررسی وجود پلاگین تکراری
            if plugin_id in self.loaded_plugins:
                print(f"⚠️ پلاگین {plugin_id} قبلاً بارگذاری شده است")
                return False
            
            # ۴. اعتبارسنجی امضای دیجیتال (اگر cryptography نصب باشه)
            if CRYPTO_AVAILABLE and not self._verify_signature(parts):
                print(f"❌ امضای پلاگین {plugin_id} نامعتبر است!")
                return False
            elif not CRYPTO_AVAILABLE:
                print(f"⚠️ اعتبارسنجی امضا رد شد (cryptography نصب نیست)")
            
            # ۵. بررسی نسخه و وابستگی‌ها
            if not self._check_compatibility(manifest):
                print(f"❌ پلاگین {plugin_id} با نسخه فعلی سازگار نیست!")
                return False
            
            # ۶. بررسی مجوزها
            if not self._check_permissions(manifest):
                print(f"❌ پلاگین {plugin_id} مجوزهای لازم را ندارد!")
                return False
            
            # ۷. بارگذاری کد پلاگین
            plugin_module = self._load_module(plugin_id, parts['code'])
            if not plugin_module:
                return False
            
            # ۸. مقداردهی اولیه پلاگین
            if hasattr(plugin_module, 'initialize'):
                try:
                    plugin_module.initialize()
                except Exception as e:
                    print(f"❌ خطا در initialize پلاگین {plugin_id}: {e}")
                    return False
            
            # ۹. ذخیره اطلاعات پلاگین
            self.loaded_plugins[plugin_id] = plugin_module
            self.plugin_info[plugin_id] = {
                'id': plugin_id,
                'name': manifest.get('name', plugin_id),
                'version': manifest.get('version', '1.0.0'),
                'description': manifest.get('description', ''),
                'author': manifest.get('author', 'Unknown'),
                'path': str(plugin_path),
                'manifest': manifest
            }
            
            print(f"✅ پلاگین {manifest.get('name', plugin_id)} v{manifest.get('version', '1.0.0')} با موفقیت بارگذاری شد")
            return True
            
        except Exception as e:
            print(f"❌ خطا در بارگذاری پلاگین {plugin_path}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_plugin(self, plugin_data: bytes) -> Optional[Dict]:
        """تجزیه فایل پلاگین به بخش‌های مختلف"""
        try:
            # فرمت: [MANIFEST_LEN:4][MANIFEST][SIGNATURE_LEN:4][SIGNATURE][CODE]
            
            manifest_len = int.from_bytes(plugin_data[:4], 'big')
            manifest_bytes = plugin_data[4:4+manifest_len]
            manifest = json.loads(manifest_bytes.decode('utf-8'))
            
            offset = 4 + manifest_len
            sig_len = int.from_bytes(plugin_data[offset:offset+4], 'big')
            offset += 4
            signature = plugin_data[offset:offset+sig_len]
            
            offset += sig_len
            code = plugin_data[offset:]
            
            return {
                'manifest': manifest,
                'signature': signature,
                'code': code
            }
        except Exception as e:
            print(f"خطا در تجزیه پلاگین: {e}")
            return None
    
    def _verify_signature(self, parts: Dict) -> bool:
        """اعتبارسنجی امضای دیجیتال"""
        if not CRYPTO_AVAILABLE:
            return True  # رد کردن اعتبارسنجی اگر cryptography نصب نیست
        
        try:
            # بارگذاری کلید عمومی
            public_key = serialization.load_pem_public_key(
                self.DEVELOPER_PUBLIC_KEY.encode(),
                backend=default_backend()
            )
            
            # داده‌ای که امضا شده
            data_to_verify = json.dumps(parts['manifest']).encode('utf-8') + parts['code']
            
            # اعتبارسنجی امضا
            public_key.verify(
                parts['signature'],
                data_to_verify,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            print(f"خطا در اعتبارسنجی امضا: {e}")
            return False
    
    def _check_compatibility(self, manifest: Dict) -> bool:
        """بررسی سازگاری پلاگین"""
        # بررسی نسخه حداقل برنامه
        if 'min_app_version' in manifest:
            if not self._version_compare(self.app_version, manifest['min_app_version']) >= 0:
                print(f"  ↳ نیاز به نسخه {manifest['min_app_version']} (نسخه فعلی: {self.app_version})")
                return False
        
        # بررسی وابستگی‌ها
        if 'dependencies' in manifest:
            for dep_id, dep_version in manifest['dependencies'].items():
                if dep_id not in self.loaded_plugins:
                    print(f"  ↳ وابستگی {dep_id} یافت نشد!")
                    return False
                
                installed_version = self.plugin_info[dep_id]['version']
                if self._version_compare(installed_version, dep_version) < 0:
                    print(f"  ↳ نسخه {dep_id} باید حداقل {dep_version} باشد (فعلی: {installed_version})")
                    return False
        
        return True
    
    def _check_permissions(self, manifest: Dict) -> bool:
        """بررسی مجوزهای پلاگین"""
        # در اینجا می‌تونیم بررسی کنیم که پلاگین مجوزهای درخواستی رو داره یا نه
        # برای MVP همه مجوزها رو قبول می‌کنیم
        return True
    
    def _version_compare(self, v1: str, v2: str) -> int:
        """مقایسه دو نسخه - بازگشت: ۱ اگر v1 بزرگتر، -۱ اگر v2 بزرگتر، ۰ اگر برابر"""
        try:
            v1_parts = [int(x) for x in v1.split('.')]
            v2_parts = [int(x) for x in v2.split('.')]
            
            for i in range(max(len(v1_parts), len(v2_parts))):
                n1 = v1_parts[i] if i < len(v1_parts) else 0
                n2 = v2_parts[i] if i < len(v2_parts) else 0
                if n1 > n2:
                    return 1
                elif n1 < n2:
                    return -1
            return 0
        except:
            return 0
    
    def _load_module(self, plugin_id: str, code: bytes):
        """بارگذاری ماژول پلاگین"""
        try:
            # ایجاد ماژول
            spec = importlib.util.spec_from_loader(
                plugin_id,
                loader=None,
                origin=f"plugin://{plugin_id}"
            )
            module = importlib.util.module_from_spec(spec)
            
            # اضافه کردن به sys.modules
            sys.modules[plugin_id] = module
            
            # اجرای کد پلاگین
            exec(code.decode('utf-8'), module.__dict__)
            
            return module
        except Exception as e:
            print(f"خطا در بارگذاری ماژول {plugin_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def load_all_plugins(self):
        """بارگذاری تمام پلاگین‌های موجود"""
        # پلاگین‌های رسمی
        official_dir = self.plugin_dir / "official_plugins"
        if official_dir.exists():
            for file in official_dir.glob("*.plugin"):
                print(f"🔍 در حال بارگذاری: {file.name}")
                self.load_plugin(str(file))
        
        # پلاگین‌های شخص ثالث
        third_party_dir = self.plugin_dir / "third_party"
        if third_party_dir.exists():
            for file in third_party_dir.glob("*.plugin"):
                print(f"🔍 در حال بارگذاری: {file.name}")
                self.load_plugin(str(file))
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """حذف یک پلاگین"""
        if plugin_id in self.loaded_plugins:
            module = self.loaded_plugins[plugin_id]
            
            # فراخوانی تابع cleanup اگر وجود داشته باشد
            if hasattr(module, 'cleanup'):
                try:
                    module.cleanup()
                except:
                    pass
            
            # حذف از حافظه
            del self.loaded_plugins[plugin_id]
            del self.plugin_info[plugin_id]
            
            if plugin_id in sys.modules:
                del sys.modules[plugin_id]
            
            return True
        return False
    
    def get_plugin_menus(self) -> List[Dict]:
        """دریافت منوهای تمام پلاگین‌ها"""
        menus = []
        for plugin_id, module in self.loaded_plugins.items():
            if hasattr(module, 'get_menus'):
                try:
                    plugin_menus = module.get_menus()
                    for menu in plugin_menus:
                        menu['plugin_id'] = plugin_id
                        menus.append(menu)
                except Exception as e:
                    print(f"خطا در دریافت منوهای {plugin_id}: {e}")
        return menus
    
    def get_plugin_tabs(self) -> List[Dict]:
        """دریافت تب‌های تمام پلاگین‌ها"""
        tabs = []
        for plugin_id, module in self.loaded_plugins.items():
            if hasattr(module, 'get_tabs'):
                try:
                    plugin_tabs = module.get_tabs()
                    for tab in plugin_tabs:
                        tab['plugin_id'] = plugin_id
                        tabs.append(tab)
                except Exception as e:
                    print(f"خطا در دریافت تب‌های {plugin_id}: {e}")
        return tabs
    
    def execute_plugin_action(self, plugin_id: str, action_id: str, **kwargs) -> Any:
        """اجرای یک action از پلاگین"""
        if plugin_id in self.loaded_plugins:
            module = self.loaded_plugins[plugin_id]
            if hasattr(module, 'execute_action'):
                try:
                    return module.execute_action(action_id, **kwargs)
                except Exception as e:
                    print(f"خطا در اجرای اکشن {action_id} از {plugin_id}: {e}")
        return None
    
    def get_plugin_widget(self, plugin_id: str, widget_id: str) -> Optional[Any]:
        """دریافت ویجت از پلاگین"""
        if plugin_id in self.loaded_plugins:
            module = self.loaded_plugins[plugin_id]
            if hasattr(module, 'get_widget'):
                try:
                    return module.get_widget(widget_id)
                except Exception as e:
                    print(f"خطا در دریافت ویجت {widget_id} از {plugin_id}: {e}")
        return None
    
    def get_all_plugins_info(self) -> List[Dict]:
        """دریافت اطلاعات تمام پلاگین‌های بارگذاری شده"""
        return list(self.plugin_info.values())


class PluginManager:
    """
    مدیریت پلاگین‌ها در سطح برنامه (Singleton)
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.loader = PluginLoader()
            cls._instance.loader.load_all_plugins()
        return cls._instance
    
    def get_all_plugins(self) -> List[Dict]:
        """دریافت لیست تمام پلاگین‌ها"""
        return self.loader.get_all_plugins_info()
    
    def get_plugin_menus(self) -> List[Dict]:
        """دریافت منوهای پلاگین‌ها"""
        return self.loader.get_plugin_menus()
    
    def get_plugin_tabs(self) -> List[Dict]:
        """دریافت تب‌های پلاگین‌ها"""
        return self.loader.get_plugin_tabs()
    
    def execute_action(self, plugin_id: str, action_id: str, **kwargs) -> Any:
        """اجرای اکشن پلاگین"""
        return self.loader.execute_plugin_action(plugin_id, action_id, **kwargs)
    
    def get_plugin_widget(self, plugin_id: str, widget_id: str) -> Optional[Any]:
        """دریافت ویجت پلاگین"""
        return self.loader.get_plugin_widget(plugin_id, widget_id)
    
    def reload_plugins(self):
        """بارگذاری مجدد تمام پلاگین‌ها"""
        # حذف پلاگین‌های فعلی
        for plugin_id in list(self.loader.loaded_plugins.keys()):
            self.loader.unload_plugin(plugin_id)
        
        # بارگذاری مجدد
        self.loader.load_all_plugins()
    
    def install_plugin(self, plugin_path: str) -> bool:
        """نصب پلاگین جدید"""
        import shutil
        
        plugin_path = Path(plugin_path)
        if not plugin_path.exists():
            return False
        
        # کپی به پوشه third_party
        dest = self.loader.plugin_dir / "third_party" / plugin_path.name
        shutil.copy2(plugin_path, dest)
        
        # بارگذاری پلاگین
        return self.loader.load_plugin(str(dest))
    
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """حذف پلاگین"""
        if plugin_id not in self.loader.plugin_info:
            return False
        
        plugin_path = self.loader.plugin_info[plugin_id]['path']
        
        # حذف از حافظه
        self.loader.unload_plugin(plugin_id)
        
        # حذف فایل
        try:
            os.remove(plugin_path)
            return True
        except:
            return False
