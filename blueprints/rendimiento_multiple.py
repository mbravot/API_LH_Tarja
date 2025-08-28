import datetime
from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta


rendimiento_multiple_bp = Blueprint('rendimiento_multiple_bp', __name__)

# 🚀 Endpoint para obtener rendimientos propios de una actividad múltiple
@rendimiento_multiple_bp.route('/actividad/<string:id_actividad>', methods=['GET'])
@jwt_required()
def obtener_rendimientos_actividad(id_actividad):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar que la actividad pertenece al usuario y es una actividad múltiple
        cursor.execute("""
            SELECT id FROM tarja_fact_actividad 
            WHERE id = %s AND id_usuario = %s 
            AND id_tipotrabajador = 1 
            AND id_contratista IS NULL 
            AND id_tiporendimiento = 3
        """, (id_actividad, usuario_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad múltiple no encontrada o no tienes permiso para acceder"}), 404

        # Obtener rendimientos propios de la actividad
        cursor.execute("""
            SELECT 
                r.id,
                r.id_actividad,
                r.id_colaborador,
                r.rendimiento,
                r.horas_trabajadas,
                r.horas_extras,
                r.id_bono,
                r.id_ceco,
                c.nombre as nombre_colaborador,
                c.rut as rut_colaborador,
                b.nombre as nombre_bono,
                ce.nombre as nombre_ceco
            FROM tarja_fact_rendimientopropio r
            LEFT JOIN general_dim_colaborador c ON r.id_colaborador = c.id
            LEFT JOIN general_dim_bono b ON r.id_bono = b.id
            LEFT JOIN general_dim_ceco ce ON r.id_ceco = ce.id
            WHERE r.id_actividad = %s
            ORDER BY c.nombre ASC
        """, (id_actividad,))

        rendimientos = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(rendimientos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para obtener todos los rendimientos propios del usuario
@rendimiento_multiple_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_rendimientos_usuario():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró sucursal activa para el usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']

        # Obtener rendimientos propios de actividades múltiples del usuario
        cursor.execute("""
            SELECT 
                r.id,
                r.id_actividad,
                r.id_colaborador,
                r.rendimiento,
                r.horas_trabajadas,
                r.horas_extras,
                r.id_bono,
                r.id_ceco,
                c.nombre as nombre_colaborador,
                c.rut as rut_colaborador,
                b.nombre as nombre_bono,
                ce.nombre as nombre_ceco,
                a.fecha,
                a.id_labor,
                l.nombre as nombre_labor
            FROM tarja_fact_rendimientopropio r
            LEFT JOIN general_dim_colaborador c ON r.id_colaborador = c.id
            LEFT JOIN general_dim_bono b ON r.id_bono = b.id
            LEFT JOIN general_dim_ceco ce ON r.id_ceco = ce.id
            LEFT JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            WHERE a.id_usuario = %s 
            AND a.id_sucursalactiva = %s
            AND a.id_tipotrabajador = 1 
            AND a.id_contratista IS NULL 
            AND a.id_tiporendimiento = 3
            ORDER BY a.fecha DESC, c.nombre ASC
        """, (usuario_id, id_sucursal))

        rendimientos = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convertir fecha a string
        for rendimiento in rendimientos:
            if isinstance(rendimiento['fecha'], (date, datetime)):
                rendimiento['fecha'] = rendimiento['fecha'].strftime('%Y-%m-%d')

        return jsonify(rendimientos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para crear un nuevo rendimiento propio
@rendimiento_multiple_bp.route('/', methods=['POST'])
@jwt_required()
def crear_rendimiento():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        # Validar campos requeridos
        campos_requeridos = ['id_actividad', 'id_colaborador', 'rendimiento', 'horas_trabajadas']
        for campo in campos_requeridos:
            if campo not in data or data[campo] in [None, '']:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400

        id_actividad = data['id_actividad']
        id_colaborador = data['id_colaborador']
        rendimiento = data['rendimiento']
        horas_trabajadas = data['horas_trabajadas']
        horas_extras = data.get('horas_extras', 0)
        id_bono = data.get('id_bono')
        id_ceco = data.get('id_ceco')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar que la actividad pertenece al usuario y es una actividad múltiple
        cursor.execute("""
            SELECT id FROM tarja_fact_actividad 
            WHERE id = %s AND id_usuario = %s 
            AND id_tipotrabajador = 1 
            AND id_contratista IS NULL 
            AND id_tiporendimiento = 3
        """, (id_actividad, usuario_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad múltiple no encontrada o no tienes permiso para modificarla"}), 404

        # Verificar que el colaborador existe
        cursor.execute("""
            SELECT id FROM general_dim_colaborador 
            WHERE id = %s
        """, (id_colaborador,))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Colaborador no encontrado"}), 404

        # Verificar que no exista ya un rendimiento para esta actividad y colaborador
        cursor.execute("""
            SELECT id FROM tarja_fact_rendimientopropio 
            WHERE id_actividad = %s AND id_colaborador = %s
        """, (id_actividad, id_colaborador))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Ya existe un rendimiento para esta actividad y colaborador"}), 400

        # Generar ID único para el rendimiento
        cursor2 = conn.cursor()
        cursor2.execute("SELECT UUID()")
        id_rendimiento = cursor2.fetchone()[0]

        # Insertar el rendimiento
        cursor2.execute("""
            INSERT INTO tarja_fact_rendimientopropio (
                id, id_actividad, id_colaborador, rendimiento, 
                horas_trabajadas, horas_extras, id_bono, id_ceco
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_rendimiento,
            id_actividad,
            id_colaborador,
            rendimiento,
            horas_trabajadas,
            horas_extras,
            id_bono,
            id_ceco
        ))

        conn.commit()
        cursor.close()
        cursor2.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Rendimiento propio creado correctamente",
            "id_rendimiento": id_rendimiento
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para editar un rendimiento propio existente
@rendimiento_multiple_bp.route('/<string:rendimiento_id>', methods=['PUT'])
@jwt_required()
def editar_rendimiento(rendimiento_id):
    try:
        usuario_id = get_jwt_identity()
        data = request.json

        # Validar campos requeridos
        campos_requeridos = ['rendimiento', 'horas_trabajadas']
        for campo in campos_requeridos:
            if campo not in data or data[campo] in [None, '']:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400

        rendimiento = data['rendimiento']
        horas_trabajadas = data['horas_trabajadas']
        horas_extras = data.get('horas_extras', 0)
        id_bono = data.get('id_bono')
        id_ceco = data.get('id_ceco')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar que el rendimiento pertenece a una actividad del usuario
        cursor.execute("""
            SELECT r.id FROM tarja_fact_rendimientopropio r
            LEFT JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            WHERE r.id = %s AND a.id_usuario = %s
            AND a.id_tipotrabajador = 1 
            AND a.id_contratista IS NULL 
            AND a.id_tiporendimiento = 3
        """, (rendimiento_id, usuario_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Rendimiento no encontrado o no tienes permiso para editarlo"}), 404

        # Actualizar el rendimiento
        cursor.execute("""
            UPDATE tarja_fact_rendimientopropio 
            SET rendimiento = %s,
                horas_trabajadas = %s,
                horas_extras = %s,
                id_bono = %s,
                id_ceco = %s
            WHERE id = %s
        """, (rendimiento, horas_trabajadas, horas_extras, id_bono, id_ceco, rendimiento_id))

        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se pudo actualizar el rendimiento"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "Rendimiento propio actualizado correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar un rendimiento propio existente
@rendimiento_multiple_bp.route('/<string:rendimiento_id>', methods=['DELETE'])
@jwt_required()
def eliminar_rendimiento(rendimiento_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar que el rendimiento pertenece a una actividad del usuario
        cursor.execute("""
            SELECT r.id FROM tarja_fact_rendimientopropio r
            LEFT JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            WHERE r.id = %s AND a.id_usuario = %s
            AND a.id_tipotrabajador = 1 
            AND a.id_contratista IS NULL 
            AND a.id_tiporendimiento = 3
        """, (rendimiento_id, usuario_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Rendimiento no encontrado o no tienes permiso para eliminarlo"}), 404

        # Eliminar el rendimiento
        cursor.execute("""
            DELETE FROM tarja_fact_rendimientopropio 
            WHERE id = %s
        """, (rendimiento_id,))

        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se pudo eliminar el rendimiento"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "Rendimiento propio eliminado correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para obtener colaboradores disponibles (filtrados por sucursal)
@rendimiento_multiple_bp.route('/colaboradores', methods=['GET'])
@jwt_required()
def obtener_colaboradores():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró sucursal activa para el usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']

        # Obtener colaboradores de la sucursal
        cursor.execute("""
            SELECT 
                c.id,
                c.nombre,
                c.rut
            FROM general_dim_colaborador c
            WHERE c.id_sucursal = %s
            ORDER BY c.nombre ASC
        """, (id_sucursal,))

        colaboradores = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(colaboradores), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para obtener bonos disponibles
@rendimiento_multiple_bp.route('/bonos', methods=['GET'])
@jwt_required()
def obtener_bonos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener bonos disponibles
        cursor.execute("""
            SELECT 
                id,
                nombre,
                monto
            FROM general_dim_bono
            ORDER BY nombre ASC
        """)

        bonos = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(bonos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
