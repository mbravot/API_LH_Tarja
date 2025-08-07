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

