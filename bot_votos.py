import requests
import sys

# 1. Asegúrate de que esta URL sea la de tu app de Railway
URL_RAILWAY = "https://web-production-76138.up.railway.app/api/push-votos?token=unjbg_esis_2026"
URL_ONPE = "https://resultadoelectoral.onpe.gob.pe/presentacion-backend/resumen-general/participantes?idEleccion=10&tipoFiltro=eleccion"

def ejecutar_robot():
    # Cabeceras de un navegador real para engañar al servidor
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-PE,es;q=0.9,en-US;q=0.8,en;q=0.7',
        'Origin': 'https://resultadoelectoral.onpe.gob.pe',
        'Referer': 'https://resultadoelectoral.onpe.gob.pe/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    }
    
    try:
        print("Intentando conectar con la ONPE...")
        session = requests.Session()
        # Primero "visitamos" la página principal para obtener cookies básicas
        session.get("https://resultadoelectoral.onpe.gob.pe/", headers=headers, timeout=15)
        
        # Ahora pedimos los datos
        res = session.get(URL_ONPE, headers=headers, timeout=15)
        
        if res.status_code == 200:
            try:
                json_data = res.json()
                print("¡Datos obtenidos con éxito!")
                
                datos = json_data['data']
                rp = next(p for p in datos if p['codigoAgrupacionPolitica'] == 35)
                jpp = next(p for p in datos if p['codigoAgrupacionPolitica'] == 10)
                
                payload = {
                    "votos_rp": rp['totalVotosValidos'],
                    "votos_jpp": jpp['totalVotosValidos']
                }
                
                print(f"Enviando a Railway: {payload}")
                r_push = requests.post(URL_RAILWAY, json=payload, timeout=15)
                print(f"Respuesta de Railway: {r_push.status_code} - {r_push.text}")
                
            except Exception:
                print(f"ERROR: La ONPE bloqueó la IP de GitHub. Respondió con HTML.")
                print(f"Primeros 100 caracteres de la respuesta: {res.text[:100]}")
                sys.exit(1)
        else:
            print(f"Error HTTP {res.status_code}. La ONPE denegó el acceso.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Fallo crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ejecutar_robot()
