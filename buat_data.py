import sqlite3

conn= sqlite3.connect("toko.db")
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS penjualan")
cursor.execute("""
    CREATE TABLE penjualan (
               id INTEGER PRIMARY KEY,
               barang TEXT,
               jumlah INTEGER,
               harga INTEGER)
""")

data_dummy = [
    ('Laptop', 2, 10000000),
    ('Mouse', 5, 100000),
    ('Keyboard', 3, 500000),
    ('Monitor', 1, 2000000)
]

cursor.executemany("INSERT INTO penjualan (barang, jumlah, harga) VALUES (?, ?, ?)", data_dummy)
conn.commit()
print("Database 'toko.db' berhasil dibuat dengan isinya!")
conn.close()