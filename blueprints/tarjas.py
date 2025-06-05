from flask import Blueprint, jsonify, request
from utils.db import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

tarjas_bp = Blueprint('tarjas_bp', __name__)

@tarjas_bp.route('/', methods=['GET'])
@jwt_required()
def obtener_tarjas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Tarjas")
        tarjas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(tarjas), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@tarjas_bp.route('/', methods=['POST'])
@jwt_required()
def crear_tarja():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        # Aquí irá la lógica para crear una tarja
        cursor.close()
        conn.close()
        return jsonify({"message": "Tarja creada correctamente"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500 