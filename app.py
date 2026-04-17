import os
import sqlite3
from flask import Flask, jsonify, render_template, request
from datetime import datetime

app = Flask(__name__)

# Configuración de la base de datos en el volumen de Railway
if os.path.exists('/data'):
    DB_PATH = '/data/elecciones.db'
else:
    DB_PATH = 'elecciones.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS historial_brecha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            votos_rp INTEGER,
            votos_jpp INTEGER,
            diferencia INTEGER
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/api/push-votos', methods=['POST'])
def recibir_votos():
    # Token de seguridad para que solo el robot de GitHub pueda enviar datos
    token = request.args.get('token')
    if token != "unjbg_esis_2026":
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    data = request.json
    try:
        v_rp = data['votos_rp']
        v_jpp = data['votos_jpp']
        dif = abs(v_rp - v_jpp)
        hora_actual = datetime.now().strftime('%H:%M')

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO historial_brecha (fecha, votos_rp, votos_jpp, diferencia) VALUES (?, ?, ?, ?)', 
                  (hora_actual, v_rp, v_jpp, dif))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "hora": hora_actual})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/historial')
def obtener_historial():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT fecha, votos_rp, votos_jpp, diferencia FROM historial_brecha ORDER BY id ASC')
        filas = c.fetchall()
        conn.close()
        return jsonify([dict(fila) for fila in filas])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
