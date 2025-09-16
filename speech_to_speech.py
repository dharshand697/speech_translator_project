import speech_recognition as sr
from deep_translator import GoogleTranslator
import pyttsx3
import time
import sqlite3
import re
import logging

# ====== PROFANITY CLEANER ======
BANNED = ['fuck', 'fucking', 'shit', 'bitch', 'asshole', 'motherfucker']
pattern = re.compile(r'\b(' + '|'.join(re.escape(w) for w in BANNED) + r')\b', flags=re.IGNORECASE)

def clean_text(text):
    """Remove banned words and extra spaces from text"""
    cleaned = pattern.sub('', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned
# ===============================

# ====== LOGGING CONFIG ======
logging.basicConfig(
    filename="translations.log",
    level=logging.INFO,
    format="%(asctime)s | SRC:%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
# =============================

def init_tts():
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    return engine

def speak_text(engine, text):
    engine.say(text)
    engine.runAndWait()

def log_translation(src_lang, tgt_lang, source_text, translated_text):
    """Log to both database and log file"""
    # ---- SQLite DB ----
    try:
        conn = sqlite3.connect("translations.db")
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS translations (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "source_lang TEXT, target_lang TEXT, source_text TEXT, translated_text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        cursor.execute(
            "INSERT INTO translations (source_lang, target_lang, source_text, translated_text) VALUES (?, ?, ?, ?)", 
            (src_lang, tgt_lang, source_text, translated_text)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Failed to log translation:", e)

    # ---- Log File ----
    logging.info(f"{src_lang}->{tgt_lang} | {source_text} => {translated_text}")

def main():
    print("=== Simple Speech-to-Speech Translator (Deep Translator Version) ===")
    print("You need a microphone and Internet (for recognition + translation).")
    print("Supported language codes: en (English), hi (Hindi), es (Spanish), fr (French), de (German), etc.")
    print("Type 'exit' as source language to quit.\n")

    src_lang = input("Enter SOURCE language code (e.g. en): ").strip() or "en"
    if src_lang.lower() == "exit":
        print("Exiting.")
        return
    tgt_lang = input("Enter TARGET language code (e.g. hi): ").strip() or "hi"

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    tts_engine = init_tts()

    print("\nAdjusting for ambient noise, please be silent for 1 second...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    print("Ready! Speak now (say 'stop' to end).")

    while True:
        try:
            with mic as source:
                print("\nListening...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            print("Recognizing...")
            try:
                recognized = recognizer.recognize_google(audio, language=src_lang)
            except sr.UnknownValueError:
                print("Could not understand audio.")
                continue
            except sr.RequestError as e:
                print("Could not request results from Google Speech Recognition service; {0}".format(e))
                continue

            recognized = recognized.strip()
            # Clean text before showing/translation
            cleaned = clean_text(recognized)

            print(f"Source [{src_lang}]: {cleaned}")

            if cleaned.lower() in ("stop", "exit", "quit"):
                print("Stopping translator.")
                break

            # Translate using deep-translator
            try:
                translated = GoogleTranslator(source=src_lang, target=tgt_lang).translate(cleaned)
            except Exception as e:
                print("Translation failed:", e)
                translated = "[translation error]"

            print(f"Translated [{tgt_lang}]: {translated}")

            # Log to DB + log file
            log_translation(src_lang, tgt_lang, cleaned, translated)

            # Speak the translated text (TTS)
            speak_text(tts_engine, translated)

        except sr.WaitTimeoutError:
            print("Listening timed out, trying again...")
            continue
        except KeyboardInterrupt:
            print("\nUser interrupted. Exiting.")
            break
        except Exception as e:
            print("Unexpected error:", e)
            time.sleep(1)
            continue

    try:
        tts_engine.stop()
    except Exception:
        pass

if __name__ == "__main__":
    main()
