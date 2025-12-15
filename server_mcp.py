from mcp.server.fastmcp import FastMCP
import sqlite3

mcp = FastMCP("AgenToko")

@mcp.tool()
def jalankan_query(query_sql: str) -> str:
    """
    Menjalankan query SQL SELECT ke database toko.db.
    Gunakan ini untuk melihat data penjualan.
    """

    if not query_sql.strip().upper().startswith("SELECT"):
        return "Error: Maaf, saya hanya boleh membaca data (SELECT), tidak boleh mengubahnya."
    
    try:
        conn = sqlite3.connect("toko.db")
        cursor = conn.cursor()
        cursor.execute(query_sql)
        hasil = cursor.fetchall()
        conn.close()

        if not hasil:
            return "Data tidak ditemukan."
        return str(hasil)
    except Exception as e:
        return f"Error SQL: {e}"
    
if __name__ == "__main__":
    mcp.run()