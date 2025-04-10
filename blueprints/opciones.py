from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
#from blueprints.auth import token_requerido

opciones_bp = Blueprint('opciones_bp', __name__)

# Obtener especies filtradas por la sucursal activa del usuario autenticado
@opciones_bp.route('/especies', methods=['GET'])
@jwt_required()
def obtener_especies():
    try:
        usuario_id = get_jwt_identity()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Obtener sucursal activa del usuario
        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['sucursal_activa']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['sucursal_activa']

        cursor.execute("""
            SELECT DISTINCT E.id, E.nombre 
            FROM Especies E
            JOIN Maestro_Cecos MC ON E.id = MC.id_especie
            WHERE MC.id_sucursal = %s
            ORDER BY E.nombre ASC
        """, (id_sucursal,))

        especies = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(especies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Obtener variedades filtradas por especie y sucursal seleccionada
@opciones_bp.route('/variedades', methods=['GET'])
@jwt_required()
def obtener_variedades():
    try:
        id_especie = request.args.get('id_especie')

        if not id_especie:
            return jsonify({"error": "id_especie es requerido"}), 400

        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener sucursal activa del usuario autenticado
        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['sucursal_activa']:
            return jsonify({"error": "No se encontró sucursal activa del usuario"}), 400

        id_sucursal = usuario['sucursal_activa']

        # Obtener variedades según especie y sucursal activa
        cursor.execute("""
            SELECT DISTINCT v.id, v.nombre 
            FROM Variedades v
            JOIN Maestro_Cecos mc ON v.id = mc.id_variedad
            WHERE v.id_especie = %s AND mc.id_sucursal = %s
            ORDER BY v.nombre ASC
        """, (id_especie, id_sucursal))

        variedades = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(variedades), 200

    except Exception as e:
        print(f"❌ Error en obtener_variedades: {e}")
        return jsonify({"error": str(e)}), 500

    
    # Obtener cecos
@opciones_bp.route('/cecos', methods=['GET'])
@jwt_required()
def obtener_cecos():
    try:
        id_especie = request.args.get('id_especie')
        id_variedad = request.args.get('id_variedad')

        if not id_especie or not id_variedad:
            return jsonify({"error": "id_especie e id_variedad son requeridos"}), 400

        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener sucursal activa del usuario
        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['sucursal_activa']:
            return jsonify({"error": "No se encontró sucursal activa del usuario"}), 400

        id_sucursal = usuario['sucursal_activa']

        # Obtener CECOs según especie, variedad y sucursal activa
        cursor.execute("""
            SELECT id, nombre FROM Maestro_Cecos
            WHERE id_especie = %s AND id_variedad = %s AND id_sucursal = %s
            ORDER BY nombre ASC
        """, (id_especie, id_variedad, id_sucursal))

        cecos = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(cecos), 200
    except Exception as e:
        print(f"❌ Error en obtener_cecos: {e}")
        return jsonify({"error": str(e)}), 500


    # Obtener labores
@opciones_bp.route('/labores', methods=['GET'])
@jwt_required()
def obtener_labores():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM Labores ORDER BY nombre ASC")
        labores = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(labores), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
        # Obtener unidades
@opciones_bp.route('/unidades', methods=['GET'])
@jwt_required()
def obtener_unidades():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM Unidades ORDER BY nombre ASC")
        unidades = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(unidades), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

     # Obtener tipo trabajador
@opciones_bp.route('/tipotrabajadores', methods=['GET'])
@jwt_required()
def obtener_tipotrabajador():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, desc_tipo FROM Tipo_Trabajadores")
        tipotrabajador = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(tipotrabajador), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
  # Obtener contratistas según la sucursal y tipo de trabajador del usuario logueado
@opciones_bp.route('/contratistas', methods=['GET'])
@jwt_required()
def obtener_contratistas():
    try:
        id_tipo_trab = request.args.get('id_tipo_trab')  # Filtro opcional

        usuario_id = get_jwt_identity()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Obtener sucursal_activa del usuario autenticado
        cursor.execute("SELECT sucursal_activa FROM Usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()

        if not usuario or not usuario['sucursal_activa']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400

        id_sucursal = usuario['sucursal_activa']

        # 🔹 Construir consulta SQL dinámica
        query = "SELECT id, nombre FROM Contratistas WHERE id_sucursal = %s"
        params = [id_sucursal]

        if id_tipo_trab:
            query += " AND id_tipo_trab = %s"
            params.append(id_tipo_trab)

        query += " ORDER BY nombre ASC"

        cursor.execute(query, tuple(params))
        contratistas = cursor.fetchall()

        cursor.close()
        conn.close()

        if not contratistas:
            print(f"⚠️ No se encontraron contratistas para sucursal: {id_sucursal} y tipo_trab: {id_tipo_trab}")

        return jsonify(contratistas), 200

    except Exception as e:
        print(f"❌ Error al obtener contratistas: {e}")
        return jsonify({"error": str(e)}), 500


    
    # Obtener tipo rendimiento
@opciones_bp.route('/tiporendimientos', methods=['GET'])
@jwt_required()
def obtener_tiporendimiento():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, tipo FROM Tipo_Rendimientos")
        tiporendimiento = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(tiporendimiento), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

 # Obtener sucursales
@opciones_bp.route('/sucursales', methods=['GET'])
@jwt_required()
def obtener_sucursales():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM Sucursales")
        sucursales = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(sucursales), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener porcentajes de trabajadores
@opciones_bp.route('/porcentajes', methods=['GET'])
@jwt_required()
def obtener_porcentajes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, porcentaje FROM Porcentaje_trabajador ORDER BY porcentaje ASC")
        porcentajes = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(porcentajes), 200
    except Exception as e:
        print(f"❌ Error al obtener porcentajes: {e}")
        return jsonify({"error": str(e)}), 500
