from flask import Blueprint, request, jsonify
import bcrypt
from config import Config
from utils.db import get_db_connection
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token
from datetime import date
import logging

# Configurar logging
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    correo = data.get('correo')
    clave = data.get('clave')
    usuario = data.get('usuario')
    id_sucursalactiva = data.get('id_sucursalactiva')
    id_estado = data.get('id_estado', 1)  # Por defecto activo
    id_rol = data.get('id_rol', 3)  # Por defecto usuario común
    id_perfil = data.get('id_perfil', 1)  # Por defecto perfil 1

    if not correo or not clave or not usuario or not id_sucursalactiva:
        return jsonify({"error": "Correo, clave, usuario y sucursal son requeridos"}), 400

    # Generar hash de la contraseña
    salt = bcrypt.gensalt()
    clave_encriptada = bcrypt.hashpw(clave.encode('utf-8'), salt)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO general_dim_usuario 
               (id, usuario, correo, clave, id_sucursalactiva, id_estado, id_rol, id_perfil, fecha_creacion) 
               VALUES (UUID(), %s, %s, %s, %s, %s, %s, %s, %s)""",
            (usuario, correo, clave_encriptada.decode('utf-8'), id_sucursalactiva, 
             id_estado, id_rol, id_perfil, date.today())
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Usuario registrado correctamente"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        logger.info("🔍 Iniciando proceso de login...")
        data = request.get_json()
        usuario = data.get('usuario')
        clave = data.get('clave')

        logger.info(f"👤 Usuario intentando login: {usuario}")

        if not usuario or not clave:
            logger.warning("❌ Faltan datos de usuario o clave")
            return jsonify({"error": "Faltan datos de usuario o clave"}), 400

        logger.info("🔗 Intentando conectar a la base de datos...")
        conn = get_db_connection()
        logger.info("✅ Conexión a BD establecida")
        
        cursor = conn.cursor(dictionary=True)

        # Buscar usuario y verificar estado y acceso a la app
        sql = """
            SELECT u.*, s.nombre as sucursal_nombre,
                   CONCAT(u.nombre, ' ', u.apellido_paterno, 
                          CASE WHEN u.apellido_materno IS NOT NULL THEN CONCAT(' ', u.apellido_materno) ELSE '' END) as nombre_completo
            FROM general_dim_usuario u
            LEFT JOIN general_dim_sucursal s ON u.id_sucursalactiva = s.id
            WHERE u.usuario = %s 
            AND u.id_estado = 1
            AND EXISTS (
                SELECT 1 
                FROM usuario_pivot_app_usuario p 
                WHERE p.id_usuario = u.id 
                AND p.id_app = 2
            )
        """
        logger.info("🔍 Ejecutando consulta de usuario...")
        cursor.execute(sql, (usuario,))
        user = cursor.fetchone()

        if not user:
            logger.warning(f"❌ Usuario no encontrado: {usuario}")
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario o clave incorrectos"}), 401

        logger.info("🔐 Verificando contraseña...")
        if not bcrypt.checkpw(clave.encode('utf-8'), user['clave'].encode('utf-8')):
            logger.warning(f"❌ Contraseña incorrecta para usuario: {usuario}")
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario o clave incorrectos"}), 401

        logger.info("✅ Usuario autenticado correctamente")

        # Crear token con información adicional
        access_token = create_access_token(
            identity=user['id'],
            additional_claims={
                'rol': user['id_rol'],
                'perfil': user['id_perfil'],
                'sucursal': user['id_sucursalactiva'],
                'sucursal_nombre': user['sucursal_nombre']
            }
        )

        cursor.close()
        conn.close()

        logger.info("🎉 Login exitoso")
        return jsonify({
            "access_token": access_token,
            "usuario": user['usuario'],
            "nombre": user['nombre'],
            "apellido_paterno": user['apellido_paterno'],
            "apellido_materno": user['apellido_materno'],
            "nombre_completo": user['nombre_completo'],
            "correo": user['correo'],
            "id_sucursal": user['id_sucursalactiva'],
            "sucursal_nombre": user['sucursal_nombre'],
            "id_rol": user['id_rol'],
            "id_perfil": user['id_perfil']
        }), 200

    except Exception as e:
        logger.error(f"❌ Error en login: {str(e)}")
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT u.*, s.nombre as sucursal_nombre,
                   CONCAT(u.nombre, ' ', u.apellido_paterno, 
                          CASE WHEN u.apellido_materno IS NOT NULL THEN CONCAT(' ', u.apellido_materno) ELSE '' END) as nombre_completo
            FROM general_dim_usuario u
            LEFT JOIN general_dim_sucursal s ON u.id_sucursalactiva = s.id
            WHERE u.id = %s 
            AND u.id_estado = 1
            AND EXISTS (
                SELECT 1 
                FROM usuario_pivot_app_usuario p 
                WHERE p.id_usuario = u.id 
                AND p.id_app = 2
            )
        """
        cursor.execute(sql, (usuario_id,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "Usuario no encontrado o sin acceso"}), 401

        access_token = create_access_token(
            identity=user['id'],
            additional_claims={
                'rol': user['id_rol'],
                'perfil': user['id_perfil'],
                'sucursal': user['id_sucursalactiva'],
                'sucursal_nombre': user['sucursal_nombre']
            }
        )

        cursor.close()
        conn.close()

        return jsonify({
            "access_token": access_token,
            "usuario": user['usuario'],
            "nombre": user['nombre'],
            "apellido_paterno": user['apellido_paterno'],
            "apellido_materno": user['apellido_materno'],
            "nombre_completo": user['nombre_completo'],
            "correo": user['correo'],
            "id_sucursal": user['id_sucursalactiva'],
            "sucursal_nombre": user['sucursal_nombre'],
            "id_rol": user['id_rol'],
            "id_perfil": user['id_perfil']
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/cambiar-clave', methods=['POST'])
@jwt_required()
def cambiar_clave():
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        clave_actual = data.get('clave_actual')
        nueva_clave = data.get('nueva_clave')

        if not clave_actual or not nueva_clave:
            return jsonify({"error": "Faltan datos de clave"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar clave actual
        cursor.execute("SELECT clave FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(clave_actual.encode('utf-8'), user['clave'].encode('utf-8')):
            cursor.close()
            conn.close()
            return jsonify({"error": "Clave actual incorrecta"}), 401

        # Generar nuevo hash con bcrypt
        salt = bcrypt.gensalt()
        nueva_clave_hash = bcrypt.hashpw(nueva_clave.encode('utf-8'), salt)

        # Actualizar clave
        cursor.execute("UPDATE general_dim_usuario SET clave = %s WHERE id = %s", 
                      (nueva_clave_hash.decode('utf-8'), usuario_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Clave actualizada correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/cambiar-sucursal', methods=['POST'])
@jwt_required()
def cambiar_sucursal():
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        nueva_sucursal_id = data.get('id_sucursal')

        if not nueva_sucursal_id:
            return jsonify({"error": "El ID de la sucursal es requerido"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar que el usuario tenga acceso a la sucursal
        cursor.execute("""
            SELECT 1 
            FROM usuario_pivot_sucursal_usuario 
            WHERE id_usuario = %s AND id_sucursal = %s
        """, (usuario_id, nueva_sucursal_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "No tienes acceso a esta sucursal"}), 403

        # Actualizar la sucursal activa
        cursor.execute("""
            UPDATE general_dim_usuario 
            SET id_sucursalactiva = %s 
            WHERE id = %s
        """, (nueva_sucursal_id, usuario_id))
        
        conn.commit()

        # Obtener el nombre de la sucursal para la respuesta
        cursor.execute("""
            SELECT nombre 
            FROM general_dim_sucursal 
            WHERE id = %s
        """, (nueva_sucursal_id,))
        
        sucursal = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Sucursal actualizada correctamente",
            "id_sucursal": nueva_sucursal_id,
            "sucursal_nombre": sucursal['nombre'] if sucursal else None
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
