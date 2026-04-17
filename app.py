import os
import sqlite3
import cloudscraper
from flask import Flask, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
# Si existe la carpeta /data (volumen de Railway), la usamos.
# Si no, usamos la carpeta local (tu PC).
if os.path.exists('/data'):
    DB_PATH = '/data/elecciones.db'
else:
    DB_PATH = 'elecciones.db'

def get_db_connection():
    """Establece la conexión usando la ruta global corregida."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crea la tabla si no existe al arrancar la app."""
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

# --- LÓGICA DE MONITOREO (SCRAPPING) ---
def actualizar_datos_onpe():
    url = 'https://resultadoelectoral.onpe.gob.pe/presentacion-backend/resumen-general/participantes?idEleccion=10&tipoFiltro=eleccion'
    try:
        # Usamos cloudscraper para evitar bloqueos de la ONPE
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=15)
        
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get('success') and json_data.get('data'):
                datos = json_data['data']
                
                # Buscamos los partidos específicos por código
                rp = next((p for p in datos if p['codigoAgrupacionPolitica'] == 35), None)
                jpp = next((p for p in datos if p['codigoAgrupacionPolitica'] == 10), None)

                if rp and jpp:
                    v_rp = rp['totalVotosValidos']
                    v_jpp = jpp['totalVotosValidos']
                    dif = abs(v_rp - v_jpp)
                    hora_actual = datetime.now().strftime('%H:%M')

                    # Guardar en la base de datos
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO historial_brecha (fecha, votos_rp, votos_jpp, diferencia)
                        VALUES (?, ?, ?, ?)
                    ''', (hora_actual, v_rp, v_jpp, dif))
                    conn.commit()
                    conn.close()
                    print(f"[{hora_actual}] Datos actualizados: Dif {dif}")
        else:
            print(f"Error HTTP {response.status_code} al consultar la ONPE")
    except Exception as e:
        print(f"Error en la tarea de monitoreo: {e}")

# --- INICIALIZACIÓN AUTOMÁTICA (Para Gunicorn y Local) ---
# Esto se ejecuta siempre que la app se carga
init_db()
scheduler = BackgroundScheduler()
# Solo añadimos el job si no está ya activo
if not scheduler.get_jobs():
    scheduler.add_job(func=actualizar_datos_onpe, trigger="interval", minutes=5)
    scheduler.start()
    # Primera ejecución manual para no esperar 5 minutos
    actualizar_datos_onpe()

# --- RUTAS DE FLASK ---
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
        # Convertimos los resultados a una lista de diccionarios para JSON
        return jsonify([dict(fila) for fila in filas])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- SOLO PARA EJECUCIÓN LOCAL ---
if __name__ == '__main__':
    # Railway usa la variable de entorno PORT automáticamente
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)