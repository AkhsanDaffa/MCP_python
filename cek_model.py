import google.generativeai as genai
import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("API Key tidak ditemukan! Pastikan sudah membuat file .env")


genai.configure(api_key=API_KEY)

print("Mencari model yang tersedia...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")