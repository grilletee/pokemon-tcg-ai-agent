import requests

def buscar_carta_pokemon(nombre_carta):
    print(f"[INFO] Ejecutando peticion a Pokemon TCG API para: {nombre_carta}")
    
    url = f"https://api.pokemontcg.io/v2/cards?q=name:\"{nombre_carta}\"&pageSize=40"
    respuesta = requests.get(url)
    
    if respuesta.status_code == 200:
        datos = respuesta.json()
        lista_cartas = datos.get("data", list())
        
        cartas_con_precio = list()
        for c in lista_cartas:
            precios = c.get("cardmarket", dict()).get("prices", dict())
            if precios.get("averageSellPrice") is not None:
                cartas_con_precio.append(c)
        
        cartas_ordenadas = sorted(
            cartas_con_precio, 
            key=lambda x: x.get("cardmarket").get("prices").get("averageSellPrice"), 
            reverse=True
        )
        
        info_final = f"--- REPORTE DE MERCADO: {nombre_carta} ---\n\n"
        contador = int("0")
        
        for carta in cartas_ordenadas:
            if contador >= 5:
                break
            
            info_final += f"ID Carta: {carta.get('id')} | Nombre: {carta.get('name')}\n"
            datos_set = carta.get("set", dict())
            info_final += f"Set: {datos_set.get('name')} ({datos_set.get('releaseDate')})\n"
            info_final += f"Rareza: {carta.get('rarity', 'N/A')}\n"
            
            precios_cm = carta.get("cardmarket", dict()).get("prices", dict())
            precio_base = float(precios_cm.get("averageSellPrice"))
            
            info_final += f"Proyeccion de precios (Mercado Secundario):\n"
            info_final += f"  > Raw (Sin gradear): {precio_base:.2f} EUR\n"
            info_final += f"  > PSA 8 (NM-MT):     {precio_base * 1.5:.2f} EUR\n"
            info_final += f"  > PSA 9 (Mint):      {precio_base * 3.5:.2f} EUR\n"
            info_final += f"  > PSA 10 (Gem Mint): {precio_base * 12.0:.2f} EUR\n\n"
            
            contador += 1
            
        if contador == 0:
            return f"Sin resultados con precio valido para {nombre_carta}."
            
        return info_final
    else:
        return f" Fallo de conexion HTTP: {respuesta.status_code}"

def analizar_tendencia_inversion(nombre_carta):
    return buscar_carta_pokemon(nombre_carta)