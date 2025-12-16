import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import content_types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 1. Konfigurasi Awal
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
SERVER_SCRIPT = "server_mcp.py"

# Gunakan model rekomendasi (Penting: Nama model harus benar)
# Pastikan nama model ini sesuai dengan yang Anda punya akses
MODEL_NAME = 'gemini-2.5-flash-lite' 

genai.configure(api_key=API_KEY)

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Asisten Toko AI", page_icon="🤖")
st.title("🤖 Asisten Database Toko")
st.caption("Tanya jawab data penjualan menggunakan Gemini & MCP")

# 2. State Management
if "messages" not in st.session_state:
    st.session_state.messages = []

# Fungsi Utama (Tanpa Policy Aneh-aneh)
async def get_response_from_ai(user_prompt, chat_history):
    server_params = StdioServerParameters(
        command="python", # Pastikan python ada di path, atau gunakan sys.executable
        args=[SERVER_SCRIPT],
        env=None
    )

    tools_declaration = [{
        "name": "jalankan_query",
        "description": "Menjalankan query SQL SELECT. Tabel: 'penjualan' (id, barang, jumlah, harga).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query_sql": {"type": "STRING", "description": "Perintah SQL SELECT"}
            },
            "required": ["query_sql"]
        }
    }]

    system_instruction = """
    PERAN: Kamu adalah Admin Gudang yang kaku dan profesional.
    
    TUGAS UTAMA:
    Hanya menjawab pertanyaan seputar stok barang dan penjualan di tabel 'penjualan'.
    
    PANTANGAN (LARANGAN KERAS):
    1. JANGAN menjawab pertanyaan tentang coding, resep masakan, atau cuaca.
    2. JANGAN membuat puisi atau lelucon.
    3. Jika user bertanya di luar topik data toko, JAWAB: "Maaf, saya hanya mengurus data toko."
    
    ATURAN DATABASE:
    - Gunakan tool 'jalankan_query' untuk mencari fakta. Jangan menebak.
    """

    try:
        # Kita gunakan timeout agar tidak hang jika server macet
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                model = genai.GenerativeModel(
                    model_name=MODEL_NAME,
                    tools=[tools_declaration],
                    system_instruction=system_instruction
                )
                
                chat = model.start_chat(
                    enable_automatic_function_calling=False,
                    history=chat_history
                )

                response = await chat.send_message_async(user_prompt)

                while response.candidates[0].content.parts[0].function_call:
                    part = response.candidates[0].content.parts[0]
                    fc = part.function_call
                    tool_name = fc.name
                    args = dict(fc.args)

                    with st.status(f"🛠️ Sedang bekerja...", expanded=False) as status:
                        st.write(f"Tool: `{tool_name}`")
                        st.write(f"Query: `{args.get('query_sql')}`")
                        
                        if tool_name == "jalankan_query":
                            mcp_result = await session.call_tool(tool_name, arguments=args)
                            result_text = mcp_result.content[0].text
                            status.update(label="✅ Sukses ambil data!", state="complete")
                        else:
                            result_text = "Error: Alat tidak dikenal."
                            status.update(label="❌ Error", state="error")

                    function_response_part = content_types.to_part({
                        "function_response": {
                            "name": tool_name,
                            "response": {"result": result_text}
                        }
                    })
                    response = await chat.send_message_async(function_response_part)
                
                return response.text

    except Exception as e:
        # Tangkap error lebih detail
        return f"🚨 Error Teknis: {type(e).__name__} - {str(e)}"

# 3. UI Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Tanya stok barang..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Sedang berpikir..."):
            gemini_history = []
            for m in st.session_state.messages[:-1]:
                role = "user" if m["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [m["content"]]})

            try:
                # Langsung run tanpa policy khusus
                response_text = asyncio.run(get_response_from_ai(prompt, gemini_history))
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                st.error(f"Gagal menjalankan Async: {e}")