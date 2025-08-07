from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from datetime import datetime, timedelta, date
from decimal import Decimal

indicadores_bp = Blueprint('indicadores_bp', __name__)

# Obtener control de horas general
@indicadores_bp.route('/control-horas', methods=['GET'])
@jwt_required()
def obtener_control_horas():
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
        id_labor = request.args.get('id_labor')
        id_ceco = request.args.get('id_ceco')
        
        # Construir consulta base
        sql = """
            SELECT 
                id_colaborador,
                colaborador,
                fecha,
                id_labor,
                labor,
                id_ceco,
                nombre_ceco,
                id_tipoceco,
                tipoceco,
                detalle_ceco,
                id_usuario,
                usuario,
                horas_trabajadas,
                id_empresa
            FROM v_tarja_tarjamovil_controlhoras
            WHERE id_empresa = (SELECT id_empresa FROM general_dim_sucursal WHERE id = %s)
                AND id_usuario = %s
        """
        params = [id_sucursal, usuario_id]
        
        # Agregar filtros
        if fecha_inicio:
            sql += " AND fecha >= %s"
            params.append(fecha_inicio)
        
        if fecha_fin:
            sql += " AND fecha <= %s"
            params.append(fecha_fin)
        
        if id_colaborador:
            sql += " AND id_colaborador = %s"
            params.append(id_colaborador)
        
        if id_labor:
            sql += " AND id_labor = %s"
            params.append(id_labor)
        
        if id_ceco:
            sql += " AND id_ceco = %s"
            params.append(id_ceco)
        
        # Ordenar por fecha y colaborador
        sql += " ORDER BY fecha DESC, colaborador ASC"
        
        cursor.execute(sql, tuple(params))
        resultados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(resultados), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener resumen de horas por colaborador
@indicadores_bp.route('/control-horas/resumen-colaborador', methods=['GET'])
@jwt_required()
def obtener_resumen_horas_colaborador():
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
        
        # Construir consulta de resumen
        sql = """
            SELECT 
                id_colaborador,
                colaborador,
                COUNT(*) as total_registros,
                SUM(horas_trabajadas) as total_horas,
                MIN(fecha) as fecha_inicio,
                MAX(fecha) as fecha_fin
            FROM v_tarja_tarjamovil_controlhoras
            WHERE id_empresa = (SELECT id_empresa FROM general_dim_sucursal WHERE id = %s)
                AND id_usuario = %s
        """
        params = [id_sucursal, usuario_id]
        
        # Agregar filtros de fecha
        if fecha_inicio:
            sql += " AND fecha >= %s"
            params.append(fecha_inicio)
        
        if fecha_fin:
            sql += " AND fecha <= %s"
            params.append(fecha_fin)
        
        # Agrupar por colaborador
        sql += " GROUP BY id_colaborador, colaborador ORDER BY total_horas DESC"
        
        cursor.execute(sql, tuple(params))
        resultados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(resultados), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

# Obtener detalle de actividades por colaborador y fecha
@indicadores_bp.route('/control-horas/detalle-actividades', methods=['GET'])
@jwt_required()
def obtener_detalle_actividades():
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
        fecha = request.args.get('fecha')
        
        if not id_colaborador or not fecha:
            return jsonify({"error": "id_colaborador y fecha son requeridos"}), 400
        
        print(f"DEBUG: usuario_id={usuario_id}, id_sucursal={id_sucursal}, id_colaborador={id_colaborador}, fecha={fecha}")
        
        # Construir consulta de detalle de actividades
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
                AND v.fecha = %s
                AND v.id_usuario = %s
            ORDER BY v.horas_trabajadas DESC
        """
        
        print(f"DEBUG: Ejecutando consulta con parámetros: {id_sucursal}, {id_colaborador}, {fecha}, {usuario_id}")
        cursor.execute(sql, (id_sucursal, id_colaborador, fecha, usuario_id))
        actividades = cursor.fetchall()
        print(f"DEBUG: Actividades encontradas: {len(actividades)}")
        
        # Obtener resumen del día
        sql_resumen = """
            SELECT 
                SUM(v.horas_trabajadas) as total_horas_dia,
                COUNT(*) as total_actividades,
                MAX(h.horas_dia) as horas_esperadas,
                (SUM(v.horas_trabajadas) - MAX(h.horas_dia)) as diferencia_total,
                CASE 
                    WHEN SUM(v.horas_trabajadas) > MAX(h.horas_dia) THEN 'MÁS'
                    WHEN SUM(v.horas_trabajadas) < MAX(h.horas_dia) THEN 'MENOS'
                    ELSE 'EXACTO'
                END as estado_trabajo_dia
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
                AND v.fecha = %s
                AND v.id_usuario = %s
        """
        
        print(f"DEBUG: Ejecutando consulta resumen con parámetros: {id_sucursal}, {id_colaborador}, {fecha}, {usuario_id}")
        cursor.execute(sql_resumen, (id_sucursal, id_colaborador, fecha, usuario_id))
        resumen = cursor.fetchone()
        print(f"DEBUG: Resumen obtenido: {resumen}")
        
        cursor.close()
        conn.close()
        
        print(f"DEBUG: Intentando serializar resumen: {resumen}")
        print(f"DEBUG: Intentando serializar actividades: {actividades}")
        
        # Convertir tipos de datos problemáticos para JSON
        if resumen:
            for key, value in resumen.items():
                if isinstance(value, (datetime, date)):
                    resumen[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    resumen[key] = float(value)
        
        if actividades:
            for actividad in actividades:
                for key, value in actividad.items():
                    if isinstance(value, (datetime, date)):
                        actividad[key] = value.isoformat()
                    elif isinstance(value, Decimal):
                        actividad[key] = float(value)
        
        return jsonify({
            "resumen_dia": resumen,
            "actividades": actividades
        }), 200
        
    except Exception as e:
        print(f"ERROR en obtener_detalle_actividades: {str(e)}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

