import mysql.connector
from config import Config
import os
import re

def get_db_connection():
    # Usar DATABASE_URL si está disponible (como la API de tickets)
    if hasattr(Config, 'DATABASE_URL') and Config.DATABASE_URL:
        # Parsear DATABASE_URL con formato de Cloud SQL
        # Formato: mysql+pymysql://user:password@/database?unix_socket=/cloudsql/instance
        url = Config.DATABASE_URL
        
        # Extraer componentes usando regex
        pattern = r'mysql\+pymysql://([^:]+):([^@]+)@/([^?]+)\?unix_socket=([^/]+)/(.+)'
        match = re.match(pattern, url)
        
        if match:
            user, password, database, socket_prefix, instance = match.groups()
            
            # Para Cloud SQL con unix_socket, usar localhost
            return mysql.connector.connect(
                host='localhost',
                user=user,
                password=password,
                database=database,
                port=3306,
                unix_socket=f'/cloudsql/{instance}'
            )
        else:
            # Fallback para formato simple
            url = url.replace('mysql+pymysql://', '')
            if '@' in url:
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
                # Formato sin host (localhost implícito)
                credentials, database = url.split('/', 1)
                user, password = credentials.split(':', 1)
                
                return mysql.connector.connect(
                    host='localhost',
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
