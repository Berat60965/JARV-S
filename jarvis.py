#!/usr/bin/env python3
"""Basit bir JARVIS benzeri asistan.

Özellikler:
- Metin veya sesli sohbet (opsiyonel paketlerle)
- Bilgisayar komutları (güvenli izin listesi ile)
- Yerel LLM (Ollama) varsa ondan cevap alır, yoksa yerel sohbet motoru kullanır
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import subprocess
import webbrowser
from dataclasses import dataclass, field
from typing import Callable
from urllib import error, request
import json


SYSTEM_PROMPT = (
    "Sen JARVIS tarzı bir asistansın. Türkçe konuş, kısa ve net cevaplar ver, "
    "tehlikeli isteklerde kullanıcıyı uyar."
)


@dataclass
class AssistantConfig:
    name: str = "JARVIS"
    model: str = "llama3.1"
    ollama_url: str = "http://127.0.0.1:11434/api/chat"
    allow_system_actions: bool = True


@dataclass
class JarvisAssistant:
    config: AssistantConfig = field(default_factory=AssistantConfig)
    history: list[dict[str, str]] = field(default_factory=list)

    def speak(self, text: str) -> None:
        """Metni yazdırır; pyttsx3 varsa seslendirir."""
        print(f"\n{self.config.name}: {text}\n")
        try:
            import pyttsx3  # type: ignore

            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception:
            # Ses altyapısı opsiyonel; hata verirse sessizce yazılı moda düş.
            pass

    def listen(self) -> str:
        """Önce metin girişini alır; kullanıcı /voice yazarsa mikrofona geçer."""
        raw = input("Sen: ").strip()
        if raw != "/voice":
            return raw

        try:
            import speech_recognition as sr  # type: ignore

            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                print("Dinliyorum...")
                audio = recognizer.listen(source, timeout=6, phrase_time_limit=15)
            text = recognizer.recognize_google(audio, language="tr-TR")
            print(f"Sen (ses): {text}")
            return text
        except Exception as exc:
            return f"Ses algılama başarısız oldu: {exc}"

    def chat_completion(self, user_text: str) -> str:
        """Ollama varsa onu kullanır, yoksa basit yerel yanıt üretir."""
        if self._is_ollama_available():
            response = self._ollama_chat(user_text)
            if response:
                return response
        return self._fallback_response(user_text)

    def _is_ollama_available(self) -> bool:
        req = request.Request(self.config.ollama_url.replace("/chat", "/tags"), method="GET")
        try:
            with request.urlopen(req, timeout=1.5):
                return True
        except Exception:
            return False

    def _ollama_chat(self, user_text: str) -> str | None:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                *self.history[-8:],
                {"role": "user", "content": user_text},
            ],
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.config.ollama_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=25) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
                return parsed.get("message", {}).get("content")
        except error.URLError:
            return None
        except Exception:
            return None

    def _fallback_response(self, user_text: str) -> str:
        text = user_text.lower()
        if any(k in text for k in ["merhaba", "selam"]):
            return "Merhaba! Hazırım. Bilgisayar komutu vermek için 'aç', 'kapat', 'web' gibi ifadeler kullanabilirsin."
        if "nasılsın" in text:
            return "Sistemlerim stabil, teşekkürler. Sana nasıl yardımcı olayım?"
        if "yardım" in text:
            return (
                "Örnekler: 'not defteri aç', 'web aç youtube.com', 'hesap makinesi aç', "
                "'uygulama kapat notepad'."
            )
        return (
            "Bunu yanıtlayabilirim, ama daha güçlü sohbet için Ollama kurup modeli çekmen iyi olur. "
            "Yine de komutlarını uygulamaya hazırım."
        )

    def maybe_run_system_action(self, user_text: str) -> str | None:
        if not self.config.allow_system_actions:
            return None

        handlers: list[tuple[re.Pattern[str], Callable[[re.Match[str]], str]]] = [
            (re.compile(r"(?:web|site) aç\s+(.+)", re.I), self._open_website),
            (re.compile(r"(.+)\s+aç$", re.I), self._open_app),
            (re.compile(r"(?:uygulama|program) kapat\s+(.+)", re.I), self._kill_app),
            (re.compile(r"dosya aç\s+(.+)", re.I), self._open_file),
        ]

        for pattern, fn in handlers:
            match = pattern.search(user_text.strip())
            if match:
                return fn(match)
        return None

    def _open_website(self, match: re.Match[str]) -> str:
        url = match.group(1).strip()
        if not re.match(r"https?://", url):
            url = "https://" + url
        webbrowser.open(url)
        return f"Web sitesi açıldı: {url}"

    def _open_app(self, match: re.Match[str]) -> str:
        app_name = match.group(1).strip().lower()
        whitelist = {
            "hesap makinesi": ["calc"] if platform.system() == "Windows" else ["gnome-calculator", "kcalc"],
            "not defteri": ["notepad"] if platform.system() == "Windows" else ["gedit", "nano"],
            "terminal": ["cmd"] if platform.system() == "Windows" else ["x-terminal-emulator", "gnome-terminal", "konsole"],
        }

        if app_name not in whitelist:
            return (
                f"'{app_name}' için otomatik açma izni yok. Güvenlik için yalnızca izinli uygulamalar açılır: "
                f"{', '.join(whitelist)}"
            )

        for cmd in whitelist[app_name]:
            try:
                subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"{app_name.title()} açıldı."
            except FileNotFoundError:
                continue
        return f"{app_name.title()} açılamadı. Sistemde uygun komut bulunamadı."

    def _kill_app(self, match: re.Match[str]) -> str:
        proc = match.group(1).strip()
        safe_names = {"notepad", "calc", "gedit", "gnome-calculator", "chrome", "firefox"}
        if proc not in safe_names:
            return "Bu süreç adı güvenlik listesinde değil; kapatma işlemi iptal edildi."

        if platform.system() == "Windows":
            cmd = ["taskkill", "/IM", proc, "/F"]
        else:
            cmd = ["pkill", "-f", proc]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return f"{proc} kapatıldı."
        except subprocess.CalledProcessError:
            return f"{proc} kapatılamadı veya zaten kapalı."

    def _open_file(self, match: re.Match[str]) -> str:
        target = os.path.expanduser(match.group(1).strip())
        if not os.path.exists(target):
            return f"Dosya bulunamadı: {target}"

        if platform.system() == "Windows":
            os.startfile(target)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return f"Dosya açıldı: {target}"

    def run(self) -> None:
        self.speak(
            "JARVIS aktif. Çıkmak için 'çık' veya 'exit' yaz. Sesli giriş için '/voice' yazabilirsin."
        )
        while True:
            user_text = self.listen().strip()
            if not user_text:
                continue
            if user_text.lower() in {"çık", "exit", "quit"}:
                self.speak("Görüşürüz.")
                return

            action_result = self.maybe_run_system_action(user_text)
            if action_result:
                self.speak(action_result)
                continue

            answer = self.chat_completion(user_text)
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": answer})
            self.speak(answer)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="JARVIS benzeri konuşabilen ve temel sistem komutları çalıştırabilen asistan."
    )
    parser.add_argument("--name", default="JARVIS", help="Asistan adı")
    parser.add_argument("--model", default="llama3.1", help="Ollama model adı")
    parser.add_argument(
        "--no-system-actions",
        action="store_true",
        help="Sistem komutlarını devre dışı bırakır (yalnızca sohbet modu).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = AssistantConfig(
        name=args.name,
        model=args.model,
        allow_system_actions=not args.no_system_actions,
    )
    JarvisAssistant(config=config).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
