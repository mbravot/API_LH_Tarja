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
            AND a.id_tiporendimiento = 3  -- MÚLTIPLE
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
            AND a.id_tiporendimiento = 3  -- MÚLTIPLE
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

        # Validar que el tipo de rendimiento sea múltiple (3)
        id_tiporendimiento = data.get('id_tiporendimiento')
        if id_tiporendimiento != 3:
            return jsonify({"error": "Las actividades múltiples deben tener id_tiporendimiento = 3"}), 400

        # Validar que el tipo de CECO sea productivo (2) o riego (5)
        id_tipoceco = data.get('id_tipoceco')
        if id_tipoceco not in [2, 5]:  # 2: Productivo, 5: Riego
            return jsonify({"error": "Las actividades múltiples solo permiten CECOs de tipo productivo (2) o riego (5)"}), 400

        # Validar que la unidad sea horas base (36) u horas trato (4)
        id_unidad = data.get('id_unidad')
        if id_unidad not in [36, 4]:  # 36: Horas base, 4: Horas trato
            return jsonify({"error": "Las actividades múltiples solo permiten unidades: horas base (36) u horas trato (4)"}), 400

        # Valores fijos para actividades múltiples
        id_tipotrabajador = 1  # Propio
        id_contratista = None  # Para propios

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
            data['id_tiporendimiento'],
            data['id_labor'],
            data['id_unidad'],
            data['id_tipoceco'],
            data['tarifa'],
            data['hora_inicio'],
            data['hora_fin'],
            data['id_estadoactividad']
        ))

        # Insertar el estado inicial en tarja_pivot_actividadestado
        cursor2.execute("SELECT UUID()")
        id_estado = cursor2.fetchone()[0]
        
        cursor2.execute("""
            INSERT INTO tarja_pivot_actividadestado (
                id, id_actividad, id_estadoactividad, fecha_hora
            ) VALUES (%s, %s, %s, CONVERT_TZ(NOW(), '+00:00', '-03:00'))
        """, (id_estado, id_actividad, 1))  # 1 = Estado "Creada"
        
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

        # Para actividades múltiples, el tipo de rendimiento siempre es 3 (MÚLTIPLE)
        id_tiporendimiento = 3

        # Obtener el tipo de CECO de los datos (se mantiene el original)
        id_tipoceco = data.get('id_tipoceco')

        # Obtener la unidad de los datos (se mantiene la original)
        id_unidad = data.get('id_unidad')

        fecha = data.get('fecha')
        id_labor = data.get('id_labor')
        id_unidad = data.get('id_unidad')
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        id_estadoactividad = data.get('id_estadoactividad')
        tarifa = data.get('tarifa')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar que la actividad pertenece al usuario y es una actividad múltiple
        cursor.execute("""
            SELECT id FROM tarja_fact_actividad 
            WHERE id = %s AND id_usuario = %s 
            AND id_tipotrabajador = 1 
            AND id_contratista IS NULL 
            AND id_tiporendimiento = 3
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
            AND id_tiporendimiento = 3
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
        
        # Verificar que la actividad existe y pertenece al usuario
        cursor.execute("""
            SELECT id FROM tarja_fact_actividad 
            WHERE id = %s AND id_usuario = %s
            AND id_tipotrabajador = 1 
            AND id_contratista IS NULL 
            AND id_tiporendimiento = 3
        """, (actividad_id, usuario_id))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad múltiple no encontrada o no tienes permiso para eliminarla"}), 404
        
        # Eliminar registros relacionados primero
        # Eliminar estados de actividad
        cursor.execute("DELETE FROM tarja_pivot_actividadestado WHERE id_actividad = %s", (actividad_id,))
        
        # Eliminar CECOs de riego (se eliminan automáticamente por CASCADE, pero por seguridad)
        cursor.execute("DELETE FROM tarja_fact_cecoriego WHERE id_actividad = %s", (actividad_id,))
        
        # Eliminar CECOs productivos (se eliminan automáticamente por CASCADE, pero por seguridad)
        cursor.execute("DELETE FROM tarja_fact_cecoproductivo WHERE id_actividad = %s", (actividad_id,))
        
        # Finalmente eliminar la actividad
        cursor.execute("DELETE FROM tarja_fact_actividad WHERE id = %s", (actividad_id,))
        
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

# 🚀 Endpoint para crear un registro de CECO de riego para actividades múltiples
@actividades_multiples_bp.route('/ceco-riego', methods=['POST'])
@jwt_required()
def crear_ceco_riego():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        # Validar campos requeridos
        campos_requeridos = ['id_actividad', 'id_sectorriego']
        for campo in campos_requeridos:
            if campo not in data or data[campo] in [None, '']:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400

        id_actividad = data['id_actividad']
        id_sectorriego = data['id_sectorriego']

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

        # Obtener información del sector de riego para autocompletar campos
        cursor.execute("""
            SELECT 
                s.id_ceco,
                s.id_equipo,
                e.id_caseta
            FROM riego_dim_sector s
            LEFT JOIN riego_dim_equipo e ON s.id_equipo = e.id
            WHERE s.id = %s
        """, (id_sectorriego,))
        
        sector_info = cursor.fetchone()
        if not sector_info:
            cursor.close()
            conn.close()
            return jsonify({"error": "Sector de riego no encontrado"}), 404

        # Verificar que el CECO del sector sea de tipo riego (5)
        cursor.execute("""
            SELECT id FROM general_dim_ceco 
            WHERE id = %s
        """, (sector_info['id_ceco'],))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "El CECO del sector no es de tipo riego"}), 400

        # Verificar que no exista ya un registro para esta actividad y sector
        cursor.execute("""
            SELECT id FROM tarja_fact_cecoriego 
            WHERE id_actividad = %s AND id_sectorriego = %s
        """, (id_actividad, id_sectorriego))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Ya existe un registro de CECO de riego para esta actividad y sector"}), 400

        # Insertar el registro de CECO de riego
        cursor.execute("""
            INSERT INTO tarja_fact_cecoriego (
                id_actividad, id_caseta, id_equiporiego, id_sectorriego, id_ceco
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            id_actividad,
            sector_info['id_caseta'],
            sector_info['id_equipo'],
            id_sectorriego,
            sector_info['id_ceco']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "CECO de riego registrado correctamente",
            "data": {
                "id_actividad": id_actividad,
                "id_sectorriego": id_sectorriego,
                "id_equiporiego": sector_info['id_equipo'],
                "id_caseta": sector_info['id_caseta'],
                "id_ceco": sector_info['id_ceco']
            }
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para obtener sectores de riego disponibles
@actividades_multiples_bp.route('/sectores-riego', methods=['GET'])
@jwt_required()
def obtener_sectores_riego():
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

        # Obtener sectores de riego con información completa filtrados por sucursal
        cursor.execute("""
            SELECT 
                s.id as id_sectorriego,
                s.nombre as nombre_sector,
                s.id_ceco,
                c.nombre as nombre_ceco,
                s.id_equipo,
                e.nombre as nombre_equipo,
                e.id_caseta,
                ca.nombre as nombre_caseta
            FROM riego_dim_sector s
            LEFT JOIN general_dim_ceco c ON s.id_ceco = c.id
            LEFT JOIN riego_dim_equipo e ON s.id_equipo = e.id
            LEFT JOIN general_dim_maquinaria ca ON e.id_caseta = ca.id
            WHERE c.id_sucursal = %s AND c.id_estado = 1
            ORDER BY s.nombre ASC
        """, (id_sucursal,))

        sectores = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(sectores), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar un registro de CECO de riego
@actividades_multiples_bp.route('/ceco-riego/<string:id_actividad>/<string:id_sectorriego>', methods=['DELETE'])
@jwt_required()
def eliminar_ceco_riego(id_actividad, id_sectorriego):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor()

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

        # Eliminar el registro de CECO de riego
        cursor.execute("""
            DELETE FROM tarja_fact_cecoriego 
            WHERE id_actividad = %s AND id_sectorriego = %s
        """, (id_actividad, id_sectorriego))

        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Registro de CECO de riego no encontrado"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "CECO de riego eliminado correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para crear un registro de CECO productivo para actividades múltiples
@actividades_multiples_bp.route('/ceco-productivo', methods=['POST'])
@jwt_required()
def crear_ceco_productivo():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        # Validar campos requeridos
        campos_requeridos = ['id_actividad', 'id_cuartel']
        for campo in campos_requeridos:
            if campo not in data or data[campo] in [None, '']:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400

        id_actividad = data['id_actividad']
        id_cuartel = data['id_cuartel']

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

        # Obtener información del cuartel para autocompletar campos
        cursor.execute("""
            SELECT 
                c.id_ceco,
                v.id_especie,
                c.id_variedad
            FROM general_dim_cuartel c
            LEFT JOIN general_dim_variedad v ON c.id_variedad = v.id
            WHERE c.id = %s
        """, (id_cuartel,))
        
        cuartel_info = cursor.fetchone()
        if not cuartel_info:
            cursor.close()
            conn.close()
            return jsonify({"error": "Cuartel no encontrado"}), 404

        # Verificar que el CECO del cuartel sea de tipo productivo (2)
        cursor.execute("""
            SELECT id FROM general_dim_ceco 
            WHERE id = %s
        """, (cuartel_info['id_ceco'],))
        
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "El CECO del cuartel no es de tipo productivo"}), 400

        # Verificar que no exista ya un registro para esta actividad y cuartel
        cursor.execute("""
            SELECT id FROM tarja_fact_cecoproductivo 
            WHERE id_actividad = %s AND id_cuartel = %s
        """, (id_actividad, id_cuartel))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Ya existe un registro de CECO productivo para esta actividad y cuartel"}), 400

        # Insertar el registro de CECO productivo
        cursor.execute("""
            INSERT INTO tarja_fact_cecoproductivo (
                id_actividad, id_especie, id_variedad, id_cuartel, id_ceco
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            id_actividad,
            cuartel_info['id_especie'],
            cuartel_info['id_variedad'],
            id_cuartel,
            cuartel_info['id_ceco']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "CECO productivo registrado correctamente",
            "data": {
                "id_actividad": id_actividad,
                "id_cuartel": id_cuartel,
                "id_especie": cuartel_info['id_especie'],
                "id_variedad": cuartel_info['id_variedad'],
                "id_ceco": cuartel_info['id_ceco']
            }
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para obtener cuarteles productivos disponibles
@actividades_multiples_bp.route('/cuarteles-productivos', methods=['GET'])
@jwt_required()
def obtener_cuarteles_productivos():
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

        # Obtener cuarteles productivos con información completa filtrados por sucursal
        cursor.execute("""
            SELECT 
                c.id as id_cuartel,
                c.nombre as nombre_cuartel,
                c.id_ceco,
                ce.nombre as nombre_ceco,
                v.id_especie,
                e.nombre as nombre_especie,
                c.id_variedad,
                v.nombre as nombre_variedad
            FROM general_dim_cuartel c
            LEFT JOIN general_dim_ceco ce ON c.id_ceco = ce.id
            LEFT JOIN general_dim_variedad v ON c.id_variedad = v.id
            LEFT JOIN general_dim_especie e ON v.id_especie = e.id
            WHERE ce.id_sucursal = %s AND ce.id_estado = 1
            -- WHERE ce.id_tipoceco = 2  -- Solo CECOs de tipo productivo (comentado temporalmente)
            ORDER BY c.nombre ASC
        """, (id_sucursal,))

        cuarteles = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(cuarteles), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar un registro de CECO productivo
@actividades_multiples_bp.route('/ceco-productivo/<string:id_actividad>/<int:id_cuartel>', methods=['DELETE'])
@jwt_required()
def eliminar_ceco_productivo(id_actividad, id_cuartel):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor()

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

        # Eliminar el registro de CECO productivo
        cursor.execute("""
            DELETE FROM tarja_fact_cecoproductivo 
            WHERE id_actividad = %s AND id_cuartel = %s
        """, (id_actividad, id_cuartel))

        conn.commit()
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Registro de CECO productivo no encontrado"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "CECO productivo eliminado correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para crear múltiples registros de CECO productivo (selección múltiple de cuarteles)
@actividades_multiples_bp.route('/ceco-productivo-multiple', methods=['POST'])
@jwt_required()
def crear_ceco_productivo_multiple():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        # Validar campos requeridos
        campos_requeridos = ['id_actividad', 'id_cuarteles']
        for campo in campos_requeridos:
            if campo not in data or data[campo] in [None, '']:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400

        id_actividad = data['id_actividad']
        id_cuarteles = data['id_cuarteles']

        # Validar que id_cuarteles sea una lista
        if not isinstance(id_cuarteles, list) or len(id_cuarteles) == 0:
            return jsonify({"error": "id_cuarteles debe ser una lista no vacía"}), 400

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

        registros_creados = []
        registros_existentes = []

        for id_cuartel in id_cuarteles:
            # Obtener información del cuartel
            cursor.execute("""
                SELECT 
                    c.id_ceco,
                    v.id_especie,
                    c.id_variedad
                FROM general_dim_cuartel c
                LEFT JOIN general_dim_variedad v ON c.id_variedad = v.id
                WHERE c.id = %s
            """, (id_cuartel,))
            
            cuartel_info = cursor.fetchone()
            if not cuartel_info:
                continue

            # Verificar que el CECO sea de tipo productivo
            cursor.execute("""
                SELECT id FROM general_dim_ceco 
                WHERE id = %s
            """, (cuartel_info['id_ceco'],))
            
            if not cursor.fetchone():
                continue

            # Verificar si ya existe el registro
            cursor.execute("""
                SELECT id FROM tarja_fact_cecoproductivo 
                WHERE id_actividad = %s AND id_cuartel = %s
            """, (id_actividad, id_cuartel))
            
            if cursor.fetchone():
                registros_existentes.append(id_cuartel)
                continue

            # Insertar el registro
            cursor.execute("""
                INSERT INTO tarja_fact_cecoproductivo (
                    id_actividad, id_especie, id_variedad, id_cuartel, id_ceco
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                id_actividad,
                cuartel_info['id_especie'],
                cuartel_info['id_variedad'],
                id_cuartel,
                cuartel_info['id_ceco']
            ))

            registros_creados.append({
                "id_cuartel": id_cuartel,
                "id_especie": cuartel_info['id_especie'],
                "id_variedad": cuartel_info['id_variedad'],
                "id_ceco": cuartel_info['id_ceco']
            })

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Se crearon {len(registros_creados)} registros de CECO productivo",
            "registros_creados": registros_creados,
            "registros_existentes": registros_existentes,
            "total_creados": len(registros_creados),
            "total_existentes": len(registros_existentes)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para crear múltiples registros de CECO de riego (selección múltiple de sectores)
@actividades_multiples_bp.route('/ceco-riego-multiple', methods=['POST'])
@jwt_required()
def crear_ceco_riego_multiple():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        # Validar campos requeridos
        campos_requeridos = ['id_actividad', 'id_sectoresriego']
        for campo in campos_requeridos:
            if campo not in data or data[campo] in [None, '']:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400

        id_actividad = data['id_actividad']
        id_sectoresriego = data['id_sectoresriego']

        # Validar que id_sectoresriego sea una lista
        if not isinstance(id_sectoresriego, list) or len(id_sectoresriego) == 0:
            return jsonify({"error": "id_sectoresriego debe ser una lista no vacía"}), 400

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

        registros_creados = []
        registros_existentes = []

        for id_sectorriego in id_sectoresriego:
            # Obtener información del sector de riego
            cursor.execute("""
                SELECT 
                    s.id_ceco,
                    s.id_equipo,
                    e.id_caseta
                FROM riego_dim_sector s
                LEFT JOIN riego_dim_equipo e ON s.id_equipo = e.id
                WHERE s.id = %s
            """, (id_sectorriego,))
            
            sector_info = cursor.fetchone()
            if not sector_info:
                continue

            # Verificar que el CECO sea de tipo riego
            cursor.execute("""
                SELECT id FROM general_dim_ceco 
                WHERE id = %s
            """, (sector_info['id_ceco'],))
            
            if not cursor.fetchone():
                continue

            # Verificar si ya existe el registro
            cursor.execute("""
                SELECT id FROM tarja_fact_cecoriego 
                WHERE id_actividad = %s AND id_sectorriego = %s
            """, (id_actividad, id_sectorriego))
            
            if cursor.fetchone():
                registros_existentes.append(id_sectorriego)
                continue

            # Insertar el registro
            cursor.execute("""
                INSERT INTO tarja_fact_cecoriego (
                    id_actividad, id_caseta, id_equiporiego, id_sectorriego, id_ceco
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                id_actividad,
                sector_info['id_caseta'],
                sector_info['id_equipo'],
                id_sectorriego,
                sector_info['id_ceco']
            ))

            registros_creados.append({
                "id_sectorriego": id_sectorriego,
                "id_equiporiego": sector_info['id_equipo'],
                "id_caseta": sector_info['id_caseta'],
                "id_ceco": sector_info['id_ceco']
            })

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Se crearon {len(registros_creados)} registros de CECO de riego",
            "registros_creados": registros_creados,
            "registros_existentes": registros_existentes,
            "total_creados": len(registros_creados),
            "total_existentes": len(registros_existentes)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint unificado para obtener actividades múltiples con todos los CECOs
@actividades_multiples_bp.route('/con-cecos', methods=['GET'])
@jwt_required()
def obtener_actividades_multiples_con_cecos():
    """
    Endpoint unificado que trae todas las actividades múltiples con todos sus CECOs
    en una sola llamada para optimizar el rendimiento del frontend
    """
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

        # Consulta optimizada para obtener todas las actividades múltiples con todos sus CECOs
        cursor.execute("""
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
                l.nombre as nombre_labor,
                u.nombre as nombre_unidad,
                tt.nombre as nombre_tipotrabajador,
                tr.nombre as nombre_tiporendimiento,
                tc.nombre as nombre_tipoceco,
                ea.nombre as nombre_estado,
                s.nombre as nombre_sucursal,
                -- Verificar si tiene rendimientos múltiples
                EXISTS (
                    SELECT 1 
                    FROM tarja_fact_rendimientopropio r 
                    WHERE r.id_actividad = a.id
                ) as tiene_rendimientos_multiples
            FROM tarja_fact_actividad a
            LEFT JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN tarja_dim_unidad u ON a.id_unidad = u.id
            LEFT JOIN general_dim_tipotrabajador tt ON a.id_tipotrabajador = tt.id
            LEFT JOIN tarja_dim_tiporendimiento tr ON a.id_tiporendimiento = tr.id
            LEFT JOIN general_dim_cecotipo tc ON a.id_tipoceco = tc.id
            LEFT JOIN tarja_dim_estadoactividad ea ON a.id_estadoactividad = ea.id
            LEFT JOIN general_dim_sucursal s ON a.id_sucursalactiva = s.id
            WHERE a.id_usuario = %s 
            AND a.id_sucursalactiva = %s 
            AND a.id_tiporendimiento = 3  -- MÚLTIPLE
            AND (a.id_estadoactividad = 1 OR a.id_estadoactividad = 2)  -- 1: creada, 2: revisada
            ORDER BY a.fecha DESC
        """, (usuario_id, id_sucursal))

        actividades = cursor.fetchall()
        
        # Para cada actividad, obtener todos sus CECOs
        resultado = []
        for actividad in actividades:
            actividad_id = actividad['id']
            
            # Obtener CECOs productivos
            cursor.execute("""
                SELECT 
                    cp.id_ceco,
                    c.nombre as nombre_ceco,
                    cp.id_cuartel,
                    cu.nombre as nombre_cuartel
                FROM tarja_fact_cecoproductivo cp
                LEFT JOIN general_dim_ceco c ON cp.id_ceco = c.id
                LEFT JOIN general_dim_cuartel cu ON cp.id_cuartel = cu.id
                WHERE cp.id_actividad = %s
            """, (actividad_id,))
            cecos_productivos = cursor.fetchall()
            
            # Obtener CECOs de riego
            cursor.execute("""
                SELECT 
                    cr.id_ceco,
                    c.nombre as nombre_ceco,
                    cr.id_sectorriego,
                    sr.nombre as nombre_sector
                FROM tarja_fact_cecoriego cr
                LEFT JOIN general_dim_ceco c ON cr.id_ceco = c.id
                LEFT JOIN riego_dim_sector sr ON cr.id_sectorriego = sr.id
                WHERE cr.id_actividad = %s
            """, (actividad_id,))
            cecos_riego = cursor.fetchall()
            
            # Obtener CECOs de maquinaria
            cursor.execute("""
                SELECT 
                    cm.id_ceco,
                    c.nombre as nombre_ceco,
                    cm.id_maquinaria,
                    m.nombre as nombre_maquinaria
                FROM tarja_fact_cecomaquinaria cm
                LEFT JOIN general_dim_ceco c ON cm.id_ceco = c.id
                LEFT JOIN maquinaria_dim_maquinaria m ON cm.id_maquinaria = m.id
                WHERE cm.id_actividad = %s
            """, (actividad_id,))
            cecos_maquinaria = cursor.fetchall()
            
            # Obtener CECOs de inversión
            cursor.execute("""
                SELECT 
                    ci.id_ceco,
                    c.nombre as nombre_ceco,
                    ci.id_proyecto,
                    p.nombre as nombre_proyecto
                FROM tarja_fact_cecoinversion ci
                LEFT JOIN general_dim_ceco c ON ci.id_ceco = c.id
                LEFT JOIN inversion_dim_proyecto p ON ci.id_proyecto = p.id
                WHERE ci.id_actividad = %s
            """, (actividad_id,))
            cecos_inversion = cursor.fetchall()
            
            # Obtener CECOs administrativos
            cursor.execute("""
                SELECT 
                    ca.id_ceco,
                    c.nombre as nombre_ceco,
                    ca.id_departamento,
                    d.nombre as nombre_departamento
                FROM tarja_fact_cecoadministrativo ca
                LEFT JOIN general_dim_ceco c ON ca.id_ceco = c.id
                LEFT JOIN administrativo_dim_departamento d ON ca.id_departamento = d.id
                WHERE ca.id_actividad = %s
            """, (actividad_id,))
            cecos_administrativos = cursor.fetchall()
            
            # Obtener rendimientos múltiples (rendimientos ya registrados)
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
                    CONCAT(c.nombre, ' ', c.apellido_paterno, ' ', COALESCE(c.apellido_materno, '')) as nombre_colaborador,
                    CONCAT(c.rut, '-', c.codigo_verificador) as rut_colaborador,
                    b.nombre as nombre_bono,
                    COALESCE(ce.nombre, 'Sin nombre') as nombre_ceco
                FROM tarja_fact_rendimientopropio r
                LEFT JOIN general_dim_colaborador c ON r.id_colaborador = c.id
                LEFT JOIN general_dim_bono b ON r.id_bono = b.id
                LEFT JOIN general_dim_ceco ce ON r.id_ceco = ce.id
                WHERE r.id_actividad = %s
                ORDER BY c.nombre ASC, c.apellido_paterno ASC, c.apellido_materno ASC
            """, (actividad_id,))
            rendimientos_multiples = cursor.fetchall()
            
            # Obtener CECOs disponibles para rendimientos (combinando riego y productivos)
            cursor.execute("""
                SELECT 
                    c.id as id_ceco,
                    COALESCE(c.nombre, 'Sin nombre') as nombre_ceco,
                    'riego' as tipo_ceco
                FROM tarja_fact_cecoriego tcr
                LEFT JOIN general_dim_ceco c ON tcr.id_ceco = c.id
                WHERE tcr.id_actividad = %s
                ORDER BY c.nombre ASC
            """, (actividad_id,))
            cecos_riego_disponibles = cursor.fetchall()
            
            cursor.execute("""
                SELECT 
                    c.id as id_ceco,
                    COALESCE(c.nombre, 'Sin nombre') as nombre_ceco,
                    'productivo' as tipo_ceco
                FROM tarja_fact_cecoproductivo tcp
                LEFT JOIN general_dim_ceco c ON tcp.id_ceco = c.id
                WHERE tcp.id_actividad = %s
                ORDER BY c.nombre ASC
            """, (actividad_id,))
            cecos_productivos_disponibles = cursor.fetchall()
            
            # Combinar CECOs disponibles para rendimientos
            cecos_disponibles_rendimientos = cecos_riego_disponibles + cecos_productivos_disponibles
            
            # Construir el objeto de respuesta
            actividad_completa = {
                "id": actividad['id'],
                "nombre_labor": actividad['nombre_labor'],
                "fecha": actividad['fecha'].strftime('%Y-%m-%d') if actividad['fecha'] else None,
                "cecos_productivos": cecos_productivos,
                "cecos_riego": cecos_riego,
                "cecos_maquinaria": cecos_maquinaria,
                "cecos_inversion": cecos_inversion,
                "cecos_administrativos": cecos_administrativos,
                "rendimientos_multiples": rendimientos_multiples,
                "tiene_rendimientos_multiples": actividad['tiene_rendimientos_multiples'],
                # Datos específicos que el frontend necesita para evitar llamadas adicionales
                "cecos_disponibles_rendimientos": cecos_disponibles_rendimientos,
                "rendimientos_existentes": rendimientos_multiples  # Alias para compatibilidad
            }
            
            resultado.append(actividad_completa)

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": resultado,
            "count": len(resultado),
            "message": f"Se obtuvieron {len(resultado)} actividades múltiples con todos sus CECOs"
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500