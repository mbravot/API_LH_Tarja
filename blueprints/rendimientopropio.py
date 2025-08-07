from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
import uuid

rendimientopropio_bp = Blueprint('rendimientopropio_bp', __name__)

# Crear rendimiento propio
@rendimientopropio_bp.route('/', methods=['POST'])
@jwt_required()
def crear_rendimiento_propio():
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        
        # Validar campos requeridos
        campos_requeridos = ['id_actividad', 'id_colaborador', 'rendimiento']
        for campo in campos_requeridos:
            if campo not in data or not data[campo]:
                return jsonify({"error": f"El campo {campo} es requerido"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que la actividad existe y pertenece al usuario
        cursor.execute("""
            SELECT id FROM tarja_fact_actividad 
            WHERE id = %s AND id_usuario = %s
        """, (data['id_actividad'], usuario_id))
        actividad = cursor.fetchone()
        if not actividad:
            cursor.close()
            conn.close()
            return jsonify({"error": "Actividad no encontrada o no tienes permisos"}), 404
        
        # Generar id UUID
        rendimiento_id = str(uuid.uuid4())
        
        sql = """
            INSERT INTO tarja_fact_rendimientopropio (
                id, id_actividad, id_colaborador, rendimiento, 
                horas_trabajadas, horas_extras, id_bono
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            rendimiento_id,
            data['id_actividad'],
            data['id_colaborador'],
            float(data['rendimiento']),  # ✅ Conversión explícita a float
            float(data.get('horas_trabajadas', 0)),
            float(data.get('horas_extras', 0)),
            data.get('id_bono', None)
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento propio creado correctamente", "id": rendimiento_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Listar rendimientos propios por actividad (filtrado por sucursal del usuario)
@rendimientopropio_bp.route('/actividad/<string:id_actividad>', methods=['GET'])
@jwt_required()
def listar_rendimientos_propios_por_actividad(id_actividad):
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
        # Verificar que la actividad pertenece a la sucursal y obtener fecha, labor y CECO principal
        cursor.execute("""
            SELECT 
                a.fecha, 
                l.nombre AS labor,
                a.id_estadoactividad,
                COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) AS id_ceco
            FROM tarja_fact_actividad a
            JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN tarja_fact_cecoproductivo cp ON a.id = cp.id_actividad
            LEFT JOIN tarja_fact_cecoinversion ci ON a.id = ci.id_actividad
            LEFT JOIN tarja_fact_cecomaquinaria cm ON a.id = cm.id_actividad
            LEFT JOIN tarja_fact_cecoriego cr ON a.id = cr.id_actividad
            LEFT JOIN tarja_fact_cecoadministrativo ca ON a.id = ca.id_actividad
            WHERE a.id = %s AND a.id_sucursalactiva = %s
            LIMIT 1
        """, (id_actividad, id_sucursal))
        actividad = cursor.fetchone()
        if not actividad:
            return jsonify({"error": "Actividad no encontrada o no pertenece a tu sucursal"}), 404
        if actividad['id_estadoactividad'] != 1:
            return jsonify({"rendimientos": []}), 200
        # Obtener nombre del CECO
        nombre_ceco = None
        if actividad['id_ceco']:
            cursor.execute("SELECT nombre FROM general_dim_ceco WHERE id = %s", (actividad['id_ceco'],))
            ceco = cursor.fetchone()
            if ceco:
                nombre_ceco = ceco['nombre']
        # Obtener rendimientos propios
        cursor.execute("""
            SELECT r.id, r.id_colaborador, c.nombre as nombre_colaborador, c.apellido_paterno, c.apellido_materno,
                   r.horas_trabajadas, r.rendimiento, r.horas_extras, r.id_bono
            FROM tarja_fact_rendimientopropio r
            JOIN general_dim_colaborador c ON r.id_colaborador = c.id
            WHERE r.id_actividad = %s
            ORDER BY c.nombre ASC, c.apellido_paterno ASC, c.apellido_materno ASC
        """, (id_actividad,))
        rendimientos = cursor.fetchall()
        cursor.close()
        conn.close()
        # Formatear nombre completo del colaborador
        for r in rendimientos:
            r['nombre_colaborador'] = f"{r['nombre_colaborador']} {r['apellido_paterno']} {r['apellido_materno'] or ''}".strip()
            del r['apellido_paterno']
            del r['apellido_materno']
        return jsonify({
            "actividad": {
                "fecha": str(actividad['fecha']),
                "labor": actividad['labor'],
                "ceco": nombre_ceco
            },
            "rendimientos": rendimientos
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar horas trabajadas (y opcionalmente otros campos) de un rendimiento propio
@rendimientopropio_bp.route('/<string:id_rendimiento>', methods=['PUT'])
@jwt_required()
def editar_rendimiento_propio(id_rendimiento):
    try:
        if not id_rendimiento or id_rendimiento.lower() == 'null':
            return jsonify({"error": "ID de rendimiento inválido"}), 400
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Verificar que el rendimiento existe
        cursor.execute("SELECT * FROM tarja_fact_rendimientopropio WHERE id = %s", (id_rendimiento,))
        rendimiento = cursor.fetchone()
        if not rendimiento:
            return jsonify({"error": "Rendimiento no encontrado"}), 404
        # Actualizar campos editables
        sql = """
            UPDATE tarja_fact_rendimientopropio
            SET horas_trabajadas = %s, horas_extras = %s, rendimiento = %s, id_bono = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            float(data.get('horas_trabajadas', rendimiento['horas_trabajadas'])),
            float(data.get('horas_extras', rendimiento['horas_extras'])),
            float(data.get('rendimiento', rendimiento['rendimiento'])),
            data.get('id_bono', rendimiento['id_bono']),
            id_rendimiento
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Rendimiento actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@rendimientopropio_bp.route('/actividades', methods=['GET'])
@jwt_required()
def listar_actividades_sucursal_usuario():
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
        # Listar actividades de la sucursal con estado 1 (creada) y obtener el CECO principal
        cursor.execute("""
            SELECT a.id, a.fecha, l.nombre AS labor, a.id_estadoactividad, a.id_tipotrabajador,
                   COALESCE(cp.id_ceco, ci.id_ceco, cm.id_ceco, cr.id_ceco, ca.id_ceco) AS id_ceco
            FROM tarja_fact_actividad a
            JOIN general_dim_labor l ON a.id_labor = l.id
            LEFT JOIN tarja_fact_cecoproductivo cp ON a.id = cp.id_actividad
            LEFT JOIN tarja_fact_cecoinversion ci ON a.id = ci.id_actividad
            LEFT JOIN tarja_fact_cecomaquinaria cm ON a.id = cm.id_actividad
            LEFT JOIN tarja_fact_cecoriego cr ON a.id = cr.id_actividad
            LEFT JOIN tarja_fact_cecoadministrativo ca ON a.id = ca.id_actividad
            WHERE a.id_sucursalactiva = %s AND a.id_estadoactividad = 1 AND a.id_tipotrabajador = 1 AND a.id_usuario = %s
            ORDER BY a.fecha DESC
        """, (id_sucursal, usuario_id))
        actividades = cursor.fetchall()
        # Obtener nombre del CECO para cada actividad
        for act in actividades:
            nombre_ceco = None
            if act['id_ceco']:
                cursor.execute("SELECT nombre FROM general_dim_ceco WHERE id = %s", (act['id_ceco'],))
                ceco = cursor.fetchone()
                if ceco:
                    nombre_ceco = ceco['nombre']
            act['ceco'] = nombre_ceco
            del act['id_ceco']
        cursor.close()
        conn.close()
        return jsonify(actividades), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500 