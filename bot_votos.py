import requests
import sys

# 1. Configuración
# Reemplaza con tu URL real de Railway
URL_RAILWAY = "https://web-production-76138.up.railway.app/api/push-votos?token=unjbg_esis_2026"
URL_ONPE = "https://resultadoelectoral.onpe.gob.pe/presentacion-backend/resumen-general/participantes?idEleccion=10&tipoFiltro=eleccion"

def ejecutar_robot():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://resultadoelectoral.onpe.gob.pe/'
    }
    
    try:
        # Obtener datos de ONPE
        response = requests.get(URL_ONPE, headers=headers, timeout=20)
        data = response.json()['data']
        
        # Filtrar por los códigos de partido (RP: 35, JPP: 10)
        rp = next(p for p in data if p['codigoAgrupacionPolitica'] == 35)
        jpp = next(p for p in data if p['codigoAgrupacionPolitica'] == 10)
        
        # Enviar a Railway
        payload = {
            "votos_rp": rp['totalVotosValidos'],
            "votos_jpp": jpp['totalVotosValidos']
        }
        r_push = requests.post(URL_RAILWAY, json=payload)
        print(f"Éxito: {r_push.json()}")
        
    except Exception as e:
        print(f"Fallo en el robot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ejecutar_robot()
