import requests
from ddgs import DDGS
from typing import Dict, Any, List

def buscar_carta_pokemon(nombre_carta: str) -> str:
    print(f"[*] API Call (pokemontcg.io) -> {nombre_carta}")
    
    # Hack: Búsqueda flexible (Fuzzy Search) con comodines para evitar fallos por mayúsculas o espacios exactos
    termino_flexible = nombre_carta.replace(' ', '*')
    url = f"https://api.pokemontcg.io/v2/cards?q=name:*{termino_flexible}*&pageSize=40"
    
    try:
        # Timeout para evitar bloqueos del hilo
        respuesta = requests.get(url, timeout=10)
        respuesta.raise_for_status() 
        
        datos = respuesta.json()
        
        # Fallback a lista vacía para evitar KeyErrors
        lista_cartas: List[Dict[str, Any]] = datos.get("data", []) 
        
        # Filtrado de mercado (List Comprehension)
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
            return f"Not Found: Sin precios válidos para {nombre_carta}."
            
        info_final = f"--- RAW DATA: {nombre_carta} ---\n\n"
        
        # Limitamos a top 5 resultados
        for carta in cartas_ordenadas[:5]:
            info_final += f"ID: {carta.get('id')} | Nombre: {carta.get('name')}\n"
            info_final += f"Set: {carta.get('set', {}).get('name')} ({carta.get('set', {}).get('releaseDate')})\n"
            info_final += f"Rareza: {carta.get('rarity', 'N/A')}\n"
            
            precio_base = float(carta.get("cardmarket", {}).get("prices", {}).get("averageSellPrice", 0))
            
            # TODO: Mover estos multiplicadores a un motor dinámico en el futuro
            info_final += f"Estimación algorítmica:\n"
            info_final += f"  > Raw:    {precio_base:.2f} EUR\n"
            info_final += f"  > PSA 8:  {precio_base * 1.5:.2f} EUR\n"
            info_final += f"  > PSA 9:  {precio_base * 3.5:.2f} EUR\n"
            info_final += f"  > PSA 10: {precio_base * 12.0:.2f} EUR\n\n"
            
        return info_final
        
    except requests.exceptions.RequestException as e:
        return f"Fetch Error: {str(e)}"

def analizar_tendencia_inversion(nombre_carta: str) -> str:
    print(f"[*] Analizando mercado real e histórico para: {nombre_carta}")
    
    # 1. Extraemos los datos base para saber de qué carta exacta hablamos (Set, Rareza, Precio Raw)
    datos_base = buscar_carta_pokemon(nombre_carta)
    
    # Si la carta no existe, cortamos la ejecución
    if "Sin resultados" in datos_base or "Error" in datos_base:
        return datos_base
        
    lineas = datos_base.split('\n')
    info_clave_carta = ""
    for linea in lineas:
        if "Nombre:" in linea or "Set:" in linea:
        # split(':')[-1] falla si el valor tiene dos puntos (ej. fechas).
        # Usamos split(':', 1) para partir solo en el primer ':'.
            partes = linea.split(':', 1)
            if len(partes) > 1:
                info_clave_carta += partes[1].strip() + " "

    # Fallback: si no extrajimos nada, usamos el nombre original que recibió la función
    if not info_clave_carta.strip():
        info_clave_carta = nombre_carta
        
    termino_busqueda = f"{info_clave_carta.strip()} PSA 10 sold price PriceCharting"
    
    print(f"[*] Cruzando datos con mercado secundario: {termino_busqueda}")
    
    # 2. Hacemos una búsqueda web dirigida para extraer ventas reales de cartas gradadas
    datos_mercado = buscar_en_internet(termino_busqueda)
    
    # 3. Le entregamos al LLM el paquete completo de información real
    reporte_financiero = f"""
--- DATOS DE LA API OFICIAL (CARTAS SIN GRADEAR) ---
{datos_base}

--- DATOS DE MERCADO SECUNDARIO (BUSQUEDA EN TIEMPO REAL) ---
{datos_mercado}

Instrucción interna para el Agente: Analiza ambos bloques de datos. Compara el precio 'Raw' con los resultados encontrados en internet para versiones PSA/BGS. Si no encuentras el precio exacto de PSA en internet, DILO CLARAMENTE, no te inventes las matemáticas.
"""
    return reporte_financiero

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