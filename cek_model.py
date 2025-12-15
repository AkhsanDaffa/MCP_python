import google.generativeai as genai

API_KEY = "AIzaSyBo05xl3RYX2JgkhCBgXEgJNjP9MsHDamU"

genai.configure(api_key=API_KEY)

print("Mencari model yang tersedia...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")