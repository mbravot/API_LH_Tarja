from flask import Flask
from flask_jwt_extended import JWTManager
from config import Config
from flask_cors import CORS
from datetime import timedelta


# Crear la aplicación Flask
def create_app():
    app = Flask(__name__)
    
    # Configurar CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:*", "http://127.0.0.1:*", "http://192.168.1.208:*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "expose_headers": ["Content-Type", "Authorization"]
        }
    })

    # Configurar JWT
    app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY  # ✅
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=5)  # o el tiempo que quieras


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
    
    app.register_blueprint(contratistas_bp, url_prefix='/api/contratistas')
    app.register_blueprint(trabajadores_bp, url_prefix='/api/trabajadores')
    app.register_blueprint(opciones_bp, url_prefix="/api/opciones")
    app.register_blueprint(usuarios_bp, url_prefix="/api/usuarios")
    app.register_blueprint(actividades_bp, url_prefix="/api/actividades")
    app.register_blueprint(rendimientos_bp, url_prefix="/api/rendimientos")
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(tarjas_bp, url_prefix='/api/tarjas')

    return app

# Crear una única instancia de la aplicación
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

