import datetime
from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from flask_cors import cross_origin
import uuid


rendimientos_bp = Blueprint('rendimientos_bp', __name__)

# 🚀 Endpoint para obtener rendimientos según el tipo de la actividad
@rendimientos_bp.route('/<string:id_actividad>', methods=['GET'])
@cross_origin()
def obtener_rendimientos(id_actividad):
    if id_actividad is None or id_actividad.lower() == 'null' or id_actividad.strip() == '':
        return jsonify({"error": "El parámetro id_actividad es inválido o no fue proporcionado"}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_tiporendimiento, id_tipotrabajador FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad no encontrada"}), 404
        tipo = actividad['id_tiporendimiento']
        tipo_trabajador = actividad['id_tipotrabajador']
        rendimientos = []
        if tipo == 1:  # Individual
            if tipo_trabajador == 1:  # Propio
                cursor.execute("""
                    SELECT r.*, l.nombre AS labor, c.nombre AS colaborador, b.nombre AS bono
                    FROM tarja_fact_rendimientopropio r
                    LEFT JOIN tarja_fact_actividad a ON r.id_actividad = a.id
                    LEFT JOIN general_dim_labor l ON a.id_labor = l.id
                    LEFT JOIN general_dim_colaborador c ON r.id_colaborador = c.id
                    LEFT JOIN general_dim_bono b ON r.id_bono = b.id
                    WHERE r.id_actividad = %s
                """, (id_actividad,))
                rendimientos = cursor.fetchall()
            elif tipo_trabajador == 2:  # Contratista
                cursor.execute("""
                    SELECT r.*, l.nombre AS labor, t.nombre AS trabajador, p.porcentaje AS porcentaje_trabajador
                    FROM tarja_fact_rendimientocontratista r
                    LEFT JOIN tarja_fact_actividad a ON r.id_actividad = a.id
                    LEFT JOIN general_dim_labor l ON a.id_labor = l.id
                    LEFT JOIN general_dim_trabajador t ON r.id_trabajador = t.id
                    LEFT JOIN general_dim_porcentajecontratista p ON r.id_porcentaje_individual = p.id
                    WHERE r.id_actividad = %s
                """, (id_actividad,))
                rendimientos = cursor.fetchall()
        elif tipo == 2:  # Grupal
            cursor.execute("""
                SELECT rg.*, a.id_labor, l.nombre AS labor
                FROM tarja_fact_redimientogrupal rg
                LEFT JOIN tarja_fact_actividad a ON rg.id_actividad = a.id
                LEFT JOIN general_dim_labor l ON a.id_labor = l.id
                WHERE rg.id_actividad = %s
            """, (id_actividad,))
            rendimientos = cursor.fetchall()
        cursor.close()
        conn.close()
        if not rendimientos:
            return jsonify({"rendimientos": []}), 200
        return jsonify({"rendimientos": rendimientos}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para crear rendimientos según el tipo de la actividad
@rendimientos_bp.route('/', methods=['POST'])
@jwt_required()
def crear_rendimiento():
    try:
        data = request.json
        if not isinstance(data, list):
            return jsonify({"error": "Se esperaba una lista de rendimientos"}), 400
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
        id_actividad = data[0].get('id_actividad')
        if not id_actividad:
            return jsonify({"error": "Falta id_actividad"}), 400
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Consultar el tipo de trabajador de la actividad
        cursor.execute("SELECT id_tipotrabajador FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad_tipo = cursor.fetchone()
        if not actividad_tipo:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se pudo determinar el tipo de trabajador de la actividad"}), 400
        tipo_trabajador = actividad_tipo['id_tipotrabajador']
        # Consultar el tipo de rendimiento de la actividad
        cursor.execute("SELECT id_tiporendimiento FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad no encontrada"}), 404
        tipo = actividad['id_tiporendimiento']
        ids_insertados = []
        if tipo == 1:  # Individual
            sql = """
                INSERT INTO tarja_fact_rendimientopropio (
                    id, id_actividad, id_colaborador,
                    rendimiento, horas_trabajadas, horas_extras,
                    id_bono, id_porcentaje_individual
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            for rendimiento in data:
                nuevo_id = str(uuid.uuid4())
                # Validación según tipo de trabajador
                if tipo_trabajador == 1:
                    if not rendimiento.get('id_colaborador'):
                        return jsonify({"error": "Falta id_colaborador para trabajador propio"}), 400
                    valores = (
                        nuevo_id,
                        rendimiento.get('id_actividad'),
                        rendimiento.get('id_colaborador'),
                        float(rendimiento.get('rendimiento', 0)),
                        float(rendimiento.get('horas_trabajadas', 0)),
                        float(rendimiento.get('horas_extras', 0)),
                        rendimiento.get('id_bono'),
                        rendimiento.get('id_porcentaje_individual')
                    )
                elif tipo_trabajador == 2:
                    if not rendimiento.get('id_trabajador'):
                        return jsonify({"error": "Falta id_trabajador para trabajador contratista"}), 400
                    valores = (
                        nuevo_id,
                        rendimiento.get('id_actividad'),
                        rendimiento.get('id_trabajador'),
                        float(rendimiento.get('rendimiento', 0)),
                        float(rendimiento.get('horas_trabajadas', 0)),
                        float(rendimiento.get('horas_extras', 0)),
                        rendimiento.get('id_bono'),
                        rendimiento.get('id_porcentaje_individual')
                    )
                else:
                    return jsonify({"error": "Tipo de trabajador no soportado"}), 400
                cursor.execute(sql, valores)
                ids_insertados.append(nuevo_id)
        elif tipo == 2:  # Grupal
            sql = """
                INSERT INTO tarja_fact_redimientogrupal (
                    id, id_actividad, rendimiento_total, cantidad_trab, id_porcentaje
                ) VALUES (%s, %s, %s, %s, %s)
            """
            for rendimiento in data:
                nuevo_id = str(uuid.uuid4())
                valores = (
                    nuevo_id,
                    rendimiento.get('id_actividad'),
                    float(rendimiento.get('rendimiento_total', 0)),
                    float(rendimiento.get('cantidad_trab', 0)),
                    rendimiento.get('id_porcentaje')
                )
                cursor.execute(sql, valores)
                ids_insertados.append(nuevo_id)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimientos creados correctamente", "ids": ids_insertados}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para editar un rendimiento existente según el tipo de la actividad
@rendimientos_bp.route('/<string:rendimiento_id>', methods=['PUT'])
@jwt_required()
def editar_rendimiento(rendimiento_id):
    try:
        data = request.json
        id_actividad = data.get('id_actividad')
        if not id_actividad:
            return jsonify({"error": "Falta id_actividad"}), 400
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Consultar el tipo de rendimiento de la actividad
        cursor.execute("SELECT id_tiporendimiento FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
        actividad = cursor.fetchone()
        if not actividad:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad no encontrada"}), 404
        tipo = actividad['id_tiporendimiento']
        if tipo == 1:  # Individual
            sql = """
                UPDATE tarja_fact_rendimientopropio 
                SET id_trabajador = %s,
                    id_colaborador = %s,
                    rendimiento = %s,
                    horas_trabajadas = %s,
                    horas_extras = %s,
                    id_bono = %s,
                    id_porcentaje_individual = %s
                WHERE id = %s
            """
            # Consultar el tipo de trabajador de la actividad
            cursor.execute("SELECT id_tipotrabajador FROM tarja_fact_actividad WHERE id = %s", (id_actividad,))
            actividad_tipo = cursor.fetchone()
            if not actividad_tipo:
                cursor.close()
                conn.close()
                return jsonify({"error": "No se pudo determinar el tipo de trabajador de la actividad"}), 400
            tipo_trabajador = actividad_tipo['id_tipotrabajador']
            # Validación según tipo de trabajador
            if tipo_trabajador == 1:
                # Propio: solo id_colaborador, id_trabajador debe ser None
                if not data.get('id_colaborador'):
                    return jsonify({"error": "Falta id_colaborador para trabajador propio"}), 400
                valores = (
                    None,  # id_trabajador
                    data.get('id_colaborador'),
                    float(data.get('rendimiento', 0)),
                    float(data.get('horas_trabajadas', 0)),
                    float(data.get('horas_extras', 0)),
                    data.get('id_bono'),
                    data.get('id_porcentaje_individual'),
                    rendimiento_id
                )
            elif tipo_trabajador == 2:
                # Contratista: solo id_trabajador, id_colaborador debe ser None
                if not data.get('id_trabajador'):
                    return jsonify({"error": "Falta id_trabajador para trabajador contratista"}), 400
                valores = (
                    data.get('id_trabajador'),
                    None,  # id_colaborador
                    float(data.get('rendimiento', 0)),
                    float(data.get('horas_trabajadas', 0)),
                    float(data.get('horas_extras', 0)),
                    data.get('id_bono'),
                    data.get('id_porcentaje_individual'),
                    rendimiento_id
                )
            else:
                return jsonify({"error": "Tipo de trabajador no soportado"}), 400
            cursor.execute(sql, valores)
        elif tipo == 2:  # Grupal
            sql = """
                UPDATE tarja_fact_redimientogrupal 
                SET rendimiento_total = %s,
                    cantidad_trab = %s,
                    id_porcentaje = %s
                WHERE id = %s
            """
            valores = (
                float(data.get('rendimiento_total', 0)),
                float(data.get('cantidad_trab', 0)),
                data.get('id_porcentaje'),
                rendimiento_id
            )
            cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@rendimientos_bp.route('/grupal', methods=['POST'])
@jwt_required()
def crear_rendimiento_grupal():
    conn = None
    cursor = None
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Consultar sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({'error': 'No se encontró la sucursal activa del usuario'}), 400
        id_sucursal = usuario['id_sucursalactiva']
        # Obtener datos del request
        data = request.get_json()
        campos_requeridos = ['id_actividad', 'rendimiento_total', 'cantidad_trab', 'id_porcentaje']
        for campo in campos_requeridos:
            if campo not in data:
                return jsonify({'error': f'El campo {campo} es requerido'}), 400
        # Validar que la actividad exista y pertenezca a la sucursal del usuario
        cursor.execute("""
            SELECT id FROM tarja_fact_actividad 
            WHERE id = %s AND id_sucursalactiva = %s AND id_estadoactividad = 1
        """, (data['id_actividad'], id_sucursal))
        actividad = cursor.fetchone()
        if not actividad:
            return jsonify({'error': 'Actividad no encontrada o no pertenece a tu sucursal'}), 404
        # Validar que el porcentaje exista
        cursor.execute("""
            SELECT id FROM general_dim_porcentajecontratista 
            WHERE id = %s
        """, (data['id_porcentaje'],))
        porcentaje = cursor.fetchone()
        if not porcentaje:
            return jsonify({'error': 'Porcentaje no encontrado'}), 404
        # Insertar rendimiento grupal
        nuevo_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO tarja_fact_redimientogrupal 
            (id, id_actividad, rendimiento_total, cantidad_trab, id_porcentaje)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            nuevo_id,
            data['id_actividad'],
            data['rendimiento_total'],
            data['cantidad_trab'],
            data['id_porcentaje']
        ))
        conn.commit()
        return jsonify({
            'mensaje': 'Rendimiento grupal creado exitosamente',
            'id': nuevo_id,
            'id_actividad': data['id_actividad']
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 🚀 Endpoint para eliminar un rendimiento individual
@rendimientos_bp.route('/individual/<string:rendimiento_id>', methods=['DELETE'])
@jwt_required()
def eliminar_rendimiento_individual(rendimiento_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el rendimiento exista y pertenezca a una actividad del usuario
        cursor.execute("""
            SELECT r.id 
            FROM tarja_fact_rendimientopropio r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            WHERE r.id = %s AND a.id_usuario = %s
        """, (rendimiento_id, usuario_id))
        
        rendimiento = cursor.fetchone()
        if not rendimiento:
            cursor.close()
            conn.close()
            return jsonify({"error": "Rendimiento no encontrado o no tienes permiso para eliminarlo"}), 404
        
        # Eliminar el rendimiento
        cursor.execute("DELETE FROM tarja_fact_rendimientopropio WHERE id = %s", (rendimiento_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento individual eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar un rendimiento grupal
@rendimientos_bp.route('/grupal/<string:rendimiento_id>', methods=['DELETE'])
@jwt_required()
def eliminar_rendimiento_grupal(rendimiento_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar que el rendimiento exista y pertenezca a una actividad del usuario
        cursor.execute("""
            SELECT rg.id 
            FROM tarja_fact_redimientogrupal rg
            JOIN tarja_fact_actividad a ON rg.id_actividad = a.id
            WHERE rg.id = %s AND a.id_usuario = %s
        """, (rendimiento_id, usuario_id))
        
        rendimiento = cursor.fetchone()
        if not rendimiento:
            cursor.close()
            conn.close()
            return jsonify({"error": "Rendimiento grupal no encontrado o no tienes permiso para eliminarlo"}), 404
        
        # Eliminar el rendimiento
        cursor.execute("DELETE FROM tarja_fact_redimientogrupal WHERE id = %s", (rendimiento_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento grupal eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Obtener rendimientos individuales propios
@rendimientos_bp.route('/individual/propio', methods=['GET'])
@jwt_required()
def obtener_rendimientos_individuales_propios():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener la sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or usuario['id_sucursalactiva'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['id_sucursalactiva']
        id_actividad = request.args.get('id_actividad')

        sql = """
            SELECT 
                r.id,
                r.id_actividad,
                r.id_colaborador,
                r.rendimiento,
                r.horas_trabajadas,
                r.horas_extras,
                r.id_bono,
                l.nombre as nombre_actividad,
                c.nombre as nombre_colaborador,
                b.nombre as nombre_bono
            FROM tarja_fact_rendimientopropio r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            JOIN general_dim_labor l ON a.id_labor = l.id
            JOIN general_dim_colaborador c ON r.id_colaborador = c.id
            LEFT JOIN general_dim_bono b ON r.id_bono = b.id
            WHERE a.id_sucursalactiva = %s
        """
        params = [id_sucursal]
        if id_actividad:
            sql += " AND r.id_actividad = %s"
            params.append(id_actividad)
        sql += " ORDER BY c.nombre ASC, c.apellido_paterno ASC, c.apellido_materno ASC, l.nombre ASC"
        cursor.execute(sql, tuple(params))
        rendimientos = cursor.fetchall()

        # Convertir valores numéricos a float para evitar redondeo
        for rendimiento in rendimientos:
            if 'rendimiento' in rendimiento and rendimiento['rendimiento'] is not None:
                rendimiento['rendimiento'] = float(rendimiento['rendimiento'])
            if 'horas_trabajadas' in rendimiento and rendimiento['horas_trabajadas'] is not None:
                rendimiento['horas_trabajadas'] = float(rendimiento['horas_trabajadas'])
            if 'horas_extras' in rendimiento and rendimiento['horas_extras'] is not None:
                rendimiento['horas_extras'] = float(rendimiento['horas_extras'])

        cursor.close()
        conn.close()

        if not rendimientos:
            return jsonify([]), 200

        return jsonify(rendimientos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Obtener rendimientos individuales de contratistas
@rendimientos_bp.route('/individual/contratista', methods=['GET'])
@jwt_required()
def obtener_rendimientos_individuales_contratistas():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener la sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or usuario['id_sucursalactiva'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['id_sucursalactiva']

        # Obtener rendimientos individuales de contratistas
        cursor.execute("""
            SELECT 
                r.id,
                r.id_actividad,
                r.id_trabajador,
                r.rendimiento,
                r.id_porcentaje_individual,
                l.nombre as nombre_actividad,
                t.nombre as nombre_trabajador,
                p.porcentaje
            FROM tarja_fact_rendimientocontratista r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            JOIN general_dim_labor l ON a.id_labor = l.id
            JOIN general_dim_trabajador t ON r.id_trabajador = t.id
            JOIN general_dim_porcentajecontratista p ON r.id_porcentaje_individual = p.id
            WHERE a.id_sucursalactiva = %s
            ORDER BY t.nombre ASC, l.nombre ASC
        """, (id_sucursal,))
        rendimientos = cursor.fetchall()

        # Convertir valores numéricos a float para evitar redondeo
        for rendimiento in rendimientos:
            if 'rendimiento' in rendimiento and rendimiento['rendimiento'] is not None:
                rendimiento['rendimiento'] = float(rendimiento['rendimiento'])

        cursor.close()
        conn.close()

        if not rendimientos:
            return jsonify([]), 200

        return jsonify(rendimientos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para crear rendimientos individuales propios
@rendimientos_bp.route('/individual/propio', methods=['POST'])
@jwt_required()
def crear_rendimiento_individual_propio():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        rendimiento_id = str(uuid.uuid4())

        # Calcular horas_trabajadas a partir de la actividad
        cursor.execute("SELECT hora_inicio, hora_fin FROM tarja_fact_actividad WHERE id = %s", (data['id_actividad'],))
        actividad = cursor.fetchone()
        if not actividad or not actividad[0] or not actividad[1]:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se pudo obtener hora_inicio y hora_fin de la actividad"}), 400
        hora_inicio = actividad[0]
        hora_fin = actividad[1]
        h_inicio = datetime.strptime(str(hora_inicio), "%H:%M:%S")
        h_fin = datetime.strptime(str(hora_fin), "%H:%M:%S")
        horas_trabajadas = (h_fin - h_inicio).total_seconds() / 3600
        if horas_trabajadas < 0:
            horas_trabajadas += 24

        # Asegurar que horas_extras nunca sea None
        horas_extras = data.get('horas_extras')
        if horas_extras is None:
            horas_extras = 0

        sql = """
            INSERT INTO tarja_fact_rendimientopropio 
            (id, id_actividad, id_colaborador, rendimiento, horas_trabajadas, horas_extras, id_bono)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            rendimiento_id,
            data['id_actividad'],
            data['id_colaborador'],
            float(data['rendimiento']),
            horas_trabajadas,
            float(horas_extras),
            data.get('id_bono', None)
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento individual propio creado correctamente", "id": rendimiento_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para crear rendimientos individuales de contratista
@rendimientos_bp.route('/individual/contratista', methods=['POST'])
@jwt_required()
def crear_rendimiento_individual_contratista():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        rendimiento_id = str(uuid.uuid4())
        sql = """
            INSERT INTO tarja_fact_rendimientocontratista 
            (id, id_actividad, id_trabajador, rendimiento, id_porcentaje_individual)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            rendimiento_id,
            data['id_actividad'],
            data['id_trabajador'],
            float(data['rendimiento']),
            data['id_porcentaje_individual']
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento individual de contratista creado correctamente", "id": rendimiento_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para editar rendimiento individual propio
@rendimientos_bp.route('/individual/propio/<string:rendimiento_id>', methods=['PUT'])
@jwt_required()
def editar_rendimiento_individual_propio(rendimiento_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()

        # Calcular horas_trabajadas a partir de la actividad
        cursor.execute("SELECT hora_inicio, hora_fin FROM tarja_fact_actividad WHERE id = %s", (data['id_actividad'],))
        actividad = cursor.fetchone()
        if not actividad or not actividad[0] or not actividad[1]:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se pudo obtener hora_inicio y hora_fin de la actividad"}), 400
        hora_inicio = actividad[0]
        hora_fin = actividad[1]
        h_inicio = datetime.strptime(str(hora_inicio), "%H:%M:%S")
        h_fin = datetime.strptime(str(hora_fin), "%H:%M:%S")
        horas_trabajadas = (h_fin - h_inicio).total_seconds() / 3600
        if horas_trabajadas < 0:
            horas_trabajadas += 24

        # Asegurar que horas_extras nunca sea None
        horas_extras = data.get('horas_extras')
        if horas_extras is None:
            horas_extras = 0

        sql = """
            UPDATE tarja_fact_rendimientopropio 
            SET id_actividad = %s, id_colaborador = %s, rendimiento = %s, 
                horas_trabajadas = %s, horas_extras = %s, id_bono = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            data['id_actividad'],
            data['id_colaborador'],
            float(data['rendimiento']),
            horas_trabajadas,
            float(horas_extras),
            data.get('id_bono', None),
            rendimiento_id
        ))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Rendimiento individual propio actualizado correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para editar rendimiento individual de contratista
@rendimientos_bp.route('/individual/contratista/<string:rendimiento_id>', methods=['PUT'])
@jwt_required()
def editar_rendimiento_individual_contratista(rendimiento_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE tarja_fact_rendimientocontratista 
            SET id_actividad = %s, id_trabajador = %s, rendimiento = %s, 
                id_porcentaje_individual = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            data['id_actividad'],
            data['id_trabajador'],
            float(data['rendimiento']),
            data['id_porcentaje_individual'],
            rendimiento_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento individual de contratista actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar rendimiento individual propio
@rendimientos_bp.route('/individual/propio/<string:rendimiento_id>', methods=['DELETE'])
@jwt_required()
def eliminar_rendimiento_individual_propio(rendimiento_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM tarja_fact_rendimientopropio WHERE id = %s"
        cursor.execute(sql, (rendimiento_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento individual propio eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 Endpoint para eliminar rendimiento individual de contratista
@rendimientos_bp.route('/individual/contratista/<string:rendimiento_id>', methods=['DELETE'])
@jwt_required()
def eliminar_rendimiento_individual_contratista(rendimiento_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM tarja_fact_rendimientocontratista WHERE id = %s"
        cursor.execute(sql, (rendimiento_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento individual de contratista eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Obtener rendimiento por ID (grupal)
@rendimientos_bp.route('/<string:rendimiento_id>', methods=['GET'])
@jwt_required()
def obtener_rendimiento(rendimiento_id):
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener la sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario or not usuario['id_sucursalactiva']:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        
        id_sucursal = usuario['id_sucursalactiva']
        
        # Buscar el rendimiento en las diferentes tablas
        # 1. Buscar en rendimientos propios
        cursor.execute("""
            SELECT r.*, 'propio' as tipo
            FROM tarja_fact_rendimientopropio r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            WHERE r.id = %s AND a.id_sucursalactiva = %s
        """, (rendimiento_id, id_sucursal))
        rendimiento = cursor.fetchone()
        
        if rendimiento:
            cursor.close()
            conn.close()
            return jsonify(rendimiento), 200
        
        # 2. Buscar en rendimientos de contratistas
        cursor.execute("""
            SELECT r.*, 'contratista' as tipo
            FROM tarja_fact_rendimientocontratista r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            WHERE r.id = %s AND a.id_sucursalactiva = %s
        """, (rendimiento_id, id_sucursal))
        rendimiento = cursor.fetchone()
        
        if rendimiento:
            cursor.close()
            conn.close()
            return jsonify(rendimiento), 200
        
        # 3. Buscar en rendimientos grupales
        cursor.execute("""
            SELECT r.*, 'grupal' as tipo
            FROM tarja_fact_redimientogrupal r
            JOIN tarja_fact_actividad a ON r.id_actividad = a.id
            WHERE r.id = %s AND a.id_sucursalactiva = %s
        """, (rendimiento_id, id_sucursal))
        rendimiento = cursor.fetchone()
        
        if rendimiento:
            cursor.close()
            conn.close()
            return jsonify(rendimiento), 200
        
        cursor.close()
        conn.close()
        return jsonify({"error": "Rendimiento no encontrado"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

