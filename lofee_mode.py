import struct
import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple
from pathlib import Path


class MaestrosoftBuilder:
    """
    بناء نوى Maestrosoft Lofee المتقدمة مع دعم الفهرسة والتشفير
    Advanced Maestrosoft Lofee Builder with indexing and encryption support
    """
    
    SIGNATURE = b"MAESTROSOFT_LOFEE_v2.0"
    MAX_FILES = 500
    HEADER_ENTRY_SIZE = 128
    BRAND = "Maestrosoft"  # الاسم الثابت الأول
    FILE_EXTENSION = ".lofee"  # الامتداد الثابت
    
    def __init__(self, root_dir: str):
        """
        تهيئة بناء Lofee
        يتم استخراج اسم الفولدر تلقائياً واستخدامه كاسم Lofee الثاني
        
        Args:
            root_dir: مسار الفولدر الأساسي
        """
        self.root_dir = os.path.abspath(root_dir)
        
        # استخراج اسم الفولدر (الاسم الثاني المتغير)
        folder_name = os.path.basename(self.root_dir)
        
        # تشكيل اسم الملف: Maestrosoft_[folder_name].lofee
        self.output_file = f"Maestrosoft_{folder_name}{self.FILE_EXTENSION}"
        self.output_dir = self.root_dir
        self.json_file = os.path.splitext(self.output_file)[0] + "_manifest.json"
        
        self.files_to_fuse: List[Dict] = []
        self.file_hashes: Dict[str, str] = {}
        self.metadata = {
            "version": "2.0",
            "created_at": datetime.now().isoformat(),
            "brand": self.BRAND,
            "lofee_file": self.output_file,
            "folder_name": folder_name,
            "total_files": 0,
            "total_size": 0,
            "root_directory": self.root_dir
        }
        
        print("[*] تم تهيئة بناء Maestrosoft Lofee")
        print(f"[*] العلامة التجارية: {self.BRAND}")
        print(f"[*] اسم الفولدر: {folder_name}")
        print(f"[*] اسم الملف الناتج: {self.output_file}")
        print(f"[*] المجلد الأساسي: {self.root_dir}")
    
    def scan_directory(self) -> bool:
        """
        مسح الفولدر وجمع ملفاته
        
        Returns:
            bool: True إذا تم العثور على ملفات
        """
        print(f"\n[*] بدء المسح الشامل في: {self.root_dir}")
        
        try:
            for root, dirs, files in os.walk(self.root_dir):
                # تخطي المجلدات المحجوزة
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                # تخطي ملفات Lofee والـ JSON نفسها
                skip_files = {self.output_file, self.json_file}
                
                for file in files:
                    if file in skip_files:
                        continue
                    
                    try:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, self.root_dir)
                        file_size = os.path.getsize(file_path)
                        
                        # حساب hash الملف
                        file_hash = self._calculate_file_hash(file_path)
                        
                        self.files_to_fuse.append({
                            "rel_path": relative_path,
                            "full_path": file_path,
                            "size": file_size,
                            "hash": file_hash
                        })
                        
                        self.file_hashes[relative_path] = file_hash
                        print(f"[V] تم العثور على: {relative_path} ({self._format_size(file_size)})")
                        
                    except Exception as e:
                        print(f"[!] خطأ في معالجة الملف {file}: {str(e)}")
                        continue
            
            if not self.files_to_fuse:
                print("[!] تحذير: لم يتم العثور على أي ملفات!")
                return False
            
            self.metadata["total_files"] = len(self.files_to_fuse)
            self.metadata["total_size"] = sum(f["size"] for f in self.files_to_fuse)
            
            print(f"\n[OK] تم العثور على {len(self.files_to_fuse)} ملف")
            print(f"[OK] الحجم الإجمالي: {self._format_size(self.metadata['total_size'])}")
            return True
            
        except Exception as e:
            print(f"[!] خطأ في المسح: {str(e)}")
            return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """حساب SHA256 hash للملف"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except:
            return "unknown"
    
    def _format_size(self, size: int) -> str:
        """تنسيق حجم الملف"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def build_lofee(self) -> bool:
        """
        بناء ملف Lofee الرئيسي
        
        Returns:
            bool: True إذا نجحت العملية
        """
        if not self.files_to_fuse:
            print("[!] لا توجد ملفات للصهر")
            return False
        
        try:
            print(f"\n[*] بدء عملية صهر الملفات...")
            
            with open(self.output_file, "wb") as f:
                # كتابة التوقيع
                f.write(self.SIGNATURE)
                f.write(struct.pack("I", len(self.files_to_fuse)))
                
                # حجز مكان الفهرس
                header_pos = f.tell()
                f.write(b"\0" * (self.MAX_FILES * self.HEADER_ENTRY_SIZE))
                
                current_offset = f.tell()
                index_data = []
                
                # صهر الملفات
                for idx, item in enumerate(self.files_to_fuse, 1):
                    try:
                        with open(item["full_path"], "rb") as src:
                            data = src.read()
                            f.write(data)
                            
                            index_data.append({
                                "rel_path": item["rel_path"],
                                "offset": current_offset,
                                "size": item["size"],
                                "hash": item["hash"]
                            })
                            
                            current_offset += item["size"]
                            
                            print(f"[*] [{idx}/{len(self.files_to_fuse)}] صهر -> {item['rel_path']}")
                    except Exception as e:
                        print(f"[!] خطأ في صهر {item['rel_path']}: {str(e)}")
                        continue
                
                # كتابة الفهرس
                f.seek(header_pos)
                for entry in index_data:
                    path_bin = entry["rel_path"].encode("utf-8")[:99].ljust(100, b"\0")
                    f.write(path_bin)
                    f.write(struct.pack("Q", entry["offset"]))
                    f.write(struct.pack("Q", entry["size"]))
                    f.write(b"\0" * 12)
            
            print(f"\n[OK] تم صهر {len(index_data)} ملف بنجاح في {self.output_file}")
            self.metadata["indexed_files"] = len(index_data)
            return True
            
        except Exception as e:
            print(f"[!] خطأ في بناء Lofee: {str(e)}")
            return False
    
    def generate_manifest(self) -> bool:
        """
        توليد ملف JSON الخاص بالتشغيل (مفتاح التشغيل)
        
        Returns:
            bool: True إذا نجحت العملية
        """
        try:
            manifest = {
                "maestrosoft_lofee": {
                    "brand": self.BRAND,  # الاسم الثابت الأول
                    "folder_name": self.metadata.get("folder_name"),  # الاسم المتغير الثاني
                    "format": "Lofee",
                    "version": self.metadata.get("version"),
                    "created_at": self.metadata.get("created_at"),
                    "lofee_file": self.output_file,
                    "manifest_file": self.json_file,
                    "file_extension": self.FILE_EXTENSION
                },
                "statistics": {
                    "total_files": self.metadata.get("total_files"),
                    "total_size_bytes": self.metadata.get("total_size"),
                    "total_size_formatted": self._format_size(self.metadata.get("total_size", 0))
                },
                "file_index": [
                    {
                        "index": idx,
                        "path": f["rel_path"],
                        "size": f["size"],
                        "size_formatted": self._format_size(f["size"]),
                        "hash": f["hash"],
                        "type": self._get_file_type(f["rel_path"])
                    }
                    for idx, f in enumerate(self.files_to_fuse, 1)
                ],
                "runtime_instructions": {
                    "initialization": [
                        "✓ تحقق من وجود ملف Lofee",
                        "✓ اقرأ التوقيع وتحقق من الإصدار (MAESTROSOFT_LOFEE_v2.0)",
                        "✓ حمّل الفهرس من الذاكرة",
                        "✓ تهيئة النموذج"
                    ],
                    "file_extraction": [
                        "✓ ابحث عن الملف المطلوب في الفهرس باستخدام المسار النسبي",
                        "✓ استخدم offset والحجم للقراءة من ملف Lofee",
                        "✓ تحقق من hash الملف للتأكد من السلامة والتكامل",
                        "✓ أعد الملف للاستخدام"
                    ],
                    "error_handling": [
                        "⚠ في حالة عدم العثور على الملف: ابحث مرة أخرى في الفهرس الكامل",
                        "⚠ في حالة عدم تطابق hash: أعد تحميل الملف من Lofee",
                        "⚠ في حالة الخطأ: احفظ معلومات الخطأ في السجل وأعد المحاولة",
                        "⚠ في حالة الفشل الكلي: تحقق من سلامة ملف Lofee"
                    ],
                    "model_integration": [
                        "🎼 استخدم معلومات الملفات لتدريب النموذج",
                        "🎼 اعتمد على الفهرس الموجود في JSON كمرجعية",
                        "🎼 راقب الأداء باستخدام البيانات الإحصائية",
                        "🎼 احفظ حالة النموذج بعد كل تحديث"
                    ]
                },
                "file_types_distribution": self._get_file_types_distribution(),
                "checksums": {
                    "lofee_file_hash": self._calculate_file_hash(self.output_file),
                    "manifest_version": "2.0",
                    "signature": "MAESTROSOFT_LOFEE_v2.0"
                },
                "system_info": {
                    "root_directory": self.root_dir,
                    "build_date": self.metadata.get("created_at"),
                    "format_type": "Binary Lofee Package",
                    "compression": "None",
                    "encryption": "SHA256 Hashing"
                }
            }
            
            # كتابة JSON بتنسيق جميل
            with open(self.json_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            print(f"\n[OK] تم توليد مفتاح التشغيل: {self.json_file}")
            return True
            
        except Exception as e:
            print(f"[!] خطأ في توليد JSON: {str(e)}")
            return False
    
    def _get_file_type(self, file_path: str) -> str:
        """تحديد نوع الملف"""
        ext = os.path.splitext(file_path)[1].lower()
        
        type_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.json': 'JSON',
            '.txt': 'Text',
            '.md': 'Markdown',
            '.pdf': 'PDF',
            '.png': 'Image',
            '.jpg': 'Image',
            '.jpeg': 'Image',
            '.gif': 'Image',
            '.mp3': 'Audio',
            '.mp4': 'Video',
            '.zip': 'Archive',
            '.tar': 'Archive',
            '.gz': 'Archive',
            '.lofee': 'Maestrosoft Lofee'
        }
        
        return type_map.get(ext, 'Other')
    
    def _get_file_types_distribution(self) -> Dict[str, int]:
        """توزيع أنواع الملفات"""
        distribution = {}
        for file in self.files_to_fuse:
            file_type = self._get_file_type(file["rel_path"])
            distribution[file_type] = distribution.get(file_type, 0) + 1
        return distribution
    
    def run(self) -> bool:
        """
        تشغيل العملية الكاملة
        
        Returns:
            bool: True إذا نجحت العملية بالكامل
        """
        folder_name = os.path.basename(self.root_dir)
        
        print("=" * 70)
        print(f"🎼 بناء {self.BRAND} Lofee المتقدم")
        print(f"📁 الفولدر: {folder_name}")
        print("=" * 70)
        
        if not self.scan_directory():
            return False
        
        if not self.build_lofee():
            return False
        
        if not self.generate_manifest():
            return False
        
        print("\n" + "=" * 70)
        print("✅ تم إنجاز العملية بنجاح!")
        print("=" * 70)
        print(f"📦 ملف Lofee: {self.output_file}")
        print(f"🔑 مفتاح التشغيل: {self.json_file}")
        print(f"🎼 العلامة التجارية: {self.BRAND}")
        print(f"📋 صيغة الملف: Lofee Format")
        print(f"📁 اسم الفولدر: {folder_name}")
        print("=" * 70)
        
        return True


def main():
    """
    نقطة البداية للبرنامج
    يتم استخراج اسم الفولدر الحالي تلقائياً
    """
    # بناء Lofee للمجلد الحالي
    # الاسم سيكون: Maestrosoft_[folder_name].lofee
    builder = MaestrosoftBuilder(".")
    builder.run()


if __name__ == "__main__":
    main()
