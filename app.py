from flask import Flask, jsonify, render_template
import sqlite3
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os

app = Flask(__name__)

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
# Si existe la carpeta /data (volumen de Railway), lo usamos. 
# Si no, usamos la carpeta local (tu PC).
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

# 2. Tarea en segundo plano: Consultar ONPE y guardar en SQLite
def actualizar_datos_onpe():
    url = 'https://resultadoelectoral.onpe.gob.pe/presentacion-backend/resumen-general/participantes?idEleccion=10&tipoFiltro=eleccion'
    try:
        # Cabeceras avanzadas para simular un navegador real (Google Chrome en Windows)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-PE,es;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://resultadoelectoral.onpe.gob.pe/elecciones2026/', # Cambia el año si es necesario
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Validamos si la respuesta HTTP es exitosa (200 OK)
        if response.status_code == 200:
            try:
                json_data = response.json()
            except ValueError:
                print("Error: La respuesta fue 200 OK, pero no es un JSON válido.")
                return

            if json_data.get('success') and json_data.get('data'):
                datos = json_data['data']
                rp = next((p for p in datos if p['codigoAgrupacionPolitica'] == 35), None)
                jpp = next((p for p in datos if p['codigoAgrupacionPolitica'] == 10), None)

                if rp and jpp:
                    votos_rp = rp['totalVotosValidos']
                    votos_jpp = jpp['totalVotosValidos']
                    diferencia = abs(votos_rp - votos_jpp)
                    ahora = datetime.now().strftime('%H:%M')

                    # Guardar en base de datos
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO historial_brecha (fecha, votos_rp, votos_jpp, diferencia)
                        VALUES (?, ?, ?, ?)
                    ''', (ahora, votos_rp, votos_jpp, diferencia))
                    conn.commit()
                    conn.close()
                    print(f"[{ahora}] Datos actualizados. Diferencia: {diferencia}")
        else:
            print(f"Error HTTP {response.status_code}: La ONPE bloqueó la petición.")
            # Descomenta la siguiente línea si quieres ver el HTML que te están enviando para bloquearte:
            # print(response.text[:200]) 

    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")

# 3. Endpoints de Flask
@app.route('/')
def index():
    # Sirve el archivo index.html de la carpeta templates
    return render_template('index.html')

@app.route('/api/historial')
def obtener_historial():
    # Devuelve todos los registros de la base de datos al frontend
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT fecha, votos_rp, votos_jpp, diferencia FROM historial_brecha ORDER BY id ASC')
    filas = c.fetchall()
    conn.close()

    # Formatear a JSON
    resultado = []
    for fila in filas:
        resultado.append({
            'hora': fila[0],
            'votos_rp': fila[1],
            'votos_jpp': fila[2],
            'diferencia': fila[3]
        })
    
    return jsonify(resultado)

# 4. Arrancar la aplicación y el Scheduler
if __name__ == '__main__':
    init_db()
    
    # Hacemos una primera consulta inmediata al arrancar el server
    actualizar_datos_onpe() 
    
    # Configuramos el scheduler para que corra cada 5 minutos
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=actualizar_datos_onpe, trigger="interval", minutes=5)
    scheduler.start()

    # Desactivar el recargo automático (use_reloader=False) es importante 
    # para que el scheduler no se ejecute dos veces en modo desarrollo
    app.run(debug=True, use_reloader=False, port=5000)