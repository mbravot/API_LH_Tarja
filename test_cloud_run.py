#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import mysql.connector
from config import Config

def test_cloud_run_connection():
    """Prueba la conexión a la base de datos en Cloud Run"""
    
    print("🔍 Probando conexión en Cloud Run...")
    print(f"K_SERVICE: {os.getenv('K_SERVICE', 'No definido')}")
    print(f"DB_HOST: {Config.DB_HOST}")
    print(f"DB_PORT: {Config.DB_PORT}")
    print(f"DB_USER: {Config.DB_USER}")
    print(f"DB_NAME: {Config.DB_NAME}")
    
    try:
        # Intentar conexión
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=Config.DB_PORT,
            connect_timeout=10
        )
        
        if connection.is_connected():
            print("✅ Conexión exitosa!")
            
            # Probar consulta
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"📊 MySQL Version: {version[0]}")
            
            # Probar tabla de usuarios
            cursor.execute("SELECT COUNT(*) FROM general_dim_usuario")
            count = cursor.fetchone()
            print(f"👥 Usuarios en BD: {count[0]}")
            
            cursor.close()
            connection.close()
            return True
        else:
            print("❌ No se pudo conectar")
            return False
            
    except mysql.connector.Error as err:
        print(f"❌ Error MySQL: {err}")
        print("\n💡 Posibles soluciones:")
        print("1. Verificar que Cloud SQL esté conectado en Cloud Run")
        print("2. Verificar variables de entorno")
        print("3. Verificar permisos de la cuenta de servicio")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

if __name__ == "__main__":
    test_cloud_run_connection() 