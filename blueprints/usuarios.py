from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
import bcrypt


usuarios_bp = Blueprint('usuarios_bp', __name__)

def verificar_admin(usuario_id):
    """Verifica si el usuario tiene rol de administrador (id_rol = 1)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_rol FROM Usuarios WHERE id = %s", (usuario_id,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    return usuario and usuario['id_rol'] == 1

# 🔹 Obtener todos los usuarios (solo admin)
@usuarios_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_usuarios():
    usuario_id = get_jwt_identity()
    if not verificar_admin(usuario_id):
        return jsonify({"error": "No autorizado"}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
    SELECT 
        u.*, 
        s.nombre AS nombre_sucursal, 
        sa.nombre AS sucursal_activa_nombre
    FROM Usuarios u
    LEFT JOIN Sucursales s ON u.id_sucursal = s.id
    LEFT JOIN Sucursales sa ON u.sucursal_activa = sa.id
""")

        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(usuarios), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Crear nuevo usuario (solo admin)
@usuarios_bp.route('/', methods=['POST'])
@jwt_required()
def crear_usuario():
    usuario_id = get_jwt_identity()
    if not verificar_admin(usuario_id):
        return jsonify({"error": "No autorizado"}), 403

    data = request.json
    nombre = data.get('nombre')
    correo = data.get('correo')
    clave = data.get('clave')
    id_sucursal = data.get('id_Sucursal')
    id_estado = data.get('id_estado')
    id_rol = data.get('id_rol', 2)  # por defecto, usuario común

    # Generar hash bcrypt
    salt = bcrypt.gensalt()
    clave_encriptada = bcrypt.hashpw(clave.encode('utf-8'), salt).decode('utf-8')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Usuarios (id, nombre, correo, clave, id_Sucursal, id_estado, id_rol, sucursal_activa)
            VALUES (UUID(), %s, %s, %s, %s, %s, %s, %s)
        """, (nombre, correo, clave_encriptada, id_sucursal, id_estado, id_rol, id_sucursal))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Usuario creado correctamente"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar usuarios
@usuarios_bp.route('/<string:usuario_id>', methods=['PUT'])
@jwt_required()
def editar_usuario(usuario_id):
    usuario_logueado = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar si el usuario logueado es administrador
    cursor.execute("SELECT id_rol FROM Usuarios WHERE id = %s", (usuario_logueado,))
    usuario = cursor.fetchone()
    if not usuario or usuario['id_rol'] != 1:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    data = request.json
    nombre = data.get('nombre')
    correo = data.get('correo')
    clave = data.get('clave')  # Puede ser None o vacío
    id_sucursal = data.get('id_sucursal')
    sucursal_activa = data.get('sucursal_activa')
    id_estado = data.get('id_estado')
    id_rol = data.get('id_rol')

    try:
        if clave:  # Solo si se envió una nueva clave
            salt = bcrypt.gensalt()
            clave = bcrypt.hashpw(clave.encode('utf-8'), salt).decode('utf-8')

            sql = """
                UPDATE Usuarios 
                SET nombre = %s, correo = %s, clave = %s, id_sucursal = %s,
                    sucursal_activa = %s, id_estado = %s, id_rol = %s
                WHERE id = %s
            """
            valores = (nombre, correo, clave, id_sucursal, sucursal_activa, id_estado, id_rol, usuario_id)
        else:
            sql = """
                UPDATE Usuarios 
                SET nombre = %s, correo = %s, id_sucursal = %s,
                    sucursal_activa = %s, id_estado = %s, id_rol = %s
                WHERE id = %s
            """
            valores = (nombre, correo, id_sucursal, sucursal_activa, id_estado, id_rol, usuario_id)

        cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Usuario actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#Eliminar usuario
@usuarios_bp.route('/<string:usuario_id>', methods=['DELETE'])
@jwt_required()
def eliminar_usuario(usuario_id):
    usuario_logueado = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar si el usuario logueado es administrador
    cursor.execute("SELECT id_rol FROM Usuarios WHERE id = %s", (usuario_logueado,))
    usuario = cursor.fetchone()
    if not usuario or usuario['id_rol'] != 1:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    try:
        cursor.execute("DELETE FROM Usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Usuario eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


    
@usuarios_bp.route('/sucursal', methods=['GET'])
@jwt_required()
def obtener_sucursal_usuario():
    try:
        usuario_id = get_jwt_identity()  # Obtener el ID del usuario desde el token JWT

        print(f"🔍 Buscando sucursal para usuario ID: {usuario_id}")  # 👀 Log para depuración

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_Sucursal FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        cursor.close()
        conn.close()

        if not usuario or not usuario['id_Sucursal']:
            print("❌ Usuario no encontrado o sin sucursal asignada")
            return jsonify({"error": "Usuario no encontrado o sin sucursal asignada"}), 404

        print(f"✅ Sucursal encontrada: {usuario['id_Sucursal']}")  # 👀 Log de éxito

        return jsonify({"id_sucursal": usuario['id_Sucursal']}), 200
    except Exception as e:
        print(f"❌ Error al obtener sucursal: {str(e)}")  # 👀 Log de error
        return jsonify({"error": str(e)}), 500

@usuarios_bp.route('/sucursal-activa', methods=['POST'])
@jwt_required()
def actualizar_sucursal_activa():
    usuario_id = get_jwt_identity()
    data = request.json
    nueva_sucursal = data.get("id_sucursal")

    if not nueva_sucursal:
        return jsonify({"error": "Sucursal no especificada"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Usuarios SET sucursal_activa = %s WHERE id = %s", (nueva_sucursal, usuario_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Sucursal actualizada"}), 200


# 🔹 Obtener sucursal activa del usuario logueado
@usuarios_bp.route('/sucursal-activa', methods=['GET'])
@jwt_required()
def obtener_sucursal_activa():
    usuario_id = get_jwt_identity()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        cursor.close()
        conn.close()

        if not usuario or usuario['sucursal_activa'] is None:
            return jsonify({"error": "No se encontró la sucursal activa"}), 404

        return jsonify({"sucursal_activa": usuario['sucursal_activa']}), 200

    except Exception as e:
        print(f"❌ Error al obtener sucursal activa: {e}")
        return jsonify({"error": str(e)}), 500
