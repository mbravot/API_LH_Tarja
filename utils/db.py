import mysql.connector
from config import Config
import os

def get_db_connection():
    # Usar DATABASE_URL si está disponible (como la API de tickets)
    if hasattr(Config, 'DATABASE_URL') and Config.DATABASE_URL:
        # Parsear DATABASE_URL
        # Formato: mysql+pymysql://user:password@host/database
        url = Config.DATABASE_URL.replace('mysql+pymysql://', '')
        credentials, rest = url.split('@', 1)
        user, password = credentials.split(':', 1)
        host, database = rest.split('/', 1)
        
        return mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=3306
        )
    else:
        # Fallback a la configuración anterior
        return mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=Config.DB_PORT
        )
