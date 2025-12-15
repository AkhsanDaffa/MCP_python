import asyncio
import os
from dotenv import load_dotenv

import google.generativeai as genai
from google.generativeai.types import content_types
from google.protobuf import struct_pb2

# Import library MCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

# ================= KONFIGURASI =================
# GANTI DENGAN API KEY ANDA
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("API Key tidak ditemukan! Pastikan sudah membuat file .env")

# Script server anda
SERVER_SCRIPT = "server_mcp.py"

# Gunakan model yang terdeteksi di komputer Anda
MODEL_NAME = 'gemini-2.5-flash-lite' 
# ===============================================

genai.configure(api_key=API_KEY)

async def run_chat():
    # 1. Menyiapkan parameter server
    server_params = StdioServerParameters(
        command="python",
        args=[SERVER_SCRIPT],
        env=None
    )

    print("🔌 Menghubungkan ke Server MCP...")
    
    # 2. Koneksi MCP
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Ambil daftar alat
            tools_list = await session.list_tools()
            tool_names = [t.name for t in tools_list.tools]
            print(f"✅ Terhubung! Alat ditemukan: {tool_names}")

            # 3. Definisi Tools untuk Gemini (Deklarasi Manual)
            # Kita beri tahu Gemini struktur alatnya secara eksplisit
            tools_declaration = [
                {
                    "name": "jalankan_query",
                    # PERUBAHAN ADA DI SINI:
                    # Kita kasih "contekkan" nama tabel dan kolomnya
                    "description": """
                        Menjalankan query SQL SELECT ke database. 
                        Tabel yang tersedia: 
                        - 'penjualan' (Kolom: id, barang, jumlah, harga).
                        Gunakan nama tabel 'penjualan', JANGAN 'products'.
                    """,
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "query_sql": {
                                "type": "STRING",
                                "description": "Perintah SQL SELECT yang valid"
                            }
                        },
                        "required": ["query_sql"]
                    }
                }
            ]

            # Tambahan 
            system_instruction = """
            Kamu adalah asisten analisis data toko. 
            Gunakan tool database untuk menjawab fakta.
            
            ATURAN BISNIS:
            - Jika total stok < 50 unit: Kategori "Toko Kecil".
            - Jika total stok 50-100 unit: Kategori "Toko Menengah".
            - Jika total stok > 100 unit: Kategori "Toko Besar".
            """

            # 4. Inisialisasi Model
            model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                tools=[tools_declaration], # Kirim definisi alat
                system_instruction=system_instruction # Tambahan
            )
            
            # Matikan automatic_function_calling agar kita bisa handle async sendiri
            chat = model.start_chat(enable_automatic_function_calling=False)

            print("\n💬 Silakan tanya tentang data penjualan (Ketik 'keluar' untuk stop)")
            print("-" * 50)

            while True:
                user_input = input("\nAnda: ")
                if user_input.lower() in ["keluar", "exit"]:
                    break

                # A. Kirim pesan user ke Gemini (Gunakan ASYNC)
                try:
                    response = await chat.send_message_async(user_input)
                except Exception as e:
                    print(f"Error komunikasi: {e}")
                    continue

                # B. Cek apakah Gemini ingin memanggil alat (Function Call)
                # Kita lakukan loop karena Gemini mungkin memanggil alat beberapa kali berturut-turut
                while response.candidates[0].content.parts[0].function_call:
                    part = response.candidates[0].content.parts[0]
                    fc = part.function_call
                    tool_name = fc.name
                    args = dict(fc.args)

                    print(f"   🤖 Gemini meminta: {tool_name} -> {args}")

                    # C. Eksekusi Alat MCP secara ASYNC (Ini kuncinya!)
                    try:
                        if tool_name == "jalankan_query":
                            # Panggil server MCP dan TUNGGU (await) hasilnya
                            mcp_result = await session.call_tool(tool_name, arguments=args)
                            result_text = mcp_result.content[0].text
                        else:
                            result_text = "Error: Alat tidak dikenal."
                    except Exception as e:
                        result_text = f"Error saat menjalankan tool: {str(e)}"

                    print(f"   💾 Hasil Database: {result_text}")

                    # D. Kirim hasil balik ke Gemini
                    # Kita harus menyusun paket respon sesuai format Gemini
                    function_response_part = content_types.to_part({
                        "function_response": {
                            "name": tool_name,
                            "response": {"result": result_text}
                        }
                    })

                    # Kirim hasil ke Gemini dan tunggu jawaban selanjutnya
                    response = await chat.send_message_async(function_response_part)
                
                # E. Tampilkan jawaban akhir (teks biasa)
                print(f"Gemini: {response.text}")

if __name__ == "__main__":
    # Fix untuk Windows Event Loop jika diperlukan
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(run_chat())