import os
import bcrypt
import mysql.connector
from dotenv import load_dotenv

load_dotenv()  

# 🔗 Conéctate a la base de datos MySQL
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT"))  # 👈 clave
)
cursor = conn.cursor()

# 🔍 Buscar todas las contraseñas en texto plano
cursor.execute("SELECT id, clave FROM general_dim_usuario")
usuarios = cursor.fetchall()

for id, clave in usuarios:
    # Verificar si la contraseña ya está encriptada
    if not clave.startswith("$2b$"):
        print(f"Encriptando contraseña para usuario ID {id}...")

        # Generar hash bcrypt
        salt = bcrypt.gensalt()
        clave_encriptada = bcrypt.hashpw(clave.encode('utf-8'), salt).decode('utf-8')

        # Actualizar la contraseña en la base de datos
        cursor.execute("UPDATE general_dim_usuario SET clave = %s WHERE id = %s", (clave_encriptada, id))

conn.commit()
cursor.close()
conn.close()

print("✅ Todas las contraseñas han sido actualizadas correctamente.")
