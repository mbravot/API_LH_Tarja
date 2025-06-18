from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
import bcrypt
from datetime import date


usuarios_bp = Blueprint('usuarios_bp', __name__)

def verificar_admin(usuario_id):
    """Verifica si el usuario tiene perfil de administrador (id_perfil = 3)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_perfil FROM general_dim_usuario WHERE id = %s", (usuario_id,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    return usuario and usuario['id_perfil'] == 3

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
        u.id, u.usuario, u.correo, u.id_sucursalactiva, u.id_estado, u.id_rol, u.id_perfil, u.id_colaborador, u.fecha_creacion, s.nombre AS nombre_sucursal
    FROM general_dim_usuario u
    LEFT JOIN general_dim_sucursal s ON u.id_sucursalactiva = s.id
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
    usuario = data.get('usuario')
    correo = data.get('correo')
    clave = data.get('clave')
    id_sucursalactiva = data.get('id_sucursalactiva')
    id_estado = data.get('id_estado')
    id_rol = data.get('id_rol', 3)  # por defecto, usuario común
    id_perfil = data.get('id_perfil', 1)  # por defecto, perfil 1
    id_colaborador = data.get('id_colaborador')  # puede ser None

    # Validar campos obligatorios
    campos_obligatorios = [usuario, correo, clave, id_sucursalactiva, id_estado]
    if any(c in [None, ''] for c in campos_obligatorios):
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    # Generar hash bcrypt
    salt = bcrypt.gensalt()
    clave_encriptada = bcrypt.hashpw(clave.encode('utf-8'), salt).decode('utf-8')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO general_dim_usuario (
                id, usuario, correo, clave, id_sucursalactiva, 
                id_estado, id_rol, id_perfil, id_colaborador, fecha_creacion
            )
            VALUES (UUID(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (usuario, correo, clave_encriptada, id_sucursalactiva, 
              id_estado, id_rol, id_perfil, id_colaborador, date.today()))
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
    cursor.execute("SELECT id_perfil FROM general_dim_usuario WHERE id = %s", (usuario_logueado,))
    usuario = cursor.fetchone()
    if not usuario or usuario['id_perfil'] != 3:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    data = request.json
    usuario_nombre = data.get('usuario')
    correo = data.get('correo')
    clave = data.get('clave')  # Puede ser None o vacío
    id_sucursalactiva = data.get('id_sucursalactiva')
    id_estado = data.get('id_estado')
    id_rol = data.get('id_rol', 3)
    id_perfil = data.get('id_perfil', 1)
    id_colaborador = data.get('id_colaborador')  # puede ser None

    # Validar campos obligatorios
    campos_obligatorios = [usuario_nombre, correo, id_sucursalactiva, id_estado]
    if any(c in [None, ''] for c in campos_obligatorios):
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    try:
        if clave:  # Solo si se envió una nueva clave
            salt = bcrypt.gensalt()
            clave = bcrypt.hashpw(clave.encode('utf-8'), salt).decode('utf-8')
            sql = """
                UPDATE general_dim_usuario 
                SET usuario = %s, correo = %s, clave = %s, id_sucursalactiva = %s,
                    id_estado = %s, id_rol = %s, id_perfil = %s, id_colaborador = %s
                WHERE id = %s
            """
            valores = (usuario_nombre, correo, clave, id_sucursalactiva, 
                      id_estado, id_rol, id_perfil, id_colaborador, usuario_id)
        else:
            sql = """
                UPDATE general_dim_usuario 
                SET usuario = %s, correo = %s, id_sucursalactiva = %s,
                    id_estado = %s, id_rol = %s, id_perfil = %s, id_colaborador = %s
                WHERE id = %s
            """
            valores = (usuario_nombre, correo, id_sucursalactiva, 
                      id_estado, id_rol, id_perfil, id_colaborador, usuario_id)

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
    cursor.execute("SELECT id_perfil FROM general_dim_usuario WHERE id = %s", (usuario_logueado,))
    usuario = cursor.fetchone()
    if not usuario or usuario['id_perfil'] != 3:
        cursor.close()
        conn.close()
        return jsonify({"error": "No autorizado"}), 403

    try:
        cursor.execute("DELETE FROM general_dim_usuario WHERE id = %s", (usuario_id,))
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
        usuario_id = get_jwt_identity()

        print(f"🔍 Buscando sucursal para usuario ID: {usuario_id}")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        cursor.close()
        conn.close()

        if not usuario or not usuario['id_sucursalactiva']:
            print("❌ Usuario no encontrado o sin sucursal asignada")
            return jsonify({"error": "Usuario no encontrado o sin sucursal asignada"}), 404

        print(f"✅ Sucursal encontrada: {usuario['id_sucursalactiva']}")

        return jsonify({"id_sucursal": usuario['id_sucursalactiva']}), 200
    except Exception as e:
        print(f"❌ Error al obtener sucursal: {str(e)}")
        return jsonify({"error": str(e)}), 500

@usuarios_bp.route('/sucursal-activa', methods=['POST'])
@jwt_required()
def actualizar_sucursal_activa():
    try:
        usuario_id = get_jwt_identity()
        data = request.json
        nueva_sucursal = data.get("id_sucursal")

        if not nueva_sucursal:
            return jsonify({"error": "Sucursal no especificada"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar que el usuario tenga acceso a la sucursal
        cursor.execute("""
            SELECT 1 
            FROM usuario_pivot_sucursal_usuario 
            WHERE id_usuario = %s AND id_sucursal = %s
        """, (usuario_id, nueva_sucursal))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "No tienes acceso a esta sucursal"}), 403

        # Actualizar la sucursal activa
        cursor.execute("""
            UPDATE general_dim_usuario 
            SET id_sucursalactiva = %s 
            WHERE id = %s
        """, (nueva_sucursal, usuario_id))
        
        conn.commit()

        # Obtener el nombre de la sucursal para la respuesta
        cursor.execute("""
            SELECT nombre 
            FROM general_dim_sucursal 
            WHERE id = %s
        """, (nueva_sucursal,))
        
        sucursal = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Sucursal actualizada correctamente",
            "id_sucursal": nueva_sucursal,
            "sucursal_nombre": sucursal['nombre'] if sucursal else None
        }), 200

    except Exception as e:
        print(f"❌ Error al actualizar sucursal activa: {e}")
        return jsonify({"error": str(e)}), 500

# 🔹 Obtener sucursal activa del usuario logueado
@usuarios_bp.route('/sucursal-activa', methods=['GET'])
@jwt_required()
def obtener_sucursal_activa():
    usuario_id = get_jwt_identity()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        cursor.close()
        conn.close()

        if not usuario or usuario['id_sucursalactiva'] is None:
            return jsonify({"error": "No se encontró la sucursal activa"}), 404

        return jsonify({"sucursal_activa": usuario['id_sucursalactiva']}), 200

    except Exception as e:
        print(f"❌ Error al obtener sucursal activa: {e}")
        return jsonify({"error": str(e)}), 500

# Obtener colaboradores según la sucursal activa del usuario logueado o por parámetro
@usuarios_bp.route('/colaboradores', methods=['GET'])
@jwt_required()
def obtener_colaboradores():
    usuario_id = get_jwt_identity()
    id_sucursal = request.args.get('id_sucursal')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if not id_sucursal:
        # Buscar sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']
    # Buscar colaboradores activos de la sucursal
    cursor.execute("""
        SELECT id, nombre, apellido_paterno, apellido_materno, rut, codigo_verificador, id_cargo
        FROM general_dim_colaborador
        WHERE id_sucursal = %s AND id_estado = 1
        ORDER BY nombre, apellido_paterno
    """, (id_sucursal,))
    colaboradores = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(colaboradores), 200
