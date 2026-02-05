# JARV-S (Basit JARVIS Asistanı)

Bu proje, **Iron Man'deki JARVIS tarzında** Türkçe sohbet edebilen ve temel bilgisayar komutlarını çalıştırabilen bir başlangıç asistanıdır.

## Özellikler

- Türkçe sohbet
- Yerel LLM desteği (Ollama varsa)
- Ollama yoksa dahili fallback sohbet motoru
- Temel bilgisayar yönetimi:
  - Uygulama açma (izin listeli)
  - Uygulama kapatma (izin listeli)
  - Web sitesi açma
  - Dosya açma
- Opsiyonel sesli giriş (`speech_recognition`) ve sesli çıktı (`pyttsx3`)

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install pyttsx3 SpeechRecognition pyaudio
```

> Not: `pyaudio` bazı sistemlerde ekstra sistem paketi gerektirebilir.

## Çalıştırma

```bash
python3 jarvis.py
```

Sohbet sırasında:
- `çık` yazarak çıkabilirsin.
- `/voice` yazarak mikrofondan konuşmayı deneyebilirsin.

## Ollama entegrasyonu (önerilir)

Ollama kuruluysa asistan otomatik bağlanır.

```bash
ollama pull llama3.1
python3 jarvis.py --model llama3.1
```

## Örnek komutlar

- `merhaba`
- `yardım`
- `web aç youtube.com`
- `hesap makinesi aç`
- `uygulama kapat firefox`
- `dosya aç ~/Masaüstü/notlar.txt`

## Güvenlik Notu

Sistem komutları güvenlik amacıyla **izin listesi** ile sınırlandırılmıştır. Bunu genişletmek için `jarvis.py` içindeki whitelist alanlarını düzenleyebilirsin.
