from flask import Flask, Blueprint
from flask_jwt_extended import JWTManager
from config import Config
from flask_cors import CORS
from datetime import timedelta
import logging
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear la aplicación Flask
def create_app():
    app = Flask(__name__)
    
    # Configurar CORS
    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:*", "http://127.0.0.1:*", "http://192.168.1.52:*", "http://192.168.1.208:*", "http://192.168.1.60:*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "expose_headers": ["Content-Type", "Authorization"],
            "max_age": 3600
        }
    })

    # Configurar JWT
    app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=10)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'

    jwt = JWTManager(app)

    # Registrar los blueprints
    from blueprints.usuarios import usuarios_bp
    from blueprints.actividades import actividades_bp
    from blueprints.rendimientos import rendimientos_bp
    from blueprints.auth import auth_bp
    from blueprints.opciones import opciones_bp
    from blueprints.trabajadores import trabajadores_bp
    from blueprints.contratistas import contratistas_bp
    from blueprints.tarjas import tarjas_bp
    from blueprints.colaboradores import colaboradores_bp
    from blueprints.permisos import permisos_bp
    from blueprints.rendimientopropio import rendimientopropio_bp
    from blueprints.indicadores import indicadores_bp
    from blueprints.actividades_multiples import actividades_multiples_bp
    from blueprints.rendimiento_multiple import rendimiento_multiple_bp

    
    # Registrar blueprints
    app.register_blueprint(actividades_bp, url_prefix='/api/actividades')
    app.register_blueprint(rendimientos_bp, url_prefix='/api/rendimientos')
    app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
    app.register_blueprint(contratistas_bp, url_prefix='/api/contratistas')
    app.register_blueprint(trabajadores_bp, url_prefix='/api/trabajadores')
    app.register_blueprint(opciones_bp, url_prefix="/api/opciones")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(tarjas_bp, url_prefix="/api/tarjas")
    app.register_blueprint(colaboradores_bp, url_prefix='/api/colaboradores')
    app.register_blueprint(permisos_bp, url_prefix='/api/permisos')
    app.register_blueprint(rendimientopropio_bp, url_prefix='/api/rendimientopropio')
    app.register_blueprint(indicadores_bp, url_prefix='/api/indicadores')
    app.register_blueprint(actividades_multiples_bp, url_prefix='/api/actividades_multiples')
    app.register_blueprint(rendimiento_multiple_bp, url_prefix='/api/rendimiento_multiple')
    
    # Crear un nuevo blueprint para las rutas raíz
    root_bp = Blueprint('root_bp', __name__)
    
    # Importar y registrar las rutas raíz
    from blueprints.opciones import obtener_sucursales
    root_bp.add_url_rule('/sucursales/', 'obtener_sucursales', obtener_sucursales, methods=['GET', 'OPTIONS'])
    
    # Endpoint de prueba para verificar conexión a BD
    @root_bp.route('/test-db', methods=['GET'])
    def test_database():
        try:
            logger.info("🔍 Iniciando prueba de conexión a BD...")
            from utils.db import get_db_connection
            logger.info(f"📊 Configuración: DATABASE_URL={getattr(Config, 'DATABASE_URL', 'No definido')}")
            
            conn = get_db_connection()
            logger.info("✅ Conexión establecida")
            
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            logger.info(f"📊 MySQL Version: {version[0]}")
            
            cursor.close()
            conn.close()
            logger.info("✅ Prueba completada exitosamente")
            
            return {"status": "success", "message": "Conexión exitosa", "mysql_version": version[0]}, 200
        except Exception as e:
            logger.error(f"❌ Error en prueba de BD: {str(e)}")
            return {"status": "error", "message": str(e)}, 500
    
    # Endpoint de configuración para debug
    @root_bp.route('/config', methods=['GET'])
    def show_config():
        try:
            config_info = {
                "DATABASE_URL": getattr(Config, 'DATABASE_URL', 'No definido'),
                "DB_HOST": getattr(Config, 'DB_HOST', 'No definido'),
                "DB_USER": getattr(Config, 'DB_USER', 'No definido'),
                "DB_NAME": getattr(Config, 'DB_NAME', 'No definido'),
                "K_SERVICE": os.getenv('K_SERVICE', 'No definido'),
                "FLASK_ENV": os.getenv('FLASK_ENV', 'No definido')
            }
            return {"status": "success", "config": config_info}, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
    
    # Registrar el blueprint raíz
    app.register_blueprint(root_bp, url_prefix="/api")

    return app

# Crear una única instancia de la aplicación
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

