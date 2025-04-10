import datetime
from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta


rendimientos_bp = Blueprint('rendimientos_bp', __name__)

# 🚀 Endpoint para obtener rendimientos con datos completos
@rendimientos_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_rendimientos():
    try:
        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ✅ Usar sucursal_activa del usuario autenticado
        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or usuario['sucursal_activa'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['sucursal_activa']

        sql = """
            SELECT 
                r.id, r.fecha, r.id_usuario, r.id_actividad, r.id_trabajador, r.id_sucursal, 
                r.rendimiento, r.cant_trab, r.cant_con_papel, r.cant_sin_papel, 
                r.horas_trab, r.horas_extra, r.hr_trabajada,
                COALESCE(CONCAT(t.nombre, ' ', t.apellido), 'Sin trabajador') AS trabajador,
                COALESCE(a.id_labor, 'Sin labor') AS labor,
                COALESCE(c.nombre, 'Sin contratista') AS contratista
            FROM Rendimientos r
            LEFT JOIN Trabajadores t ON r.id_trabajador = t.id
            LEFT JOIN Actividades a ON r.id_actividad = a.id
            LEFT JOIN Contratistas c ON a.id_contratista = c.id
            WHERE r.id_usuario = %s AND r.id_sucursal = %s
        """

        cursor.execute(sql, (usuario_id, id_sucursal))
        rendimientos = cursor.fetchall()

        for rendimiento in rendimientos:
            if 'fecha' in rendimiento and isinstance(rendimiento['fecha'], (date, datetime)):
                rendimiento['fecha'] = rendimiento['fecha'].strftime('%Y-%m-%d')

            if isinstance(rendimiento['horas_trab'], timedelta):
                rendimiento['horas_trab'] = str(rendimiento['horas_trab'])

            if isinstance(rendimiento['horas_extra'], timedelta):
                rendimiento['horas_extra'] = str(rendimiento['horas_extra'])

            if isinstance(rendimiento['hr_trabajada'], timedelta):
                rendimiento['hr_trabajada'] = str(rendimiento['hr_trabajada'])

        cursor.close()
        conn.close()

        return jsonify(rendimientos), 200

    except Exception as e:
        print(f"❌ Error en obtener_rendimientos: {e}")
        return jsonify({"error": str(e)}), 500



@rendimientos_bp.route('/', methods=['POST'])
@jwt_required()
def crear_rendimiento():
    try:
        data = request.json  
        usuario_id = get_jwt_identity()

        if not isinstance(data, list):
            return jsonify({"error": "Se esperaba una lista de rendimientos"}), 400

        # 🔍 Validar que todos los elementos sean dicts
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return jsonify({"error": f"El elemento en índice {i} no es un objeto JSON válido"}), 400

        print(f"📥 Datos recibidos en API: {data}")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        # ✅ Obtener sucursal_activa del usuario logueado
        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or usuario['sucursal_activa'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['sucursal_activa']  # 🔐 Usar esta sucursal en todos los rendimientos

        sql = """
            INSERT INTO Rendimientos (
                id, fecha, id_usuario, id_actividad, id_trabajador, id_sucursal, 
                rendimiento, cant_trab, cant_con_papel, cant_sin_papel, horas_trab, horas_extra
            ) VALUES (UUID(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for rendimiento in data:
            fecha = rendimiento.get('fecha')
            id_actividad = rendimiento.get('id_actividad')
            id_trabajador = rendimiento.get('id_trabajador')
            rendimiento_valor = rendimiento.get('rendimiento')
            cant_trab = rendimiento.get('cant_trab', 1)
            cant_con_papel = rendimiento.get('cant_con_papel', 0)
            cant_sin_papel = rendimiento.get('cant_sin_papel', 0)
            horas_extra = rendimiento.get('horas_extra', "00:00:00")

            # ✅ Validar horas_trab
            horas_trab = rendimiento.get('horas_trab', "00:00:00")
            if isinstance(horas_trab, str) and ":" in horas_trab:
                try:
                    datetime.strptime(horas_trab, "%H:%M:%S")
                except ValueError:
                    horas_trab = "00:00:00"
            else:
                horas_trab = "00:00:00"

            if fecha is None or id_actividad is None or rendimiento_valor is None:
                print(f"❌ Error: Datos inválidos en rendimiento -> {rendimiento}")
                return jsonify({"error": "Faltan datos obligatorios en uno o más rendimientos"}), 400

            valores = (fecha, usuario_id, id_actividad, id_trabajador, id_sucursal, 
                       rendimiento_valor, cant_trab, cant_con_papel, cant_sin_papel, horas_trab, horas_extra)

            cursor.execute(sql, valores)

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Rendimientos creados correctamente"}), 201

    except Exception as e:
        print(f"❌ Error en API: {e}")
        return jsonify({"error": str(e)}), 500



# 🚀 Endpoint para editar un rendimiento existente
@rendimientos_bp.route('/<string:rendimiento_id>', methods=['PUT'])
@jwt_required()
def editar_rendimiento(rendimiento_id):
    try:
        usuario_id = get_jwt_identity()

        if not request.is_json:
            print("❌ El body recibido no es JSON válido.")
            return jsonify({"error": "El contenido debe ser JSON"}), 400

        data = request.get_json()

        # 📌 Verificar si el rendimiento pertenece al usuario
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id FROM Rendimientos 
            WHERE id = %s AND id_usuario = %s
        """, (rendimiento_id, usuario_id))
        rendimiento_existente = cursor.fetchone()

        if not rendimiento_existente:
            return jsonify({"error": "No tienes permisos para editar este rendimiento"}), 403

        # 📌 Obtener los datos recibidos
        fecha = data.get('fecha')
        id_trabajador = data.get('id_trabajador')
        rendimiento = data.get('rendimiento')
        cant_trab = data.get('cant_trab')
        cant_con_papel = data.get('cant_con_papel')
        cant_sin_papel = data.get('cant_sin_papel')
        horas_trab = data.get('horas_trab')
        horas_extra = data.get('horas_extra')
        hr_trabajada = data.get('hr_trabajada')

        # ✅ Logs de depuración
        print(f"📥 Datos recibidos para actualizar: {data}")
        print(f"🧾 ID trabajador recibido: {id_trabajador} ({type(id_trabajador)})")

        # 📌 Ejecutar actualización
        sql = """
            UPDATE Rendimientos 
            SET fecha = %s, id_trabajador = %s, rendimiento = %s, 
                cant_trab = %s, cant_con_papel = %s, cant_sin_papel = %s, 
                horas_trab = %s, horas_extra = %s
            WHERE id = %s
        """
        valores = (
            fecha, id_trabajador, rendimiento,
            cant_trab, cant_con_papel, cant_sin_papel,
            horas_trab, horas_extra,
            rendimiento_id
        )

        cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()

        print("✅ Rendimiento actualizado correctamente.")
        return jsonify({"message": "Rendimiento actualizado correctamente"}), 200

    except Exception as e:
        print(f"❌ Error en editar_rendimiento: {e}")
        return jsonify({"error": str(e)}), 500

