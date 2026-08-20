import pyaudio
import numpy as np
import threading
import queue
import time
import struct
import json
from datetime import datetime
from typing import Callable, Optional
import wave
import os
from pathlib import Path


class AudioStreamHandler:
    """معالج بث الصوت المباشر من ويندوز"""
    
    # إعدادات الصوت
    CHUNK = 1024  # حجم الكتلة الصوتية
    FORMAT = 8  # 16-bit PCM
    CHANNELS = 1  # Mono
    RATE = 16000  # 16kHz (مثالي للـ Speech Recognition)
    THRESHOLD = 500  # حد التشويش
    SILENCE_DURATION = 1.5  # مدة الصمت قبل إنهاء التسجيل
    
    def __init__(self):
        """تهيئة معالج الصوت"""
        self.audio = pyaudio.PyAudio()
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.frames = []
        self.start_time = None
        self.last_sound_time = None
        
        print("[*] تم تهيئة معالج الصو��")
        self._list_devices()
    
    def _list_devices(self):
        """عرض قائمة أجهزة الصوت المتاحة"""
        print("\n[*] أجهزة الصوت المتاحة:")
        print("=" * 60)
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            device_name = info['name']
            max_input = info['maxInputChannels']
            max_output = info['maxOutputChannels']
            
            if max_input > 0 or max_output > 0:
                device_type = "🎤 Input" if max_input > 0 else "🔊 Output"
                print(f"[{i}] {device_name} - {device_type}")
        print("=" * 60 + "\n")
    
    def start_listening(self):
        """بدء الاستماع في خيط منفصل"""
        self.is_listening = True
        listener_thread = threading.Thread(target=self._listening_loop, daemon=True)
        listener_thread.start()
        print("[✓] تم بدء الاستماع...")
    
    def stop_listening(self):
        """إيقاف الاستماع"""
        self.is_listening = False
        print("[✓] تم إيقاف الاستماع")
    
    def _listening_loop(self):
        """حلقة الاستماع المستمرة"""
        try:
            # فتح مجرى الصوت من المايك
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            print("[🎤] المايك نشط - في انتظار صوتك...")
            is_recording = False
            silence_counter = 0
            
            while self.is_listening:
                try:
                    # قراءة البيانات الصوتية
                    data = stream.read(self.CHUNK, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    
                    # حساب مستوى الصوت (RMS)
                    volume = np.sqrt(np.mean(audio_data ** 2))
                    
                    if volume > self.THRESHOLD:
                        # تم التقاط صوت
                        if not is_recording:
                            print("\n[🔴] تسجيل جاري...")
                            is_recording = True
                            self.frames = []
                            self.start_time = time.time()
                        
                        self.frames.append(data)
                        self.last_sound_time = time.time()
                        silence_counter = 0
                    
                    elif is_recording:
                        # حساب مدة الصمت
                        silence_duration = time.time() - self.last_sound_time if self.last_sound_time else 0
                        
                        if silence_duration > self.SILENCE_DURATION:
                            # انتهاء التسجيل
                            duration = time.time() - self.start_time
                            print(f"[⏹️] انتهى التسجيل ({duration:.1f}s)")
                            
                            # إرسال البيانات للمعالجة
                            audio_data = b''.join(self.frames)
                            self.audio_queue.put(audio_data)
                            
                            is_recording = False
                            self.frames = []
                        else:
                            # إضافة صمت قصير
                            self.frames.append(data)
                            silence_counter += 1
                
                except Exception as e:
                    print(f"[!] خطأ في القراءة: {e}")
                    continue
            
            stream.stop_stream()
            stream.close()
        
        except Exception as e:
            print(f"[!] خطأ في فتح مجرى الصوت: {e}")
    
    def get_audio_data(self, timeout=5):
        """الحصول على بيانات صوتية من القائمة"""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def save_audio_file(self, audio_data, filename="audio_record.wav"):
        """حفظ البيانات الصوتية في ملف WAV"""
        try:
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(self.CHANNELS)
                wav_file.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wav_file.setframerate(self.RATE)
                wav_file.writeframes(audio_data)
            print(f"[✓] تم حفظ الملف: {filename}")
            return filename
        except Exception as e:
            print(f"[!] خطأ في حفظ الملف: {e}")
            return None
    
    def cleanup(self):
        """تنظيف الموارد"""
        self.stop_listening()
        self.audio.terminate()
        print("[✓] تم تنظيف الموارد")


class TextToSpeechHandler:
    """معالج تحويل النص لصوت مع البث المباشر"""
    
    def __init__(self):
        """تهيئة معالج TTS"""
        self.audio = pyaudio.PyAudio()
        self.is_playing = False
        print("[*] تم تهيئة معالج TTS")
    
    def speak_streaming(self, text: str, rate: int = 16000):
        """
        نطق النص مع البث المباشر
        محاكاة الـ Streaming TTS
        """
        print(f"\n[🔊 LOFEE]: {text}")
        
        # تقسيم النص لكلمات للبث المرحلي
        words = text.split()
        
        try:
            stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=rate,
                output=True
            )
            
            self.is_playing = True
            print("[🎵] جاري النطق...")
            
            # محاكاة البث - كل 3 كلمات
            for i in range(0, len(words), 3):
                chunk = ' '.join(words[i:i+3])
                
                # توليد نبرة صوتية بسيطة (sine wave)
                audio_chunk = self._generate_tone_chunk(len(chunk) * 0.1)
                
                if audio_chunk is not None:
                    stream.write(audio_chunk)
                    time.sleep(0.1)
            
            stream.stop_stream()
            stream.close()
            self.is_playing = False
            print("[✓] انتهى النطق")
        
        except Exception as e:
            print(f"[!] خطأ في النطق: {e}")
    
    def _generate_tone_chunk(self, duration: float, frequency: float = 440) -> bytes:
        """توليد نبرة صوتية بسيطة"""
        try:
            sample_rate = 16000
            num_samples = int(sample_rate * duration)
            
            # إنشاء موجة جيبية
            t = np.linspace(0, duration, num_samples, False)
            wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
            
            # تحويل لـ Float32
            return wave_data.astype(np.float32).tobytes()
        except:
            return None
    
    def cleanup(self):
        """تنظيف الموارد"""
        self.audio.terminate()
        print("[✓] تم تنظيف موارد TTS")


class BigLofeeAudioAgent:
    """وكيل صوتي ذكي متصل بـ BigLofee"""
    
    def __init__(self):
        """تهيئة الوكيل الصوتي"""
        self.audio_handler = AudioStreamHandler()
        self.tts_handler = TextToSpeechHandler()
        self.is_running = False
        
        # تحميل ملفات المهارات
        self.skills_data = self._load_skills()
        
        print("\n" + "=" * 70)
        print("🎼 BigLofee Audio Assistant - وكيل صوتي ذكي")
        print("=" * 70)
        print("[✓] النظام جاهز للعمل\n")
    
    def _load_skills(self):
        """تحميل ملفات المهارات من Maestrosoft"""
        skills_data = {
            "commands": [],
            "functions": [],
            "capabilities": []
        }
        
        # البحث عن ملفات _skills.md و _packages.json
        for file in Path(".").glob("*_skills.md"):
            print(f"[✓] تم تحميل ملف المهارات: {file}")
        
        for file in Path(".").glob("*_packages.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    packages = json.load(f)
                    skills_data["commands"] = packages.get("executable_functions", [])
                    print(f"[✓] تم تحميل {len(skills_data['commands'])} أمر قابل للتنفيذ")
            except Exception as e:
                print(f"[!] خطأ في تحميل {file}: {e}")
        
        return skills_data
    
    def _process_command(self, text: str) -> str:
        """معالجة الأمر الصوتي وتحديد النية"""
        text_lower = text.lower()
        
        # البحث في الأوامر المسجلة
        for cmd in self.skills_data["commands"]:
            cmd_name = cmd.get("name", "").lower()
            if cmd_name in text_lower or text_lower in cmd_name:
                return f"تم تحديد الأمر: {cmd.get('name', 'غير معروف')}\nتنفيذ الأمر الآن..."
        
        # أوامر النظام
        if any(word in text_lower for word in ["افتح", "شغل", "لونش"]):
            return "تم تحديد أمر تنفيذي للنظام - جاري التنفيذ..."
        
        if any(word in text_lower for word in ["الوقت", "كم الساعة"]):
            current_time = datetime.now().strftime("%H:%M:%S")
            return f"الساعة الآن: {current_time}"
        
        if any(word in text_lower for word in ["التاريخ", "كم اليوم"]):
            current_date = datetime.now().strftime("%Y-%m-%d")
            return f"التاريخ اليوم: {current_date}"
        
        # رد افتراضي ودي
        return "تم استقبال أمرك بنجاح. كيف يمكنني مساعدتك؟"
    
    def run(self):
        """بدء حلقة الوكيل الرئيسية"""
        self.is_running = True
        self.audio_handler.start_listening()
        
        print("[🎤] اضغط Ctrl+C للإيقاف\n")
        
        try:
            while self.is_running:
                # انتظار بيانات صوتية
                audio_data = self.audio_handler.get_audio_data()
                
                if audio_data:
                    # حفظ الملف الصوتي للمرجع
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    wav_file = f"audio_record_{timestamp}.wav"
                    self.audio_handler.save_audio_file(audio_data, wav_file)
                    
                    # محاكاة تحويل الصوت لنص (في بيئة حقيقية ستستخدم STT مثل Whisper أو Azure)
                    simulated_text = "[Text Recognition Placeholder - استخدم Whisper أو STT آخر]"
                    print(f"\n[👤 أنت]: {simulated_text}")
                    
                    # معالجة الأمر
                    response = self._process_command(simulated_text)
                    
                    # الرد الصوتي
                    self.tts_handler.speak_streaming(response)
                    
                    time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\n[-] تم إيقاف النظام من قبل المستخدم")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """تنظيف الموارد"""
        self.is_running = False
        self.audio_handler.cleanup()
        self.tts_handler.cleanup()
        print("[✓] تم إغلاق النظام بنجاح")


def main():
    """نقطة البداية للتطبيق"""
    agent = BigLofeeAudioAgent()
    agent.run()


if __name__ == "__main__":
    main()
