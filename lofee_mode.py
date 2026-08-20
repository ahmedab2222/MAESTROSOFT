import struct
import os
import json
import hashlib
import re
import ast
from datetime import datetime
from typing import List, Dict, Tuple, Any
from pathlib import Path


class CommandExtractor:
    """استخراج الدوال والأوامر من الملفات Python"""
    
    @staticmethod
    def extract_from_python(file_path: str) -> Dict[str, Any]:
        """استخراج الدوال والأوامر من ملف Python"""
        commands = {
            "functions": [],
            "classes": [],
            "imports": [],
            "code_snippets": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # استخراج الـ imports
            import_pattern = r'^(?:from\s+[\w.]+\s+)?import\s+[\w\s,.*]+$'
            commands["imports"] = re.findall(import_pattern, content, re.MULTILINE)
            
            # محاولة تحليل AST
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    # استخراج الدوال
                    if isinstance(node, ast.FunctionDef):
                        func_info = {
                            "name": node.name,
                            "args": [arg.arg for arg in node.args.args],
                            "docstring": ast.get_docstring(node) or "No documentation",
                            "line": node.lineno
                        }
                        commands["functions"].append(func_info)
                    
                    # استخراج الفئات
                    elif isinstance(node, ast.ClassDef):
                        class_info = {
                            "name": node.name,
                            "methods": [],
                            "docstring": ast.get_docstring(node) or "No documentation",
                            "line": node.lineno
                        }
                        
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                class_info["methods"].append(item.name)
                        
                        commands["classes"].append(class_info)
            
            except SyntaxError:
                pass
            
            return commands
        
        except Exception as e:
            return {"error": str(e), "functions": [], "classes": [], "imports": []}
    
    @staticmethod
    def extract_from_json(file_path: str) -> Dict[str, Any]:
        """استخراج البيانات من ملف JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {"data_structure": data}
        except:
            return {"error": "Failed to parse JSON"}
    
    @staticmethod
    def extract_from_markdown(file_path: str) -> Dict[str, Any]:
        """استخراج الأوامر من ملف Markdown"""
        commands = {
            "headings": [],
            "code_blocks": [],
            "commands": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # استخراج العناوين
            commands["headings"] = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
            
            # استخراج كتل الكود
            code_blocks = re.findall(r'```(?:python|bash|sh)?\n(.*?)```', content, re.DOTALL)
            commands["code_blocks"] = code_blocks
            
            # استخراج الأوامر (الأسطر التي تبدأ بـ - أو *)
            commands["commands"] = re.findall(r'^[\-\*]\s+(.+)$', content, re.MULTILINE)
            
            return commands
        
        except Exception as e:
            return {"error": str(e)}


class MaestrosoftBuilder:
    """
    بناء نوى Maestrosoft Lofee المتقدمة مع استخراج الأوامر والدوال
    Advanced Maestrosoft Lofee Builder with command extraction
    """
    
    SIGNATURE = b"MAESTROSOFT_LOFEE_v2.0"
    MAX_FILES = 500
    HEADER_ENTRY_SIZE = 128
    BRAND = "Maestrosoft"
    FILE_EXTENSION = ".lofee"
    MODEL_NAME = "BigLofee"
    
    def __init__(self, root_dir: str):
        """تهيئة بناء Lofee مع استخراج الأوامر"""
        self.root_dir = os.path.abspath(root_dir)
        folder_name = os.path.basename(self.root_dir)
        
        self.output_file = f"Maestrosoft_{folder_name}{self.FILE_EXTENSION}"
        self.output_dir = self.root_dir
        self.json_file = os.path.splitext(self.output_file)[0] + "_manifest.json"
        self.packages_file = os.path.splitext(self.output_file)[0] + "_packages.json"
        self.skills_file = os.path.splitext(self.output_file)[0] + "_skills.md"
        
        self.files_to_fuse: List[Dict] = []
        self.file_hashes: Dict[str, str] = {}
        self.extracted_commands: Dict[str, Any] = {}
        self.all_functions: List[Dict] = []
        self.all_classes: List[Dict] = []
        
        self.metadata = {
            "version": "2.0",
            "created_at": datetime.now().isoformat(),
            "brand": self.BRAND,
            "model_name": self.MODEL_NAME,
            "lofee_file": self.output_file,
            "folder_name": folder_name,
            "total_files": 0,
            "total_size": 0,
            "root_directory": self.root_dir
        }
        
        print("[*] تم تهيئة بناء Maestrosoft Lofee")
        print(f"[*] العلامة التجارية: {self.BRAND}")
        print(f"[*] النموذج: {self.MODEL_NAME}")
        print(f"[*] اسم الفولدر: {folder_name}")
        print(f"[*] اسم الملف الناتج: {self.output_file}")
    
    def scan_directory(self) -> bool:
        """مسح الفولدر وجمع ملفاته مع استخراج الأوامر"""
        print(f"\n[*] بدء المسح الشامل في: {self.root_dir}")
        
        try:
            for root, dirs, files in os.walk(self.root_dir):
                # تخطي المجلدات المحجوزة
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                skip_files = {self.output_file, self.json_file, self.packages_file, self.skills_file}
                
                for file in files:
                    if file in skip_files:
                        continue
                    
                    try:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, self.root_dir)
                        file_size = os.path.getsize(file_path)
                        
                        file_hash = self._calculate_file_hash(file_path)
                        file_extension = os.path.splitext(file)[1].lower()
                        
                        # استخراج الأوامر حسب نوع الملف
                        extracted_commands = self._extract_commands(file_path, file_extension)
                        
                        self.files_to_fuse.append({
                            "rel_path": relative_path,
                            "full_path": file_path,
                            "size": file_size,
                            "hash": file_hash,
                            "extension": file_extension,
                            "commands": extracted_commands
                        })
                        
                        self.extracted_commands[relative_path] = extracted_commands
                        
                        # جمع جميع الدوال والفئات
                        if file_extension == '.py':
                            if "functions" in extracted_commands:
                                self.all_functions.extend(extracted_commands["functions"])
                            if "classes" in extracted_commands:
                                self.all_classes.extend(extracted_commands["classes"])
                        
                        self.file_hashes[relative_path] = file_hash
                        print(f"[V] تم العثور على: {relative_path} ({self._format_size(file_size)})")
                        
                        if extracted_commands and ("functions" in extracted_commands or "classes" in extracted_commands):
                            func_count = len(extracted_commands.get("functions", []))
                            class_count = len(extracted_commands.get("classes", []))
                            print(f"    └─ تم استخراج: {func_count} دوال، {class_count} فئات")
                        
                    except Exception as e:
                        print(f"[!] خطأ في معالجة الملف {file}: {str(e)}")
                        continue
            
            if not self.files_to_fuse:
                print("[!] تحذير: لم يتم العثور على أي ملفات!")
                return False
            
            self.metadata["total_files"] = len(self.files_to_fuse)
            self.metadata["total_size"] = sum(f["size"] for f in self.files_to_fuse)
            self.metadata["total_functions"] = len(self.all_functions)
            self.metadata["total_classes"] = len(self.all_classes)
            
            print(f"\n[OK] تم العثور على {len(self.files_to_fuse)} ملف")
            print(f"[OK] الحجم الإجمالي: {self._format_size(self.metadata['total_size'])}")
            print(f"[OK] إجمالي الدوال المستخرجة: {len(self.all_functions)}")
            print(f"[OK] إجمالي الفئات المستخرجة: {len(self.all_classes)}")
            return True
            
        except Exception as e:
            print(f"[!] خطأ في المسح: {str(e)}")
            return False
    
    def _extract_commands(self, file_path: str, extension: str) -> Dict[str, Any]:
        """استخراج الأوامر حسب نوع الملف"""
        if extension == '.py':
            return CommandExtractor.extract_from_python(file_path)
        elif extension == '.json':
            return CommandExtractor.extract_from_json(file_path)
        elif extension == '.md':
            return CommandExtractor.extract_from_markdown(file_path)
        else:
            return {}
    
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
        """بناء ملف Lofee الرئيسي"""
        if not self.files_to_fuse:
            print("[!] لا توجد ملفات للصهر")
            return False
        
        try:
            print(f"\n[*] بدء عملية صهر الملفات...")
            
            with open(self.output_file, "wb") as f:
                f.write(self.SIGNATURE)
                f.write(struct.pack("I", len(self.files_to_fuse)))
                
                header_pos = f.tell()
                f.write(b"\0" * (self.MAX_FILES * self.HEADER_ENTRY_SIZE))
                
                current_offset = f.tell()
                index_data = []
                
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
                
                f.seek(header_pos)
                for entry in index_data:
                    path_bin = entry["rel_path"].encode("utf-8")[:99].ljust(100, b"\0")
                    f.write(path_bin)
                    f.write(struct.pack("Q", entry["offset"]))
                    f.write(struct.pack("Q", entry["size"]))
                    f.write(b"\0" * 12)
            
            print(f"\n[OK] تم صهر {len(index_data)} ملف بنجاح في {self.output_file}")
            return True
            
        except Exception as e:
            print(f"[!] خطأ في بناء Lofee: {str(e)}")
            return False
    
    def generate_packages_json(self) -> bool:
        """توليد ملف Packages JSON مع جميع الأوامر والدوال"""
        try:
            print(f"\n[*] توليد ملف الـ Packages JSON...")
            
            packages = {
                "maestrosoft_packages": {
                    "brand": self.BRAND,
                    "model": self.MODEL_NAME,
                    "version": self.metadata.get("version"),
                    "created_at": self.metadata.get("created_at"),
                    "total_packages": len(self.all_functions) + len(self.all_classes)
                },
                "executable_functions": [
                    {
                        "id": idx,
                        "name": func.get("name", "unknown"),
                        "file": next((f["rel_path"] for f in self.files_to_fuse if func in self.extracted_commands.get(f["rel_path"], {}).get("functions", [])), "unknown"),
                        "arguments": func.get("args", []),
                        "docstring": func.get("docstring", "No documentation"),
                        "type": "function",
                        "executable": True,
                        "command": f"execute_function('{func.get('name', 'unknown')}')"
                    }
                    for idx, func in enumerate(self.all_functions, 1)
                ],
                "class_methods": [
                    {
                        "id": idx,
                        "class_name": cls.get("name", "unknown"),
                        "methods": cls.get("methods", []),
                        "docstring": cls.get("docstring", "No documentation"),
                        "type": "class",
                        "executable": True,
                        "command": f"execute_class('{cls.get('name', 'unknown')}')"
                    }
                    for idx, cls in enumerate(self.all_classes, 1)
                ],
                "file_commands": {}
            }
            
            # إضافة أوامر كل ملف
            for file_info in self.files_to_fuse:
                file_path = file_info["rel_path"]
                commands = self.extracted_commands.get(file_path, {})
                
                if commands:
                    packages["file_commands"][file_path] = {
                        "size": file_info["size"],
                        "hash": file_info["hash"],
                        "extension": file_info["extension"],
                        "commands": commands
                    }
            
            with open(self.packages_file, "w", encoding="utf-8") as f:
                json.dump(packages, f, ensure_ascii=False, indent=2)
            
            print(f"[OK] تم توليد ملف الـ Packages: {self.packages_file}")
            return True
            
        except Exception as e:
            print(f"[!] خطأ في توليد Packages JSON: {str(e)}")
            return False
    
    def generate_skills_markdown(self) -> bool:
        """توليد ملف Skills Markdown لنموذج BigLofee"""
        try:
            print(f"\n[*] توليد ملف Skills Markdown...")
            
            total_files = self.metadata.get('total_files')
            total_size = self._format_size(self.metadata.get('total_size', 0))
            total_funcs = len(self.all_functions)
            total_cls = len(self.all_classes)
            version = self.metadata.get('version')
            created = self.metadata.get('created_at')
            folder = self.metadata.get('folder_name')
            model = self.MODEL_NAME
            brand = self.BRAND
            pkgs_file = self.packages_file
            lofee_file = self.output_file
            
            markdown_content = "# " + model + " - Skills & Commands Guide\n\n"
            markdown_content += "**العلامة التجارية:** " + brand + "\n"
            markdown_content += "**الإصدار:** " + version + "\n"
            markdown_content += "**تاريخ الإنشاء:** " + created + "\n"
            markdown_content += "**المجلد:** " + folder + "\n\n"
            markdown_content += "---\n\n"
            markdown_content += "## " + "📊 الإحصائيات الشاملة" + "\n\n"
            markdown_content += "| الخاصية | القيمة |\n"
            markdown_content += "|--------|--------|\n"
            markdown_content += "| إجمالي الملفات | " + str(total_files) + " |\n"
            markdown_content += "| الحجم الإجمالي | " + total_size + " |\n"
            markdown_content += "| إجمالي الدوال | " + str(total_funcs) + " |\n"
            markdown_content += "| إجمالي الفئات | " + str(total_cls) + " |\n\n"
            markdown_content += "---\n\n"
            markdown_content += "## " + "🎯 الدوال المتاحة (Executable Functions)" + "\n\n"
            
            if self.all_functions:
                for idx, func in enumerate(self.all_functions, 1):
                    func_name = func.get('name', 'unknown')
                    file_path = next((f['rel_path'] for f in self.files_to_fuse if func in self.extracted_commands.get(f['rel_path'], {}).get('functions', [])), 'unknown')
                    args = ', '.join(func.get('args', [])) or 'بدون معاملات'
                    doc = func.get('docstring', 'لا توجد وثائق')
                    
                    markdown_content += "### " + str(idx) + ". `" + func_name + "`\n\n"
                    markdown_content += "**الملف:** `" + file_path + "`\n"
                    markdown_content += "**المعاملات:** " + args + "\n"
                    markdown_content += "**الوثائق:** " + doc + "\n\n"
                    markdown_content += "**أمر التشغيل:**\n"
                    markdown_content += "```python\n"
                    markdown_content += "execute_function('" + func_name + "')\n"
                    markdown_content += "```\n\n"
                    markdown_content += "---\n\n"
            else:
                markdown_content += "_لم يتم العثور على دوال مستخرجة._\n\n---\n\n"
            
            markdown_content += "## " + "🏗️ الفئات والطرق (Classes & Methods)" + "\n\n"
            
            if self.all_classes:
                for idx, cls in enumerate(self.all_classes, 1):
                    cls_name = cls.get('name', 'unknown')
                    file_path = next((f['rel_path'] for f in self.files_to_fuse if cls in self.extracted_commands.get(f['rel_path'], {}).get('classes', [])), 'unknown')
                    methods = ', '.join(cls.get('methods', [])) or 'بدون طرق'
                    doc = cls.get('docstring', 'لا توجد وثائق')
                    
                    markdown_content += "### " + str(idx) + ". الفئة: `" + cls_name + "`\n\n"
                    markdown_content += "**الملف:** `" + file_path + "`\n"
                    markdown_content += "**الطرق:** " + methods + "\n"
                    markdown_content += "**الوثائق:** " + doc + "\n\n"
                    markdown_content += "**أمر التشغيل:**\n"
                    markdown_content += "```python\n"
                    markdown_content += "execute_class('" + cls_name + "')\n"
                    markdown_content += "```\n\n"
                    markdown_content += "---\n\n"
            else:
                markdown_content += "_لم يتم العثور على فئات مستخرجة._\n\n---\n\n"
            
            markdown_content += "## " + "📁 الملفات المعالجة" + "\n\n"
            markdown_content += "| الملف | الحجم | النوع | الأوامر |\n"
            markdown_content += "|------|-------|--------|--------|\n"
            
            for file_info in self.files_to_fuse:
                file_path = file_info["rel_path"]
                commands = self.extracted_commands.get(file_path, {})
                cmd_count = len(commands.get("functions", [])) + len(commands.get("classes", []))
                markdown_content += "| `" + file_path + "` | " + self._format_size(file_info['size']) + " | " + file_info['extension'] + " | " + str(cmd_count) + " |\n"
            
            markdown_content += "\n---\n\n"
            markdown_content += "## " + "🚀 دليل التشغيل السريع" + "\n\n"
            markdown_content += "### 1️⃣ التهيئة\n"
            markdown_content += "```python\n"
            markdown_content += "from Maestrosoft_BigLofee import initialize_model\n"
            markdown_content += "initialize_model()\n"
            markdown_content += "```\n\n"
            markdown_content += "### 2️⃣ تنفيذ دالة\n"
            markdown_content += "```python\n"
            markdown_content += "result = execute_function('function_name')\n"
            markdown_content += "```\n\n"
            markdown_content += "### 3️⃣ تنفيذ فئة\n"
            markdown_content += "```python\n"
            markdown_content += "instance = execute_class('ClassName')\n"
            markdown_content += "```\n\n"
            markdown_content += "---\n\n"
            markdown_content += "## " + "📋 ملاحظات مهمة" + "\n\n"
            markdown_content += "- ✓ جميع الأوامر والدوال مستخرجة تلقائياً من الملفات\n"
            markdown_content += "- ✓ استخدم ملف `" + pkgs_file + "` للحصول على تفاصيل كاملة\n"
            markdown_content += "- ✓ يمكنك تشغيل أي دالة بشكل مستقل دون تأثير على البقية\n"
            markdown_content += "- ✓ جميع الملفات محفوظة بشكل آمن في `" + lofee_file + "`\n\n"
            markdown_content += "---\n\n"
            markdown_content += "**تم التوليد بواسطة:** " + brand + " Lofee Builder\n"
            markdown_content += "**آخر تحديث:** " + created + "\n"
            
            with open(self.skills_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            print(f"[OK] تم توليد ملف Skills: {self.skills_file}")
            return True
            
        except Exception as e:
            print(f"[!] خطأ في توليد Skills Markdown: {str(e)}")
            return False
    
    def generate_manifest(self) -> bool:
        """توليد ملف JSON الخاص بالتشغيل الرئيسي"""
        try:
            manifest = {
                "maestrosoft_lofee": {
                    "brand": self.BRAND,
                    "model_name": self.MODEL_NAME,
                    "folder_name": self.metadata.get("folder_name"),
                    "format": "Lofee",
                    "version": self.metadata.get("version"),
                    "created_at": self.metadata.get("created_at"),
                    "lofee_file": self.output_file,
                    "manifest_file": self.json_file,
                    "packages_file": self.packages_file,
                    "skills_file": self.skills_file,
                    "file_extension": self.FILE_EXTENSION
                },
                "statistics": {
                    "total_files": self.metadata.get("total_files"),
                    "total_size_bytes": self.metadata.get("total_size"),
                    "total_size_formatted": self._format_size(self.metadata.get("total_size", 0)),
                    "total_functions": len(self.all_functions),
                    "total_classes": len(self.all_classes)
                },
                "file_index": [
                    {
                        "index": idx,
                        "path": f["rel_path"],
                        "size": f["size"],
                        "size_formatted": self._format_size(f["size"]),
                        "hash": f["hash"],
                        "extension": f["extension"],
                        "commands_extracted": len(f.get("commands", {}).get("functions", [])) + len(f.get("commands", {}).get("classes", []))
                    }
                    for idx, f in enumerate(self.files_to_fuse, 1)
                ],
                "runtime_instructions": {
                    "initialization": [
                        "✓ تحقق من وجود ملف Lofee",
                        "✓ اقرأ التوقيع وتحقق من الإصدار",
                        "✓ حمّل الفهرس من الذاكرة",
                        "✓ تهيئة نموذج BigLofee"
                    ],
                    "command_execution": [
                        "✓ ابحث عن الأ��ر في ملف packages.json",
                        "✓ استخرج الدالة أو الفئة المطلوبة",
                        "✓ قم بتشغيل الأمر المعني فقط",
                        "✓ أعد النتيجة للنموذج"
                    ]
                }
            }
            
            with open(self.json_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            print(f"[OK] تم توليد مفتاح التشغيل الرئيسي: {self.json_file}")
            return True
            
        except Exception as e:
            print(f"[!] خطأ في توليد Manifest JSON: {str(e)}")
            return False
    
    def run(self) -> bool:
        """تشغيل العملية الكاملة"""
        folder_name = os.path.basename(self.root_dir)
        
        print("=" * 70)
        print(f"🎼 بناء {self.BRAND} {self.MODEL_NAME} المتقدم")
        print(f"📁 الفولدر: {folder_name}")
        print("=" * 70)
        
        if not self.scan_directory():
            return False
        
        if not self.build_lofee():
            return False
        
        if not self.generate_packages_json():
            return False
        
        if not self.generate_skills_markdown():
            return False
        
        if not self.generate_manifest():
            return False
        
        print("\n" + "=" * 70)
        print("✅ تم إنجاز العملية بنجاح!")
        print("=" * 70)
        print(f"📦 ملف Lofee: {self.output_file}")
        print(f"📋 مفتاح التشغيل الرئيسي: {self.json_file}")
        print(f"📦 ملف الأوامر (Packages): {self.packages_file}")
        print(f"📚 دليل المهارات: {self.skills_file}")
        print(f"🎼 العلامة التجارية: {self.BRAND}")
        print(f"🤖 النموذج: {self.MODEL_NAME}")
        print("=" * 70)
        
        return True


def main():
    """نقطة البداية للبرنامج"""
    builder = MaestrosoftBuilder(".")
    builder.run()


if __name__ == "__main__":
    main()
