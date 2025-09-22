from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.db import get_db_connection
from utils.validar_rut import validar_rut
import uuid

colaboradores_bp = Blueprint('colaboradores_bp', __name__)

# Listar colaboradores (por sucursal activa del usuario)
@colaboradores_bp.route('', methods=['GET'])
@jwt_required()
def listar_colaboradores():
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
        # Listar colaboradores de la sucursal
        cursor.execute("""
            SELECT * FROM general_dim_colaborador
            WHERE id_sucursal = %s AND id_estado = 1
            ORDER BY nombre, apellido_paterno, apellido_materno ASC
        """, (id_sucursal,))
        colaboradores = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(colaboradores), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear colaborador
@colaboradores_bp.route('/', methods=['POST'])
@jwt_required()
def crear_colaborador():
    try:
        data = request.json
        usuario_id = get_jwt_identity()
        # Validar RUT si viene
        rut = data.get('rut')
        codigo_verificador = data.get('codigo_verificador')
        if rut and codigo_verificador and not validar_rut(str(rut) + codigo_verificador):
            return jsonify({"error": "RUT inválido"}), 400
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener sucursal activa del usuario
        cursor.execute("SELECT id_sucursalactiva FROM general_dim_usuario WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario or not usuario['id_sucursalactiva']:
            return jsonify({"error": "No se encontró la sucursal activa del usuario"}), 400
        id_sucursal = usuario['id_sucursalactiva']
        colaborador_id = str(uuid.uuid4())
        sql = """
            INSERT INTO general_dim_colaborador (
                id, nombre, apellido_paterno, apellido_materno, rut, codigo_verificador,
                id_sucursal, id_cargo, fecha_nacimiento, fecha_incorporacion,
                id_prevision, id_afp, id_estado
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            colaborador_id,
            data['nombre'],
            data['apellido_paterno'],
            data.get('apellido_materno'),
            data.get('rut'),
            data.get('codigo_verificador'),
            id_sucursal,
            data.get('id_cargo'),
            data.get('fecha_nacimiento'),
            data.get('fecha_incorporacion'),
            data.get('id_prevision'),
            data.get('id_afp'),
            data.get('id_estado', 1)
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Colaborador creado correctamente", "id": colaborador_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Editar colaborador
@colaboradores_bp.route('/<string:colaborador_id>', methods=['PUT'])
@jwt_required()
def editar_colaborador(colaborador_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Obtener colaborador actual
        cursor.execute("SELECT * FROM general_dim_colaborador WHERE id = %s", (colaborador_id,))
        colaborador_actual = cursor.fetchone()
        if not colaborador_actual:
            return jsonify({"error": "Colaborador no encontrado"}), 404
        # Validar RUT si se está modificando
        rut = data.get('rut', colaborador_actual['rut'])
        codigo_verificador = data.get('codigo_verificador', colaborador_actual['codigo_verificador'])
        if rut and codigo_verificador and not validar_rut(str(rut) + codigo_verificador):
            return jsonify({"error": "RUT inválido"}), 400
        # Conservar valores existentes si no se mandan en el request
        nombre = data.get('nombre', colaborador_actual['nombre'])
        apellido_paterno = data.get('apellido_paterno', colaborador_actual['apellido_paterno'])
        apellido_materno = data.get('apellido_materno', colaborador_actual['apellido_materno'])
        id_sucursalcontrato = data.get('id_sucursalcontrato', colaborador_actual['id_sucursalcontrato'])
        id_cargo = data.get('id_cargo', colaborador_actual['id_cargo'])
        fecha_nacimiento = data.get('fecha_nacimiento', colaborador_actual['fecha_nacimiento'])
        fecha_incorporacion = data.get('fecha_incorporacion', colaborador_actual['fecha_incorporacion'])
        id_prevision = data.get('id_prevision', colaborador_actual['id_prevision'])
        id_afp = data.get('id_afp', colaborador_actual['id_afp'])
        id_estado = data.get('id_estado', colaborador_actual['id_estado'])
        # Actualizar colaborador
        sql = """
            UPDATE general_dim_colaborador
            SET nombre = %s, apellido_paterno = %s, apellido_materno = %s, rut = %s, codigo_verificador = %s,
                id_sucursalcontrato = %s, id_cargo = %s, fecha_nacimiento = %s, fecha_incorporacion = %s,
                id_prevision = %s, id_afp = %s, id_estado = %s
            WHERE id = %s
        """
        cursor.execute(sql, (
            nombre,
            apellido_paterno,
            apellido_materno,
            rut,
            codigo_verificador,
            id_sucursalcontrato,
            id_cargo,
            fecha_nacimiento,
            fecha_incorporacion,
            id_prevision,
            id_afp,
            id_estado,
            colaborador_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Colaborador actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
