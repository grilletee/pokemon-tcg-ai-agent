import os
import time
from datetime import datetime

from google import genai
from google.genai import types
from dotenv import load_dotenv

from herramientas import buscar_carta_pokemon, analizar_tendencia_inversion, buscar_en_internet
from motor_rag import consultar_rag

load_dotenv()

MODELO_LLM = "gemini-2.5-flash"
MAX_REINTENTOS_API = 4  # intentos ante error 503
MAX_RONDAS_AGENT = 5    # rondas máximas de tool calling


# ---------------------------------------------------------------------------
# Definición de herramientas
# ---------------------------------------------------------------------------

HERRAMIENTAS_GEMINI = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="buscar_carta_pokemon",
            description="Busca datos en bruto de una carta Pokémon en la API oficial.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "nombre_carta": types.Schema(
                        type="STRING",
                        description="SOLO el nombre del Pokémon base (ej. 'Umbreon'). Extrae la palabra EXACTA que escribió el usuario. NUNCA lo cambies ni lo corrijas por otro Pokémon."
                    )
                },
                required=["nombre_carta"]
            )
        ),
        types.FunctionDeclaration(
            name="analizar_tendencia_inversion",
            description="Herramienta financiera suprema. Úsala para calcular el valor real, histórico y gradado (PSA/BGS) de una carta. Cruza la API con datos reales de internet.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "nombre_carta": types.Schema(
                        type="STRING",
                        description="SOLO el nombre del Pokémon base (ej. 'Umbreon'). Extrae la palabra EXACTA que escribió el usuario. NUNCA lo cambies ni lo corrijas por otro Pokémon."
                    )
                },
                required=["nombre_carta"]
            )
        ),
        types.FunctionDeclaration(
            name="consultar_memoria_privada",
            description="Busca en la memoria privada del usuario. Úsala SIEMPRE PRIMERO para consultar su colección de cartas actual, sus precios de compra o sus estrategias de torneo.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "consulta": types.Schema(
                        type="STRING",
                        description="Pregunta o término a buscar en la memoria privada (ej. 'precio Umbreon', 'reglas torneo')."
                    )
                },
                required=["consulta"]
            )
        ),
        types.FunctionDeclaration(
            name="buscar_en_internet",
            description="Buscar en internet noticias, ganadores de torneos o novedades.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "consulta": types.Schema(
                        type="STRING",
                        description="Término de búsqueda (ej. noticias, campeonatos, torneos)"
                    )
                },
                required=["consulta"]
            )
        )
    ])
]


# ---------------------------------------------------------------------------
# Helper: llamada al modelo con retry ante 503
# ---------------------------------------------------------------------------

def _llamar_modelo(cliente, historial, config) -> any:
    """
    Envuelve generate_content con backoff exponencial para errores 503.
    Esperas: 2s, 4s, 8s, 16s antes de rendirse.
    """
    for intento in range(MAX_REINTENTOS_API):
        try:
            return cliente.models.generate_content(
                model=MODELO_LLM,
                contents=historial,
                config=config
            )
        except Exception as e:
            es_503 = "503" in str(e) or "UNAVAILABLE" in str(e)
            es_ultimo_intento = intento == MAX_REINTENTOS_API - 1

            if es_503 and not es_ultimo_intento:
                espera = 2 ** (intento + 1)  # 2s, 4s, 8s
                print(f"[!] Servidor saturado. Reintentando en {espera}s... ({intento + 1}/{MAX_REINTENTOS_API - 1})")
                time.sleep(espera)
            else:
                raise  # cualquier otro error o reintentos agotados: propagamos


# ---------------------------------------------------------------------------
# Dispatcher de tools
# ---------------------------------------------------------------------------

def _ejecutar_tool_call(nombre: str, argumentos: dict) -> str:
    if nombre == "buscar_carta_pokemon":
        return buscar_carta_pokemon(argumentos.get("nombre_carta"))

    elif nombre == "analizar_tendencia_inversion":
        return analizar_tendencia_inversion(argumentos.get("nombre_carta"))

    elif nombre == "buscar_en_internet":
        return buscar_en_internet(argumentos.get("consulta"))

    elif nombre == "consultar_memoria_privada":
        print("[*] Consultando Base de Datos Vectorial RAG...")
        resultado = consultar_rag(argumentos.get("consulta"))
        return resultado if resultado else "No hay datos sobre esto en la memoria privada. Busca en internet o en la API."

    else:
        return f"Error: Tool '{nombre}' no reconocida."


# ---------------------------------------------------------------------------
# Agente
# ---------------------------------------------------------------------------

class AgenteTCG:
    def __init__(self):
        fecha_actual = datetime.now().strftime("%Y")

        self.system_prompt = f"""Rol: Analista financiero experto en Pokémon TCG.
Contexto: El año actual es {fecha_actual}.

Reglas Críticas de Ejecución (Si rompes una, fallas el sistema):
1. ERES EL ÚNICO EXPERTO. Está TERMINANTEMENTE PROHIBIDO sugerir al usuario que busque en internet o que consulte a un experto humano. Si tras buscar no tienes datos, asume la responsabilidad y dile que el mercado no tiene registros actuales.
2. Anclaje temporal: Al buscar el "último" mundial o evento, busca explícitamente "ganador mundial pokemon tcg 2024" (último evento con datos web estables), a menos que el usuario pida otro año.
3. Si la búsqueda web no devuelve el dato exacto (ej. falta el mazo del ganador), ESTÁS OBLIGADO a iterar y ejecutar otra Tool Call con términos diferentes.
4. Obligatorio invocar las herramientas mediante Tool Calls. No imprimir la intención de búsqueda en texto plano.
5. Procesa los datos web y redacta una respuesta natural. Si encuentras precios contradictorios o sospechosamente bajos para un grado PSA 10, indícalo como una estimación y prioriza siempre la fuente más reciente o la lógica de mercado.
6. Manejo de errores: Si el usuario escribe algo incomprensible, un error tipográfico o un saludo básico, NO ejecutes ninguna herramienta. Responde simplemente pidiendo que aclare la pregunta.
7. Uso obligatorio de memoria privada: Si consultar_memoria_privada devuelve datos (precio de compra, estado de la carta, estrategia), DEBES usarlos en tu respuesta. Nunca ignores esos datos ni pidas al usuario información que ya está en la memoria."""

        self.cliente = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.historial: list[types.Content] = []

    def preguntar_a_ia(self, pregunta_usuario: str) -> str:
        self.historial.append(
            types.Content(role="user", parts=[types.Part(text=pregunta_usuario)])
        )

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            tools=HERRAMIENTAS_GEMINI
        )

        try:
            for _ in range(MAX_RONDAS_AGENT):
                respuesta = _llamar_modelo(self.cliente, self.historial, config)
                candidato = respuesta.candidates[0]

                tool_calls = [
                    part for part in candidato.content.parts
                    if part.function_call is not None
                ]

                if tool_calls:
                    self.historial.append(candidato.content)

                    partes_respuesta = []
                    for part in tool_calls:
                        fc = part.function_call
                        argumentos = dict(fc.args) if fc.args else {}
                        resultado = _ejecutar_tool_call(fc.name, argumentos)
                        print(f"[*] Tool ejecutada: {fc.name}")

                        partes_respuesta.append(
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=fc.name,
                                    response={"result": resultado}
                                )
                            )
                        )

                    self.historial.append(
                        types.Content(role="user", parts=partes_respuesta)
                    )
                    continue

                # Sin tool calls: respuesta final en texto
                texto_final = "".join(
                    part.text for part in candidato.content.parts
                    if hasattr(part, 'text') and part.text
                )

                if texto_final:
                    self.historial.append(
                        types.Content(role="model", parts=[types.Part(text=texto_final)])
                    )
                    return texto_final

                return "No se pudo generar una respuesta. Intenta de nuevo."

            return "El agente alcanzó el límite de rondas de razonamiento."

        except Exception as e:
            error_str = str(e)
            print(f"[!] Error: {error_str}")
            if self.historial and self.historial[-1].role == "user":
                self.historial.pop()
            return f"Error al procesar la solicitud. Intenta de nuevo. Log: {error_str[:80]}..."


if __name__ == "__main__":
    print("TCG Agent CLI v2.2.0 (Gemini 2.5 Flash)")
    print("Escribe 'exit' para salir.\n")

    agente = AgenteTCG()

    while True:
        try:
            mi_pregunta = input("> ")
            if mi_pregunta.lower() in ("salir", "exit", "quit", "q"):
                print("\n[*] Cerrando sesión...")
                break

            if not mi_pregunta.strip():
                continue

            print(f"\n{agente.preguntar_a_ia(mi_pregunta)}\n")

        except KeyboardInterrupt:
            print("\n\n[*] Ejecución interrumpida por el usuario.")
            break