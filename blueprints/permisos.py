from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from datetime import datetime, date
import uuid

permisos_bp = Blueprint('permisos_bp', __name__)

def format_fecha(fecha):
    if isinstance(fecha, (date, datetime)):
        return fecha.strftime('%Y-%m-%d')
    return fecha

# Listar permisos (solo de la sucursal activa del usuario)
@permisos_bp.route('', methods=['GET'])
@jwt_required()
def listar_permisos():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']
        # Listar permisos de colaboradores de la sucursal y del usuario autenticado
        cursor.execute("""
            SELECT p.*, t.nombre AS tipo_permiso, c.nombre AS nombre_colaborador, c.apellido_paterno, c.apellido_materno, e.nombre AS estado_permiso, a.nombre AS nombre_actividad
            FROM tarja_fact_permiso p
            JOIN tarja_dim_permisotipo t ON p.id_tipopermiso = t.id
            JOIN general_dim_colaborador c ON p.id_colaborador = c.id
            JOIN tarja_dim_permisoestado e ON p.id_estadopermiso = e.id
            LEFT JOIN tarja_fact_actividad a ON p.id_actividad = a.id
            WHERE c.id_sucursal = %s AND p.id_usuario = %s
            ORDER BY p.fecha DESC
        """, (id_sucursal, usuario_id))
        permisos = cursor.fetchall()
        cursor.close()
        conn.close()
        # Formatear fechas
        for permiso in permisos:
            if 'fecha' in permiso and permiso['fecha']:
                permiso['fecha'] = format_fecha(permiso['fecha'])
            if 'timestamp' in permiso and permiso['timestamp']:
                permiso['timestamp'] = format_fecha(permiso['timestamp'])
        return jsonify(permisos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear permiso
@permisos_bp.route('/', methods=['POST'])
@jwt_required()
def crear_permiso():
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validar campos requeridos
        campos_requeridos = ['fecha', 'id_tipopermiso', 'id_colaborador', 'horas', 'id_estadopermiso', 'id_actividad']
        for campo in campos_requeridos:
            if campo not in data or not data[campo]:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que la actividad existe
        cursor.execute("SELECT id FROM tarja_fact_actividad WHERE id = %s", (data['id_actividad'],))
        actividad = cursor.fetchone()
        if not actividad:
            cursor.close()
            conn.close()
            return jsonify({"error": "La actividad especificada no existe"}), 400
        
        # Generar id UUID
        permiso_id = str(uuid.uuid4())
        sql = """
            INSERT INTO tarja_fact_permiso (
                id, id_usuario, fecha, id_tipopermiso, id_colaborador, horas, id_estadopermiso, id_actividad
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            permiso_id,
            usuario_id,
            data['fecha'],
            data['id_tipopermiso'],
            data['id_colaborador'],
            data['horas'],
            data['id_estadopermiso'],
            data['id_actividad']
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Permiso creado correctamente", "id": permiso_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar permiso
@permisos_bp.route('/<string:permiso_id>', methods=['PUT'])
@jwt_required()
def editar_permiso(permiso_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Verificar que el permiso existe
        cursor.execute("SELECT * FROM tarja_fact_permiso WHERE id = %s", (permiso_id,))
        permiso = cursor.fetchone()
        if not permiso:
            return jsonify({"error": "Permiso no encontrado"}), 404
        # Actualizar campos editables
        sql = """
            UPDATE tarja_fact_permiso
            SET fecha = %s, id_tipopermiso = %s, id_colaborador = %s, horas = %s, id_estadopermiso = %s, id_actividad = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            data.get('fecha', permiso['fecha']),
            data.get('id_tipopermiso', permiso['id_tipopermiso']),
            data.get('id_colaborador', permiso['id_colaborador']),
            data.get('horas', permiso['horas']),
            data.get('id_estadopermiso', permiso['id_estadopermiso']),
            data.get('id_actividad', permiso['id_actividad']),
            permiso_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Permiso actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar permiso
@permisos_bp.route('/<string:permiso_id>', methods=['DELETE'])
@jwt_required()
def eliminar_permiso(permiso_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("DELETE FROM tarja_fact_permiso WHERE id = %s", (permiso_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Permiso eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@permisos_bp.route('/tipos', methods=['GET'])
@jwt_required()
def obtener_tipos_permiso():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM tarja_dim_permisotipo ORDER BY nombre ASC")
        tipos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(tipos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@permisos_bp.route('/actividades', methods=['GET'])
@jwt_required()
def obtener_actividades():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        # Obtener actividades de la sucursal
        cursor.execute("""
            SELECT id, nombre 
            FROM tarja_fact_actividad 
            WHERE id_sucursal = %s 
            ORDER BY nombre ASC
        """, (usuario['id_sucursalactiva'],))
        actividades = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(actividades), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@permisos_bp.route('/<string:permiso_id>', methods=['GET'])
@jwt_required()
def obtener_permiso_por_id(permiso_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, t.nombre AS tipo_permiso, c.nombre AS nombre_colaborador, c.apellido_paterno, c.apellido_materno, e.nombre AS estado_permiso, a.nombre AS nombre_actividad
            FROM tarja_fact_permiso p
            JOIN tarja_dim_permisotipo t ON p.id_tipopermiso = t.id
            JOIN general_dim_colaborador c ON p.id_colaborador = c.id
            JOIN tarja_dim_permisoestado e ON p.id_estadopermiso = e.id
            LEFT JOIN tarja_fact_actividad a ON p.id_actividad = a.id
            WHERE p.id = %s
        """, (permiso_id,))
        permiso = cursor.fetchone()
        cursor.close()
        conn.close()
        if not permiso:
            return jsonify({"error": "Permiso no encontrado"}), 404
        if 'fecha' in permiso and permiso['fecha']:
            permiso['fecha'] = format_fecha(permiso['fecha'])
        if 'timestamp' in permiso and permiso['timestamp']:
            permiso['timestamp'] = format_fecha(permiso['timestamp'])
        return jsonify(permiso), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
