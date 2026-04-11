import requests
from ddgs import DDGS
from typing import Dict, Any, List

def buscar_carta_pokemon(nombre_carta: str) -> str:
    print(f"[*] GET a Pokémon TCG API: {nombre_carta}")
    url = f"https://api.pokemontcg.io/v2/cards?q=name:\"{nombre_carta}\"&pageSize=40"
    
    try:
        # Timeout de 10s para no bloquear el hilo principal si la API cae
        respuesta = requests.get(url, timeout=10)
        respuesta.raise_for_status() 
        
        datos = respuesta.json()
        
        # get() con lista vacía por defecto para evitar un "NullPointer" si no viene 'data'
        lista_cartas: List[Dict[str, Any]] = datos.get("data", []) 
        
        cartas_con_precio = [
            carta for carta in lista_cartas
            if carta.get("cardmarket", {}).get("prices", {}).get("averageSellPrice") is not None
        ]
        
        cartas_ordenadas = sorted(
            cartas_con_precio, 
            key=lambda x: x.get("cardmarket", {}).get("prices", {}).get("averageSellPrice", 0), 
            reverse=True
        )
        
        if not cartas_ordenadas:
            return f"Sin resultados con precio válido para {nombre_carta}."
            
        info_final = f"--- REPORTE DE MERCADO: {nombre_carta} ---\n\n"
        
        for carta in cartas_ordenadas[:5]:
            info_final += f"ID: {carta.get('id')} | Nombre: {carta.get('name')}\n"
            info_final += f"Set: {carta.get('set', {}).get('name')} ({carta.get('set', {}).get('releaseDate')})\n"
            info_final += f"Rareza: {carta.get('rarity', 'N/A')}\n"
            
            precio_base = float(carta.get("cardmarket", {}).get("prices", {}).get("averageSellPrice", 0))
            
            info_final += f"Proyección de mercado:\n"
            info_final += f"  > Raw:    {precio_base:.2f} EUR\n"
            info_final += f"  > PSA 8:  {precio_base * 1.5:.2f} EUR\n"
            info_final += f"  > PSA 9:  {precio_base * 3.5:.2f} EUR\n"
            info_final += f"  > PSA 10: {precio_base * 12.0:.2f} EUR\n\n"
            
        return info_final
        
    except requests.exceptions.RequestException as e:
        return f"Error HTTP o Timeout: {str(e)}"

def analizar_tendencia_inversion(nombre_carta: str) -> str:
    return buscar_carta_pokemon(nombre_carta)

def buscar_en_internet(consulta: str) -> str:
    print(f"[*] Buscando en DuckDuckGo: {consulta}")
    try:
        resultados = DDGS().text(consulta, max_results=5)
        info_final = f"--- RESULTADOS WEB: {consulta} ---\n\n"
        for r in resultados:
            info_final += f"Título: {r.get('title')}\nResumen: {r.get('body')}\nFuente: {r.get('href')}\n\n"
        return info_final
    except Exception as e:
        return f"Error en búsqueda web: {str(e)}"