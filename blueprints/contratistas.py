from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

contratistas_bp = Blueprint('contratistas_bp', __name__)

# 📌 Obtener lista de contratistas
@contratistas_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_contratistas():
    try:
        # Obtener ID del usuario autenticado
        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Obtener la sucursal ACTIVA del usuario
        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or usuario['sucursal_activa'] is None:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['sucursal_activa']

        # 🔹 Filtrar por la sucursal activa y obtener nombre de sucursal
        cursor.execute(
            """
            SELECT c.*, s.nombre as nombre_sucursal 
            FROM Contratistas c
            JOIN Sucursales s ON c.id_sucursal = s.id
            WHERE c.id_sucursal = %s 
            ORDER BY c.nombre ASC
            """,
            (id_sucursal,)
        )
        contratistas = cursor.fetchall()

        cursor.close()
        conn.close()

        if not contratistas:
            print(f"⚠️ No se encontraron contratistas para sucursal_activa: {id_sucursal}")

        return jsonify(contratistas), 200

    except Exception as e:
        print(f"❌ Error en obtener_contratistas: {e}")
        return jsonify({"error": str(e)}), 500



# 📌 Crear un nuevo contratista
@contratistas_bp.route('/', methods=['POST'])
@jwt_required()
def crear_contratista():
    try:
        data = request.json
        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Obtener sucursal activa del usuario autenticado
        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or usuario['sucursal_activa'] is None:
            return jsonify({"error": "No se pudo obtener la sucursal activa del usuario"}), 400

        id_sucursal = usuario['sucursal_activa']

        # 🔹 Crear contratista
        sql = """
            INSERT INTO Contratistas (id, rut, nombre, id_sucursal, id_tipo_trab, id_estado) 
            VALUES (UUID(), %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (data['rut'], data['nombre'], id_sucursal, 2, 1))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Contratista creado correctamente"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 📌 Editar contratista
@contratistas_bp.route('/<string:contratista_id>', methods=['PUT'])
@jwt_required()
def editar_contratista(contratista_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE Contratistas 
            SET rut = %s, nombre = %s, id_estado = %s
            WHERE id = %s
        """
        cursor.execute(sql, (data['rut'], data['nombre'], data['id_estado'], contratista_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Contratista actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
