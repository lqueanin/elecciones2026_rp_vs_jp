import os
import sqlite3
import requests
from flask import Flask, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
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

# --- LÓGICA DE MONITOREO CON PROXY DE GOOGLE ---
def actualizar_datos_onpe():
    # PEGA AQUÍ LA URL QUE COPIASTE DE GOOGLE APPS SCRIPT
    PROXY_URL = 'https://script.google.com/macros/s/AKfycbyFjvjFSM_FcQqKeliwSPZfqPivdmdvCLOFk2xogAhV_SItwO7hCaff7OHBZ7YY-Jc/exec' 
    
    try:
        # Ya no necesitamos cloudscraper aquí porque Google hace el trabajo sucio
        response = requests.get(PROXY_URL, timeout=30)
        
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get('success') and json_data.get('data'):
                datos = json_data['data']
                rp = next((p for p in datos if p['codigoAgrupacionPolitica'] == 35), None)
                jpp = next((p for p in datos if p['codigoAgrupacionPolitica'] == 10), None)

                if rp and jpp:
                    v_rp = rp['totalVotosValidos']
                    v_jpp = jpp['totalVotosValidos']
                    dif = abs(v_rp - v_jpp)
                    hora_actual = datetime.now().strftime('%H:%M')

                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute('INSERT INTO historial_brecha (fecha, votos_rp, votos_jpp, diferencia) VALUES (?, ?, ?, ?)', 
                              (hora_actual, v_rp, v_jpp, dif))
                    conn.commit()
                    conn.close()
                    print(f"[{hora_actual}] Guardado mediante Proxy Google: Dif {dif}")
        else:
            print(f"Error en Proxy: {response.status_code}")
    except Exception as e:
        print(f"Fallo en la conexión al Proxy: {e}")

# --- INICIALIZACIÓN ---
init_db()
scheduler = BackgroundScheduler()
if not scheduler.get_jobs():
    scheduler.add_job(func=actualizar_datos_onpe, trigger="interval", minutes=5)
    scheduler.start()
    actualizar_datos_onpe()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/historial')
def obtener_historial():
    try:
        conn = get_db_connection() # Corregido para usar la función de conexión
        c = conn.cursor()
        c.execute('SELECT fecha, votos_rp, votos_jpp, diferencia FROM historial_brecha ORDER BY id ASC')
        filas = c.fetchall()
        conn.close()
        return jsonify([dict(fila) for fila in filas])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
