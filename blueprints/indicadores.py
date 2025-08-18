from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from datetime import datetime, timedelta, date
from decimal import Decimal

indicadores_bp = Blueprint('indicadores_bp', __name__)


# Obtener resumen de horas diarias por colaborador vs horas esperadas
@indicadores_bp.route('/control-horas/resumen-diario-colaborador', methods=['GET'])
@jwt_required()
def obtener_resumen_horas_diarias_colaborador():
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
        
        # Parámetros de filtrado
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        id_colaborador = request.args.get('id_colaborador')
        
        # Construir consulta de resumen diario usando id_sucursal directamente de la vista
        sql = """
            SELECT 
                v.id_colaborador,
                v.colaborador,
                v.fecha,
                DAYNAME(v.fecha) as nombre_dia,
                SUM(v.horas_trabajadas) as horas_trabajadas,
                h.horas_dia as horas_esperadas,
                (SUM(v.horas_trabajadas) - h.horas_dia) as diferencia_horas,
                CASE 
                    WHEN SUM(v.horas_trabajadas) > h.horas_dia THEN 'MÁS'
                    WHEN SUM(v.horas_trabajadas) < h.horas_dia THEN 'MENOS'
                    ELSE 'EXACTO'
                END as estado_trabajo
            FROM v_tarja_tarjamovil_controlhoras v
            LEFT JOIN tarja_dim_horaspordia h ON h.id_empresa = v.id_empresa 
                AND h.nombre_dia = CASE 
                    WHEN DAYNAME(v.fecha) = 'Monday' THEN 'Lunes'
                    WHEN DAYNAME(v.fecha) = 'Tuesday' THEN 'Martes'
                    WHEN DAYNAME(v.fecha) = 'Wednesday' THEN 'Miércoles'
                    WHEN DAYNAME(v.fecha) = 'Thursday' THEN 'Jueves'
                    WHEN DAYNAME(v.fecha) = 'Friday' THEN 'Viernes'
                    WHEN DAYNAME(v.fecha) = 'Saturday' THEN 'Sábado'
                    WHEN DAYNAME(v.fecha) = 'Sunday' THEN 'Domingo'
                END
            WHERE v.id_sucursal = %s
                AND v.id_usuario = %s
                AND estado_actividad = 'CREADA'
        """
        params = [id_sucursal, usuario_id]
        
        # Agregar filtros
        if fecha_inicio:
            sql += " AND v.fecha >= %s"
            params.append(fecha_inicio)
        
        if fecha_fin:
            sql += " AND v.fecha <= %s"
            params.append(fecha_fin)
        
        if id_colaborador:
            sql += " AND v.id_colaborador = %s"
            params.append(id_colaborador)
        
        # Agrupar por colaborador y fecha
        sql += " GROUP BY v.id_colaborador, v.colaborador, v.fecha, h.horas_dia ORDER BY v.fecha DESC, v.colaborador ASC"
        
        cursor.execute(sql, tuple(params))
        resultados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(resultados), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Obtener actividades de un colaborador específico
@indicadores_bp.route('/control-horas/actividades-colaborador', methods=['GET'])
@jwt_required()
def obtener_actividades_colaborador():
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
        
        # Parámetros requeridos
        id_colaborador = request.args.get('id_colaborador')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        if not id_colaborador:
            return jsonify({"error": "id_colaborador es requerido"}), 400
        
        # Construir consulta de actividades del colaborador
        sql = """
            SELECT 
                v.id_colaborador,
                v.colaborador,
                v.fecha,
                v.labor,
                v.horas_trabajadas,
                v.nombre_ceco,
                v.tipoceco,
                v.detalle_ceco,
                v.usuario,
                DAYNAME(v.fecha) as nombre_dia,
                h.horas_dia as horas_esperadas,
                (v.horas_trabajadas - h.horas_dia) as diferencia_horas,
                CASE 
                    WHEN v.horas_trabajadas > h.horas_dia THEN 'MÁS'
                    WHEN v.horas_trabajadas < h.horas_dia THEN 'MENOS'
                    ELSE 'EXACTO'
                END as estado_trabajo
            FROM v_tarja_tarjamovil_controlhoras v
            LEFT JOIN tarja_dim_horaspordia h ON h.id_empresa = v.id_empresa 
                AND h.nombre_dia = CASE 
                    WHEN DAYNAME(v.fecha) = 'Monday' THEN 'Lunes'
                    WHEN DAYNAME(v.fecha) = 'Tuesday' THEN 'Martes'
                    WHEN DAYNAME(v.fecha) = 'Wednesday' THEN 'Miércoles'
                    WHEN DAYNAME(v.fecha) = 'Thursday' THEN 'Jueves'
                    WHEN DAYNAME(v.fecha) = 'Friday' THEN 'Viernes'
                    WHEN DAYNAME(v.fecha) = 'Saturday' THEN 'Sábado'
                    WHEN DAYNAME(v.fecha) = 'Sunday' THEN 'Domingo'
                END
            WHERE v.id_sucursal = %s 
                AND v.id_colaborador = %s
                AND v.id_usuario = %s
        """
        params = [id_sucursal, id_colaborador, usuario_id]
        
        # Agregar filtros de fecha si se proporcionan
        if fecha_inicio:
            sql += " AND v.fecha >= %s"
            params.append(fecha_inicio)
        
        if fecha_fin:
            sql += " AND v.fecha <= %s"
            params.append(fecha_fin)
        
        # Ordenar por fecha descendente y horas trabajadas descendente
        sql += " ORDER BY v.fecha DESC, v.horas_trabajadas DESC"
        
        cursor.execute(sql, tuple(params))
        actividades = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Convertir tipos de datos problemáticos para JSON
        if actividades:
            for actividad in actividades:
                for key, value in actividad.items():
                    if isinstance(value, (datetime, date)):
                        actividad[key] = value.isoformat()
                    elif isinstance(value, Decimal):
                        actividad[key] = float(value)
        
        return jsonify(actividades), 200
        
    except Exception as e:
        print(f"ERROR en obtener_actividades_colaborador: {str(e)}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


# Resumen diario de rendimientos individuales (propios y contratistas) por fecha
@indicadores_bp.route('/control-rendimientos/individuales', methods=['GET'])
@jwt_required()
def obtener_rendimientos_individuales():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or usuario['id_sucursalactiva'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']

        # Filtros opcionales
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        id_tiporendimiento = request.args.get('id_tiporendimiento')
        id_labor = request.args.get('id_labor')
        id_ceco = request.args.get('id_ceco')
        id_trabajador = request.args.get('id_trabajador')
        id_unidad = request.args.get('id_unidad')
        tipo_mo = request.args.get('tipo_mo')  # 'PROPIO' o 'CONTRATISTA'

        # Consulta de rendimientos individuales (donde id_trabajador NO es NULL)
        sql = """
            SELECT
                v.fecha,
                v.tipo_mo,
                v.id_tiporendimiento,
                v.tipo_rendimiento,
                v.grupo_mo,
                v.id_labor,
                v.labor,
                v.id_ceco,
                v.nombre_ceco,
                v.id_tipoceco,
                v.tipoceco,
                v.detalle_ceco,
                v.id_trabajador,
                v.trabajador,
                v.rendimiento,
                v.id_unidad,
                v.unidad,
                v.porcentaje_contratista,
                v.usuario,
                v.sucursal
            FROM v_tarja_tarjamovil_controlrendimiento v
            WHERE v.id_sucursal = %s
              AND v.id_usuario = %s
              AND v.id_trabajador IS NOT NULL
        """
        params = [id_sucursal, usuario_id]

        if fecha_inicio:
            sql += " AND v.fecha >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND v.fecha <= %s"
            params.append(fecha_fin)
        if id_tiporendimiento:
            sql += " AND v.id_tiporendimiento = %s"
            params.append(id_tiporendimiento)
        if id_labor:
            sql += " AND v.id_labor = %s"
            params.append(id_labor)
        if id_ceco:
            sql += " AND v.id_ceco = %s"
            params.append(id_ceco)
        if id_trabajador:
            sql += " AND v.id_trabajador = %s"
            params.append(id_trabajador)
        if id_unidad:
            sql += " AND v.id_unidad = %s"
            params.append(id_unidad)
        if tipo_mo:
            sql += " AND v.tipo_mo = %s"
            params.append(tipo_mo)

        sql += " ORDER BY v.fecha DESC, v.tipo_mo ASC, v.labor ASC, v.trabajador ASC, v.nombre_ceco ASC, v.unidad ASC"

        cursor.execute(sql, tuple(params))
        rendimientos = cursor.fetchall()

        # Normalizar tipos para JSON
        for fila in rendimientos:
            if isinstance(fila.get('fecha'), (datetime, date)):
                fila['fecha'] = fila['fecha'].isoformat()
            if isinstance(fila.get('rendimiento'), Decimal):
                fila['rendimiento'] = float(fila['rendimiento'])
            if isinstance(fila.get('porcentaje_contratista'), Decimal):
                fila['porcentaje_contratista'] = float(fila['porcentaje_contratista'])

        cursor.close()
        conn.close()
        return jsonify(rendimientos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Resumen diario de rendimientos grupales (contratistas) por fecha
@indicadores_bp.route('/control-rendimientos/grupales', methods=['GET'])
@jwt_required()
def obtener_rendimientos_grupales():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or usuario['id_sucursalactiva'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']

        # Filtros opcionales
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        id_tiporendimiento = request.args.get('id_tiporendimiento')
        id_labor = request.args.get('id_labor')
        id_ceco = request.args.get('id_ceco')
        id_unidad = request.args.get('id_unidad')
        grupo_mo = request.args.get('grupo_mo')  # Nombre del contratista

        # Consulta de rendimientos grupales (donde id_trabajador ES NULL)
        sql = """
            SELECT
                v.fecha,
                v.tipo_mo,
                v.id_tiporendimiento,
                v.tipo_rendimiento,
                v.grupo_mo,
                v.cantidad_trab,
                v.id_labor,
                v.labor,
                v.id_ceco,
                v.nombre_ceco,
                v.id_tipoceco,
                v.tipoceco,
                v.detalle_ceco,
                v.rendimiento,
                v.id_unidad,
                v.unidad,
                v.porcentaje_contratista,
                v.usuario,
                v.sucursal
            FROM v_tarja_tarjamovil_controlrendimiento v
            WHERE v.id_sucursal = %s
              AND v.id_usuario = %s
              AND v.id_trabajador IS NULL
        """
        params = [id_sucursal, usuario_id]

        if fecha_inicio:
            sql += " AND v.fecha >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND v.fecha <= %s"
            params.append(fecha_fin)
        if id_tiporendimiento:
            sql += " AND v.id_tiporendimiento = %s"
            params.append(id_tiporendimiento)
        if id_labor:
            sql += " AND v.id_labor = %s"
            params.append(id_labor)
        if id_ceco:
            sql += " AND v.id_ceco = %s"
            params.append(id_ceco)
        if id_unidad:
            sql += " AND v.id_unidad = %s"
            params.append(id_unidad)
        if grupo_mo:
            sql += " AND v.grupo_mo = %s"
            params.append(grupo_mo)

        sql += " ORDER BY v.fecha DESC, v.tipo_mo ASC, v.labor ASC, v.grupo_mo ASC, v.nombre_ceco ASC, v.unidad ASC"

        cursor.execute(sql, tuple(params))
        rendimientos = cursor.fetchall()

        # Normalizar tipos para JSON
        for fila in rendimientos:
            if isinstance(fila.get('fecha'), (datetime, date)):
                fila['fecha'] = fila['fecha'].isoformat()
            if isinstance(fila.get('rendimiento'), Decimal):
                fila['rendimiento'] = float(fila['rendimiento'])
            if isinstance(fila.get('porcentaje_contratista'), Decimal):
                fila['porcentaje_contratista'] = float(fila['porcentaje_contratista'])
            if isinstance(fila.get('cantidad_trab'), Decimal):
                fila['cantidad_trab'] = int(fila['cantidad_trab'])

        cursor.close()
        conn.close()
        return jsonify(rendimientos), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Resumen diario de rendimientos (todos los tipos) por fecha
@indicadores_bp.route('/control-rendimientos/resumen', methods=['GET'])
@jwt_required()
def obtener_resumen_rendimientos_diario():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or usuario['id_sucursalactiva'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']

        # Filtros opcionales
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        id_tiporendimiento = request.args.get('id_tiporendimiento')
        id_labor = request.args.get('id_labor')
        id_ceco = request.args.get('id_ceco')
        id_unidad = request.args.get('id_unidad')
        tipo_mo = request.args.get('tipo_mo')

        # Consulta de resumen agregado por día, tipo de mano de obra, labor, CECO y unidad
        sql = """
            SELECT
                v.fecha,
                v.tipo_mo,
                v.id_tiporendimiento,
                v.tipo_rendimiento,
                v.grupo_mo,
                v.id_labor,
                v.labor,
                v.id_ceco,
                v.nombre_ceco,
                v.id_tipoceco,
                v.tipoceco,
                v.detalle_ceco,
                v.id_unidad,
                v.unidad,
                SUM(v.rendimiento) AS total_rendimiento,
                COUNT(DISTINCT CASE WHEN v.id_trabajador IS NOT NULL THEN v.id_trabajador END) AS total_trabajadores_individuales,
                COUNT(DISTINCT CASE WHEN v.id_trabajador IS NULL THEN v.grupo_mo END) AS total_grupos,
                SUM(CASE WHEN v.id_trabajador IS NOT NULL THEN v.cantidad_trab ELSE 0 END) AS total_cantidad_individuales,
                SUM(CASE WHEN v.id_trabajador IS NULL THEN v.cantidad_trab ELSE 0 END) AS total_cantidad_grupales
            FROM v_tarja_tarjamovil_controlrendimiento v
            WHERE v.id_sucursal = %s
              AND v.id_usuario = %s
        """
        params = [id_sucursal, usuario_id]

        if fecha_inicio:
            sql += " AND v.fecha >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += " AND v.fecha <= %s"
            params.append(fecha_fin)
        if id_tiporendimiento:
            sql += " AND v.id_tiporendimiento = %s"
            params.append(id_tiporendimiento)
        if id_labor:
            sql += " AND v.id_labor = %s"
            params.append(id_labor)
        if id_ceco:
            sql += " AND v.id_ceco = %s"
            params.append(id_ceco)
        if id_unidad:
            sql += " AND v.id_unidad = %s"
            params.append(id_unidad)
        if tipo_mo:
            sql += " AND v.tipo_mo = %s"
            params.append(tipo_mo)

        sql += """ GROUP BY v.fecha, v.tipo_mo, v.id_tiporendimiento, v.tipo_rendimiento, v.grupo_mo, 
                   v.id_labor, v.labor, v.id_ceco, v.nombre_ceco, v.id_tipoceco, v.tipoceco, v.detalle_ceco, v.id_unidad, v.unidad"""
        sql += " ORDER BY v.fecha DESC, v.tipo_mo ASC, v.labor ASC, v.grupo_mo ASC, v.nombre_ceco ASC, v.unidad ASC"

        cursor.execute(sql, tuple(params))
        resumen = cursor.fetchall()

        # Normalizar tipos para JSON
        for fila in resumen:
            if isinstance(fila.get('fecha'), (datetime, date)):
                fila['fecha'] = fila['fecha'].isoformat()
            if isinstance(fila.get('total_rendimiento'), Decimal):
                fila['total_rendimiento'] = float(fila['total_rendimiento'])
            if isinstance(fila.get('total_trabajadores_individuales'), Decimal):
                fila['total_trabajadores_individuales'] = int(fila['total_trabajadores_individuales'])
            if isinstance(fila.get('total_grupos'), Decimal):
                fila['total_grupos'] = int(fila['total_grupos'])
            if isinstance(fila.get('total_cantidad_individuales'), Decimal):
                fila['total_cantidad_individuales'] = int(fila['total_cantidad_individuales'])
            if isinstance(fila.get('total_cantidad_grupales'), Decimal):
                fila['total_cantidad_grupales'] = int(fila['total_cantidad_grupales'])

        cursor.close()
        conn.close()
        return jsonify(resumen), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

