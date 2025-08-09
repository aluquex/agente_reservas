import sqlite3

conn = sqlite3.connect("peluqueria.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM reservas")
filas = cursor.fetchall()

for fila in filas:
    print(fila)

conn.close()
