from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from utils.validar_rut import validar_rut


trabajadores_bp = Blueprint('trabajadores_bp', __name__)

# Obtener trabajadores
@trabajadores_bp.route('', methods=['GET'])  
@jwt_required()
def obtener_trabajadores():
    try:
        id_contratista = request.args.get('id_contratista')
        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or usuario['sucursal_activa'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['sucursal_activa']

        base_query = """
            SELECT t.id, t.rut, t.nombre, t.apellido, t.nom_ap, 
                   t.id_tipo_trab, t.id_contratista, c.nombre AS nombre_contratista,
                   t.id_sucursal, t.id_estado, t.id_porcentaje
            FROM Trabajadores t
            LEFT JOIN Contratistas c ON t.id_contratista = c.id
            WHERE t.id_sucursal = %s
        """
        params = [id_sucursal]

        if id_contratista:
            base_query += " AND t.id_contratista = %s"
            params.append(id_contratista)

        base_query += " ORDER BY t.nom_ap ASC"

        cursor.execute(base_query, tuple(params))
        trabajadores = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(trabajadores), 200

    except Exception as e:
        print(f"❌ Error en obtener trabajadores: {e}")
        return jsonify({"error": str(e)}), 500


# 📌 Crear trabajador
@trabajadores_bp.route('/', methods=['POST'])
@jwt_required()
def crear_trabajador():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        rut = data.get("rut")
        print(f"🔍 RUT recibido desde frontend: {rut}")
        if not rut or not validar_rut(rut):
            return jsonify({"error": "RUT inválido"}), 400


        # 🔹 Obtener sucursal activa del usuario logueado
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['sucursal_activa']:
            return jsonify({"error": "No se pudo obtener la sucursal activa"}), 400

        id_sucursal = usuario['sucursal_activa']

        sql = """
            INSERT INTO Trabajadores (
                id, rut, nombre, apellido, nom_ap, id_tipo_trab,
                id_contratista, id_sucursal, id_estado, id_porcentaje
            ) VALUES (UUID(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            data['rut'],
            data['nombre'],
            data['apellido'],
            data['nom_ap'],
            data['id_tipo_trab'],
            data['id_contratista'],
            id_sucursal,          # 🔹 Usar sucursal activa desde backend
            1,                    # 🔹 Estado activo por defecto
            data['id_porcentaje']
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Trabajador creado correctamente"}), 201
    except Exception as e:
        print(f"❌ Error al crear trabajador: {e}")
        return jsonify({"error": str(e)}), 500


# 📌 Editar trabajador (VERSIÓN FLEXIBLE)
@trabajadores_bp.route('/<string:trabajador_id>', methods=['PUT'])
@jwt_required()
def editar_trabajador(trabajador_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔸 Obtener trabajador actual
        cursor.execute("SELECT * FROM Trabajadores WHERE id = %s", (trabajador_id,))
        trabajador_actual = cursor.fetchone()

        if not trabajador_actual:
            return jsonify({"error": "Trabajador no encontrado"}), 404

        # 🔸 Conservar valores existentes si no se mandan en el request
        rut = data.get("rut", trabajador_actual["rut"])
        nombre = data.get("nombre", trabajador_actual["nombre"])
        apellido = data.get("apellido", trabajador_actual["apellido"])
        nom_ap = f"{nombre} {apellido}"
        id_contratista = data.get("id_contratista", trabajador_actual["id_contratista"])
        id_estado = data.get("id_estado", trabajador_actual["id_estado"])
        id_porcentaje = data.get("id_porcentaje", trabajador_actual["id_porcentaje"])
        id_tipo_trab = trabajador_actual["id_tipo_trab"]
        id_sucursal = trabajador_actual["id_sucursal"]
        
        # 🔸 Actualizar con los valores finales
        sql = """
            UPDATE Trabajadores 
            SET rut = %s, nombre = %s, apellido = %s, nom_ap = %s, 
                id_tipo_trab = %s, id_contratista = %s, id_sucursal = %s, id_estado = %s, 
                id_porcentaje = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            rut, nombre, apellido, nom_ap,
            id_tipo_trab, id_contratista, id_sucursal,
            id_estado, id_porcentaje, trabajador_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Trabajador actualizado correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
