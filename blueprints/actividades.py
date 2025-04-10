import datetime
from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta


actividades_bp = Blueprint('actividades_bp', __name__)

@actividades_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_actividades():
    try:
        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ✅ Usar la sucursal activa del usuario logueado
        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or usuario['sucursal_activa'] is None:
            print("⚠️ No se encontró la sucursal activa del usuario")
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['sucursal_activa']
        usuario_id = str(usuario_id)

        print(f"🟢 usuario_id: {usuario_id} ({type(usuario_id)})")
        print(f"🟢 sucursal_activa: {id_sucursal} ({type(id_sucursal)})")

        sql = """
            SELECT 
                a.id, 
                a.fecha, 
                a.estado,
                a.id_especie,
                a.id_variedad,
                a.id_ceco,
                a.id_labor,
                a.id_unidad,
                a.id_tipo_trab,
                a.id_tipo_rend,
                a.id_contratista,
                a.id_sucursal,
                a.hora_inicio,
                a.hora_fin,
                a.horas_trab,
                a.tarifa,
                a.OC,
                l.nombre AS labor, 
                c.nombre AS ceco,
                co.nombre AS contratista, 
                tr.tipo AS tipo_rend 
            FROM Actividades a
            LEFT JOIN Labores l ON a.id_labor = l.id
            LEFT JOIN Maestro_Cecos c ON a.id_ceco = c.id
            LEFT JOIN Contratistas co ON a.id_contratista = co.id
            LEFT JOIN Tipo_Rendimientos tr ON a.id_tipo_rend = tr.id
            WHERE a.id_usuario = %s 
                AND a.estado = 'creada'
                AND a.id_sucursal = %s
        """

        cursor.execute(sql, (usuario_id, id_sucursal))
        actividades = cursor.fetchall()

        for actividad in actividades:
            if 'fecha' in actividad and isinstance(actividad['fecha'], (date, datetime)):
                actividad['fecha'] = actividad['fecha'].strftime('%Y-%m-%d')

            if isinstance(actividad['hora_inicio'], timedelta):
                actividad['hora_inicio'] = str(actividad['hora_inicio'])
            if isinstance(actividad['hora_fin'], timedelta):
                actividad['hora_fin'] = str(actividad['hora_fin'])
            if isinstance(actividad['horas_trab'], timedelta):
                actividad['horas_trab'] = str(actividad['horas_trab'])

        cursor.close()
        conn.close()

        return jsonify(actividades), 200

    except Exception as e:
        print(f"❌ Error al obtener actividades: {e}")
        return jsonify({"error": str(e)}), 500

    

# 🚀 Endpoint para crear una nueva actividad
@actividades_bp.route('/', methods=['POST'])
@jwt_required()
def crear_actividad():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        # Obtener sucursal activa del usuario
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['sucursal_activa']:
            cursor.close()
            conn.close()
            return jsonify({"error": "Sucursal activa no encontrada"}), 400

        id_sucursal = usuario['sucursal_activa']

        # Extraer otros datos
        fecha = data.get('fecha')
        id_especie = data.get('id_especie')
        id_variedad = data.get('id_variedad')
        id_ceco = data.get('id_ceco')
        id_labor = data.get('id_labor')
        id_unidad = data.get('id_unidad')
        id_tipo_trab = data.get('id_tipo_trab')
        id_contratista = data.get('id_contratista')
        id_tipo_rend = data.get('id_tipo_rend')
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        horas_trab = data.get('horas_trab')
        estado = data.get('estado', 'creada')
        tarifa = data.get('tarifa')
        oc = data.get('OC', "0")

        # Validación
        if not all([fecha, id_especie, id_variedad, id_ceco, id_labor, id_unidad,
                    id_tipo_trab, id_contratista, id_tipo_rend, id_sucursal, horas_trab, tarifa]):
            cursor.close()
            conn.close()
            return jsonify({"error": "Faltan datos obligatorios"}), 400

        # Insertar actividad
        cursor = conn.cursor()
        sql = """
            INSERT INTO Actividades (
                id, fecha, id_usuario, id_especie, id_variedad, id_ceco, id_labor, 
                id_unidad, id_tipo_trab, id_contratista, id_tipo_rend, id_sucursal, 
                hora_inicio, hora_fin, horas_trab, estado, tarifa, OC
            ) VALUES (UUID(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (fecha, usuario_id, id_especie, id_variedad, id_ceco, id_labor,
                   id_unidad, id_tipo_trab, id_contratista, id_tipo_rend, id_sucursal,
                   hora_inicio, hora_fin, horas_trab, estado, tarifa, oc)

        cursor.execute(sql, valores)
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Actividad creada correctamente"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# 🚀 Endpoint para editar una actividad existente
@actividades_bp.route('/<string:actividad_id>', methods=['PUT'])
@jwt_required()
def editar_actividad(actividad_id):
    try:
        usuario_id = get_jwt_identity()  # Obtener el ID del usuario autenticado
        data = request.json  # Datos enviados desde el frontend

        # Extraer datos a actualizar
        fecha = data.get('fecha')
        id_especie = data.get('id_especie')
        id_variedad = data.get('id_variedad')
        id_ceco = data.get('id_ceco')
        id_labor = data.get('id_labor')
        id_unidad = data.get('id_unidad')
        id_tipo_trab = data.get('id_tipo_trab')
        id_contratista = data.get('id_contratista')
        id_tipo_rend = data.get('id_tipo_rend')
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        tarifa = data.get('tarifa')

        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()

        # ✅ Verificar que la actividad pertenece al usuario autenticado
        cursor.execute("SELECT id FROM Actividades WHERE id = %s AND id_usuario = %s", (actividad_id, usuario_id))
        actividad = cursor.fetchone()

        if not actividad:
            return jsonify({"error": "No tienes permisos para editar esta actividad"}), 403

        # ✅ Actualizar los datos en la base de datos
        sql = """
            UPDATE Actividades 
            SET fecha = %s, id_especie = %s, id_variedad = %s, id_ceco = %s, 
                id_labor = %s, id_unidad = %s, id_tipo_trab = %s, id_contratista = %s, 
                id_tipo_rend = %s, hora_inicio = %s, hora_fin = %s, tarifa = %s 
            WHERE id = %s
        """
        valores = (fecha, id_especie, id_variedad, id_ceco, id_labor, id_unidad, id_tipo_trab,
                   id_contratista, id_tipo_rend, hora_inicio, hora_fin, tarifa, actividad_id)

        cursor.execute(sql, valores)
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Actividad actualizada correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
