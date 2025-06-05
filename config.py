import os
from dotenv import load_dotenv

load_dotenv()  # Carga las variables del archivo .env

class Config:
    DEBUG = os.getenv("DEBUG", "True") == "True"
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME", "lahornilla_base_normalizada")  # Nombre de la base de datos por defecto
    DB_PORT = int(os.getenv("DB_PORT", 35026))
    JWT_SECRET_KEY = 'Inicio01*'  # ✅ Esta clave es usada por Flask-JWT-Extended
    SECRET_KEY = 'Inicio01*'
    DEBUG = True
