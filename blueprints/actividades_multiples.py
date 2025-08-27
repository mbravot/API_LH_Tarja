import datetime
from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta


actividades_multiples_bp = Blueprint('actividades_multiples_bp', __name__)

# 🚀 Endpoint para obtener actividades múltiples por sucursal
@actividades_multiples_bp.route('/sucursal/<string:id_sucursal>', methods=['GET'])
@jwt_required()
def obtener_actividades_multiples_por_sucursal(id_sucursal):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT 
                a.id, 
                a.fecha, 
                a.id_estadoactividad,
                a.id_labor,
                a.id_unidad,
                a.id_tipotrabajador,
                a.id_tiporendimiento,
                a.id_contratista,
                a.id_sucursalactiva,
                a.hora_inicio,
                a.hora_fin,
                a.tarifa,
                l.nombre AS labor, 
                tr.nombre AS tipo_rend,
                EXISTS (
                    SELECT 1 
                    FROM tarja_fact_rendimiento r 
                    WHERE r.id_actividad = a.id
                ) AS tiene_rendimiento
            FROM tarja_fact_actividad a
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN tarja_dim_tiporendimiento tr ON a.id_tiporendimiento = tr.id
            WHERE a.id_sucursalactiva = %s
            AND a.id_tipotrabajador = 1  -- Propio
            AND a.id_contratista IS NULL  -- Para propios
            AND a.id_tiporendimiento = 1  -- Individual
            AND (a.id_estadoactividad = 1 OR a.id_estadoactividad = 2)  -- 1: creada, 2: revisada
            GROUP BY a.id
            ORDER BY a.fecha DESC
        """

        cursor.execute(sql, (id_sucursal,))
        actividades = cursor.fetchall()

        for actividad in actividades:
            if 'fecha' in actividad and isinstance(actividad['fecha'], (date, datetime)):
                actividad['fecha'] = actividad['fecha'].strftime('%Y-%m-%d')

            if isinstance(actividad['hora_inicio'], timedelta):
                actividad['hora_inicio'] = str(actividad['hora_inicio'])
            if isinstance(actividad['hora_fin'], timedelta):
                actividad['hora_fin'] = str(actividad['hora_fin'])

        cursor.close()
        conn.close()

        return jsonify(actividades), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para obtener todas las actividades múltiples del usuario
@actividades_multiples_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_actividades_multiples():
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

        # Obtener actividades múltiples del usuario con valores fijos (solo CECOs productivos y riego)
        cursor.execute("""
            SELECT 
                a.*,
                l.nombre as nombre_labor,
                u.nombre as nombre_unidad,
                tt.nombre as nombre_tipotrabajador,
                tr.nombre as nombre_tiporendimiento,
                tc.nombre as nombre_tipoceco,
                ea.nombre as nombre_estado,
                s.nombre as nombre_sucursal,
                -- CECOs Productivos
                GROUP_CONCAT(DISTINCT CONCAT(cp.id_ceco, ':', ce.nombre) SEPARATOR '|') as cecos_productivos,
                -- CECOs de Riego
                GROUP_CONCAT(DISTINCT CONCAT(cr.id_ceco, ':', cer.nombre) SEPARATOR '|') as cecos_riego
            FROM tarja_fact_actividad a
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN tarja_dim_unidad u ON a.id_unidad = u.id
            LEFT JOIN general_dim_tipotrabajador tt ON a.id_tipotrabajador = tt.id
            LEFT JOIN tarja_dim_tiporendimiento tr ON a.id_tiporendimiento = tr.id
            LEFT JOIN general_dim_cecotipo tc ON a.id_tipoceco = tc.id
            LEFT JOIN tarja_dim_estadoactividad ea ON a.id_estadoactividad = ea.id
            LEFT JOIN general_dim_sucursal s ON a.id_sucursalactiva = s.id
            -- Joins para CECOs Productivos
            LEFT JOIN tarja_fact_cecoproductivo cp ON a.id = cp.id_actividad
            LEFT JOIN general_dim_ceco ce ON cp.id_ceco = ce.id
            -- Joins para CECOs de Riego
            LEFT JOIN tarja_fact_cecoriego cr ON a.id = cr.id_actividad
            LEFT JOIN general_dim_ceco cer ON cr.id_ceco = cer.id
            WHERE a.id_usuario = %s 
            AND a.id_sucursalactiva = %s 
            AND a.id_estadoactividad = 1
            AND a.id_tipotrabajador = 1  -- Propio
            AND a.id_contratista IS NULL  -- Para propios
            AND a.id_tiporendimiento = 1  -- Individual
            GROUP BY a.id
            ORDER BY l.nombre ASC, a.fecha DESC, a.hora_inicio DESC
        """, (usuario_id, id_sucursal))

        actividades = cursor.fetchall()
        cursor.close()
        conn.close()

        if not actividades:
            return jsonify([]), 200

        # Convertir timedelta a string para hora_inicio y hora_fin
        for actividad in actividades:
            if isinstance(actividad['hora_inicio'], timedelta):
                actividad['hora_inicio'] = str(actividad['hora_inicio'])
            if isinstance(actividad['hora_fin'], timedelta):
                actividad['hora_fin'] = str(actividad['hora_fin'])
            if isinstance(actividad['fecha'], (date, datetime)):
                actividad['fecha'] = actividad['fecha'].strftime('%Y-%m-%d')

            # Convertir los CECOs concatenados en arrays de objetos (solo productivos y riego)
            if actividad['cecos_productivos']:
                actividad['cecos_productivos'] = [
                    {'id': int(x.split(':')[0]), 'nombre': x.split(':')[1]} 
                    for x in actividad['cecos_productivos'].split('|')
                ]
            else:
                actividad['cecos_productivos'] = []

            if actividad['cecos_riego']:
                actividad['cecos_riego'] = [
                    {'id': int(x.split(':')[0]), 'nombre': x.split(':')[1]} 
                    for x in actividad['cecos_riego'].split('|')
                ]
            else:
                actividad['cecos_riego'] = []

            # Inicializar arrays vacíos para CECOs que no aplican en actividades múltiples
            actividad['cecos_inversion'] = []
            actividad['cecos_maquinaria'] = []
            actividad['cecos_administrativos'] = []

        return jsonify(actividades), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para crear una nueva actividad múltiple
@actividades_multiples_bp.route('/', methods=['POST'])
@jwt_required()
def crear_actividad_multiple():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        # Obtener sucursal activa del usuario
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró sucursal activa para el usuario"}), 400
        id_sucursalactiva = usuario['id_sucursalactiva']

        # Si no viene fecha, usar la fecha de hoy
        fecha = data.get('fecha')
        if not fecha or fecha in [None, '']:
            fecha = date.today().isoformat()

        # Validar campos requeridos (excluyendo los que son fijos)
        campos_requeridos = [
            'id_labor', 'id_unidad', 'id_tipoceco', 'tarifa', 
            'hora_inicio', 'hora_fin', 'id_estadoactividad'
        ]
        for campo in campos_requeridos:
            if campo not in data or data[campo] in [None, '']:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400

        # Validar que el tipo de CECO sea productivo (1) o riego (4)
        id_tipoceco = data.get('id_tipoceco')
        if id_tipoceco not in [1, 4]:  # 1: Productivo, 4: Riego
            return jsonify({"error": "Las actividades múltiples solo permiten CECOs de tipo productivo (1) o riego (4)"}), 400

        # Valores fijos para actividades múltiples
        id_tipotrabajador = 1  # Propio
        id_contratista = None  # Para propios
        id_tiporendimiento = 1  # Individual

        # Generar ID único para la actividad
        cursor2 = conn.cursor()
        cursor2.execute("SELECT UUID()")
        id_actividad = cursor2.fetchone()[0]

        # Insertar la actividad
        cursor2.execute("""
            INSERT INTO tarja_fact_actividad (
                id, fecha, id_usuario, id_sucursalactiva, id_tipotrabajador,
                id_contratista, id_tiporendimiento, id_labor, id_unidad,
                id_tipoceco, tarifa, hora_inicio, hora_fin, id_estadoactividad
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_actividad,
            fecha,
            usuario_id,
            id_sucursalactiva,
            id_tipotrabajador,
            id_contratista,
            id_tiporendimiento,
            data['id_labor'],
            data['id_unidad'],
            data['id_tipoceco'],
            data['tarifa'],
            data['hora_inicio'],
            data['hora_fin'],
            data['id_estadoactividad']
        ))
        conn.commit()
        cursor.close()
        cursor2.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Actividad múltiple creada correctamente",
            "id_actividad": id_actividad,
            "id_tipoceco": data['id_tipoceco']
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para editar una actividad múltiple existente
@actividades_multiples_bp.route('/<string:actividad_id>', methods=['PUT'])
@jwt_required()
def editar_actividad_multiple(actividad_id): 
    try:
        usuario_id = get_jwt_identity()
        data = request.json

        # Validar campos requeridos (excluyendo los que son fijos)
        campos_requeridos = [
            'fecha', 'id_labor', 'id_unidad', 'id_tipoceco', 
            'tarifa', 'hora_inicio', 'hora_fin', 'id_estadoactividad'
        ]
        for campo in campos_requeridos:
            if campo not in data or data[campo] in [None, '']:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400

        # Validar que el tipo de CECO sea productivo (1) o riego (4)
        id_tipoceco = data.get('id_tipoceco')
        if id_tipoceco not in [1, 4]:  # 1: Productivo, 4: Riego
            return jsonify({"error": "Las actividades múltiples solo permiten CECOs de tipo productivo (1) o riego (4)"}), 400

        fecha = data.get('fecha')
        id_labor = data.get('id_labor')
        id_unidad = data.get('id_unidad')
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        id_estadoactividad = data.get('id_estadoactividad')
        tarifa = data.get('tarifa')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar que la actividad pertenece al usuario y tiene los valores fijos correctos
        cursor.execute("""
            SELECT id FROM tarja_fact_actividad 
            WHERE id = %s AND id_usuario = %s 
            AND id_tipotrabajador = 1 
            AND id_contratista IS NULL 
            AND id_tiporendimiento = 1
        """, (actividad_id, usuario_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad múltiple no encontrada o no tienes permiso para editarla"}), 404

        sql = """
            UPDATE tarja_fact_actividad 
            SET fecha = %s,
                id_labor = %s,
                id_unidad = %s,
                hora_inicio = %s,
                hora_fin = %s,
                id_estadoactividad = %s,
                tarifa = %s,
                id_tipoceco = %s
            WHERE id = %s AND id_usuario = %s
            AND id_tipotrabajador = 1 
            AND id_contratista IS NULL 
            AND id_tiporendimiento = 1
        """
        valores = (fecha, id_labor, id_unidad, hora_inicio,
                  hora_fin, id_estadoactividad, tarifa, id_tipoceco, 
                  actividad_id, usuario_id)

        cursor.execute(sql, valores)
        conn.commit()

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se pudo actualizar la actividad múltiple"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "Actividad múltiple actualizada correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar una actividad múltiple existente
@actividades_multiples_bp.route('/<string:actividad_id>', methods=['DELETE'])
@jwt_required()
def eliminar_actividad_multiple(actividad_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Solo permitir eliminar si la actividad es del usuario y tiene los valores fijos correctos
        cursor.execute("""
            DELETE FROM tarja_fact_actividad 
            WHERE id = %s AND id_usuario = %s
            AND id_tipotrabajador = 1 
            AND id_contratista IS NULL 
            AND id_tiporendimiento = 1
        """, (actividad_id, usuario_id))
        
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad múltiple no encontrada o no tienes permiso para eliminarla"}), 404
        cursor.close()
        conn.close()
        return jsonify({"message": "Actividad múltiple eliminada correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
