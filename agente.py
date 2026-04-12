import os
import json
import re
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from herramientas import buscar_carta_pokemon, analizar_tendencia_inversion, buscar_en_internet

load_dotenv()

# Definición de tools permitidas para el LLM
HERRAMIENTAS_DISPONIBLES = [
    {
        "type": "function",
        "function": {
            "name": "buscar_carta_pokemon",
            "description": "Busca datos en bruto de una carta Pokémon en la API oficial.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_carta": {"type": "string", "description": "SOLO el nombre del Pokémon (ej. 'Charizard'). NUNCA incluyas el nombre del set aquí."}
                },
                "required": ["nombre_carta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_tendencia_inversion",
            "description": "Herramienta financiera suprema. Úsala para calcular el valor real, histórico y gradado (PSA/BGS) de una carta. Cruza la API con datos reales de internet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_carta": {"type": "string", "description": "SOLO el nombre del Pokémon (ej. 'Charizard'). NUNCA incluyas el nombre del set aquí."}
                },
                "required": ["nombre_carta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_en_internet",
            "description": "Buscar en internet noticias, ganadores de torneos o novedades.",
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {"type": "string", "description": "Término de búsqueda (ej. noticias, campeonatos, torneos)"}
                },
                "required": ["consulta"]
            }
        }
    }
]

class AgenteTCG:
    def __init__(self):
        self.cliente = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        # Inyectamos el año actual en el contexto para evitar alucinaciones temporales
        fecha_actual = datetime.now().strftime("%Y")
        
        self.mensajes_chat = [
            {"role": "system", "content": f"""Rol: Analista financiero experto en Pokémon TCG.
Contexto: El año actual es {fecha_actual}.

Reglas Críticas de Ejecución (Si rompes una, fallas el sistema):
1. PROHIBIDO derivar la búsqueda al usuario, sugerir páginas web o decir "busca en internet". Tú debes dar la respuesta final.
2. Anclaje temporal: Al buscar el "último" mundial o evento, busca explícitamente "ganador mundial pokemon tcg 2024" (último evento con datos web estables), a menos que el usuario pida otro año.
3. Si la búsqueda web no devuelve el dato exacto (ej. falta el mazo del ganador), ESTÁS OBLIGADO a iterar y ejecutar otra Tool Call con términos diferentes.
4. Obligatorio invocar las herramientas mediante Tool Calls. No imprimir la intención de búsqueda en texto plano.
5. Tras usar 'buscar_en_internet', procesar los datos y redactar una respuesta natural. No devolver los enlaces ni el texto en bruto.
6. Manejo de errores: Si el usuario escribe algo incomprensible, un error tipográfico (ej. "salor") o un saludo básico, NO ejecutes ninguna herramienta. Responde simplemente pidiendo que aclare la pregunta."""}
        ]

    def preguntar_a_ia(self, pregunta_usuario: str) -> str:
        self.mensajes_chat.append({"role": "user", "content": pregunta_usuario})

        try:
            respuesta = self.cliente.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=self.mensajes_chat,
                tools=HERRAMIENTAS_DISPONIBLES,
                tool_choice="auto"
            )
            
            # choices devuelve una lista, extraemos el primer mensaje
            mensaje_ia = respuesta.choices[0].message
            
            if getattr(mensaje_ia, 'tool_calls', None):
                for tool_call in mensaje_ia.tool_calls:
                    argumentos = json.loads(tool_call.function.arguments)
                    
                    if tool_call.function.name == "buscar_carta_pokemon":
                        resultado_datos = buscar_carta_pokemon(argumentos.get("nombre_carta"))
                    elif tool_call.function.name == "analizar_tendencia_inversion":
                        resultado_datos = analizar_tendencia_inversion(argumentos.get("nombre_carta"))
                    elif tool_call.function.name == "buscar_en_internet":
                        resultado_datos = buscar_en_internet(argumentos.get("consulta"))
                    else:
                        resultado_datos = "Herramienta desconocida."
                    
                    self.mensajes_chat.append(mensaje_ia)
                    self.mensajes_chat.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": str(resultado_datos)
                    })
                    
                    respuesta_final = self.cliente.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=self.mensajes_chat
                    )
                    
                    respuesta_texto = respuesta_final.choices[0].message.content
                    self.mensajes_chat.append({"role": "assistant", "content": respuesta_texto})
                    return respuesta_texto
                    
            respuesta_texto_normal = mensaje_ia.content
            
            # FIX 1: Alucinación de Tool Call (Texto plano o XML de Llama)
            if respuesta_texto_normal and ('buscar_en_internet' in respuesta_texto_normal.lower() or '<function' in respuesta_texto_normal):
                termino_busqueda = ""
                
                # Si usa el formato XML nativo de Llama (como el bug del Charizard)
                if '<function' in respuesta_texto_normal:
                    match = re.search(r'<function[^>]*>(.*?)</function>', respuesta_texto_normal, re.IGNORECASE)
                    if match:
                        # Limpiamos todos los símbolos de programación raros (+, comillas, paréntesis)
                        termino_busqueda = re.sub(r'["\'\+\(\)\{\}\[\]:=]', ' ', match.group(1)).strip()
                        termino_busqueda = termino_busqueda.replace("consulta", "").strip()
                
                # Si usa el formato de texto plano clásico
                else:
                    busqueda = re.search(r'consulta["\'\s:={\\]+([^"\'\}]+)', respuesta_texto_normal, re.IGNORECASE)
                    if busqueda:
                        termino_busqueda = busqueda.group(1).strip()
                
                if termino_busqueda:
                    print(f"[*] Caza de alucinación XML exitosa. Buscando: {termino_busqueda}")
                    resultado_datos = buscar_en_internet(termino_busqueda)
                    
                    texto_limpio = re.sub(r'<[^>]+>', '', respuesta_texto_normal).strip() 
                    if not texto_limpio or "{" in texto_limpio or "(" in texto_limpio:
                        texto_limpio = f"Ampliando información de mercado sobre: {termino_busqueda}"
                        
                    self.mensajes_chat.append({"role": "assistant", "content": texto_limpio})
                    self.mensajes_chat.append({"role": "user", "content": f"Resultados web: {resultado_datos}\nSintetiza esto y dame una respuesta directa basada en los precios reales."})
                    
                    r_final = self.cliente.chat.completions.create(model="llama-3.3-70b-versatile", messages=self.mensajes_chat)
                    txt_final = r_final.choices[0].message.content
                    self.mensajes_chat.append({"role": "assistant", "content": txt_final})
                    return txt_final
                    
            self.mensajes_chat.append({"role": "assistant", "content": respuesta_texto_normal})
            return respuesta_texto_normal

        # FIX 2: Groq lanza 400 Bad Request si el array de mensajes tiene una secuencia no válida.
        except Exception as e:
            error_str = str(e)
            print(f"[!] Error de API. Posible estado corrupto, ejecutando rollback...")
            
            # Hacemos pop() del último input para no envenenar el contexto
            if self.mensajes_chat and self.mensajes_chat[-1]["role"] == "user":
                pregunta_original = self.mensajes_chat.pop()["content"]
            else:
                pregunta_original = "Sintetiza la información obtenida en la última consulta."
                
            if "failed_generation" in error_str:
                busqueda = re.search(r'"consulta":\s*"([^"]+)"', error_str)
                if busqueda:
                    print("[*] Relanzando búsqueda desde los logs...")
                    resultado_datos = buscar_en_internet(busqueda.group(1))
                    
                    # Contexto temporal para no romper la memoria principal
                    mensajes_temporales = self.mensajes_chat.copy()
                    mensajes_temporales.append({
                        "role": "user", 
                        "content": f"Usuario: '{pregunta_original}'.\nDatos extraídos: \n{resultado_datos}\n\nGenera una respuesta con estos datos sin incluir los enlaces."
                    })
                    
                    r_final = self.cliente.chat.completions.create(model="llama-3.3-70b-versatile", messages=mensajes_temporales)
                    txt_final = r_final.choices[0].message.content
                    
                    self.mensajes_chat.append({"role": "user", "content": pregunta_original})
                    self.mensajes_chat.append({"role": "assistant", "content": txt_final})
                    
                    return txt_final
            
            return f"Error crítico (400). El contexto se ha reiniciado por seguridad. Log: {error_str[:60]}..."

if __name__ == "__main__":
    print("TCG Agent CLI v1.3.0")
    print("Escribe 'exit' para salir.\n")
    
    agente = AgenteTCG()
    
    while True:
        try:
            mi_pregunta = input("> ")
            # Hemos añadido los errores tipográficos más comunes
            if mi_pregunta.lower() in ("salir", "exit", "quit", "salor", "sañir", "q", "sair", "exir", "salr"):
                print("\n[*] Cerrando sesión...")
                break
            
            if not mi_pregunta.strip():
                continue
                
            print(f"\n{agente.preguntar_a_ia(mi_pregunta)}\n")
            
        except KeyboardInterrupt:
            print("\n\n[*] Ejecución interrumpida por el usuario.")
            break