from flask import Blueprint, request, jsonify
import bcrypt
from config import Config
from utils.db import get_db_connection
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    correo = data.get('correo')
    clave = data.get('clave')

    if not correo or not clave:
        return jsonify({"error": "Correo y clave son requeridos"}), 400

    # Generar hash de la contraseña
    salt = bcrypt.gensalt()
    clave_encriptada = bcrypt.hashpw(clave.encode('utf-8'), salt)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Usuarios (correo, clave) VALUES (%s, %s)",
            (correo, clave_encriptada.decode('utf-8'))
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Usuario registrado correctamente"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    correo = data.get('correo')
    clave = data.get('clave')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔄 AÑADIR JOIN para obtener también el nombre de la sucursal
    cursor.execute("""
    SELECT u.id, u.nombre, u.sucursal_activa AS id_sucursal, u.clave, s.nombre AS nombre_sucursal, id_rol
    FROM Usuarios u
    LEFT JOIN Sucursales s ON u.sucursal_activa = s.id
    WHERE u.correo=%s
""", (correo,))

    
    usuario = cursor.fetchone()

    cursor.close()
    conn.close()

    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if not bcrypt.checkpw(clave.encode('utf-8'), usuario['clave'].encode('utf-8')):
        return jsonify({"error": "Clave incorrecta"}), 401

    # ✅ Generar tokens de acceso y refresco
    access_token = create_access_token(
        identity=str(usuario['id']),
        additional_claims={"nombre": usuario['nombre'], "id_sucursal": usuario['id_sucursal']}
    )
    refresh_token = create_refresh_token(identity=str(usuario['id']))

    # ✅ INCLUIR nombre_sucursal en la respuesta
    return jsonify({
        "token": access_token,
        "refresh_token": refresh_token,
        "nombre": usuario['nombre'],
        "id_sucursal": usuario['id_sucursal'],
        "nombre_sucursal": usuario['nombre_sucursal'],  # 🏢 nuevo
        "id_rol": usuario['id_rol']  # 🔥 Agregado
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)  # 🔥 Este requiere el refresh_token
def refresh_token():
    usuario_id = get_jwt_identity()
    nuevo_token = create_access_token(identity=usuario_id)
    return jsonify({"token": nuevo_token}), 200



@auth_bp.route('/cambiar-clave', methods=['POST'])
@jwt_required()
def cambiar_clave():
    try:
        data = request.json
        usuario_id = get_jwt_identity()  # ID del usuario autenticado

        clave_actual = data.get('clave_actual')
        nueva_clave = data.get('nueva_clave')

        if not clave_actual or not nueva_clave:
            return jsonify({"error": "Debe ingresar ambas contraseñas"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener la clave actual del usuario
        cursor.execute("SELECT clave FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Verificar la clave actual
        if not bcrypt.checkpw(clave_actual.encode('utf-8'), usuario['clave'].encode('utf-8')):
            return jsonify({"error": "La contraseña actual es incorrecta"}), 401

        # Cifrar la nueva clave
        salt = bcrypt.gensalt()
        clave_encriptada = bcrypt.hashpw(nueva_clave.encode('utf-8'), salt)

        # Actualizar la clave en la base de datos
        cursor.execute("UPDATE Usuarios SET clave = %s WHERE id = %s", (clave_encriptada.decode('utf-8'), usuario_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Contraseña actualizada correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
