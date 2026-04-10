import os
import json
from groq import Groq
from dotenv import load_dotenv
from herramientas import buscar_carta_pokemon, analizar_tendencia_inversion

load_dotenv()
cliente = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Definicion de herramientas
prop_buscar = dict()
prop_buscar["type"] = "string"
prop_buscar["description"] = "Nombre de la carta de Pokemon"

props_1 = dict()
props_1["nombre_carta"] = prop_buscar

params_1 = dict()
params_1["type"] = "object"
params_1["properties"] = props_1
params_1["required"] = list(["nombre_carta"])

func_1 = dict()
func_1["name"] = "buscar_carta_pokemon"
func_1["description"] = "Busca datos generales y precio base actual de una carta"
func_1["parameters"] = params_1

herr_1 = dict()
herr_1["type"] = "function"
herr_1["function"] = func_1

prop_inversion = dict()
prop_inversion["type"] = "string"
prop_inversion["description"] = "Nombre de la carta para analizar su inversion"

props_2 = dict()
props_2["nombre_carta"] = prop_inversion

params_2 = dict()
params_2["type"] = "object"
params_2["properties"] = props_2
params_2["required"] = list(["nombre_carta"])

func_2 = dict()
func_2["name"] = "analizar_tendencia_inversion"
func_2["description"] = "Ejecutar al solicitar analisis de inversion, historicos o valores PSA/BGS."
func_2["parameters"] = params_2

herr_2 = dict()
herr_2["type"] = "function"
herr_2["function"] = func_2

herramientas_disponibles = list([herr_1, herr_2])
mensajes_chat = list()

# System Prompt Profesional
mensaje_sistema = dict()
mensaje_sistema["role"] = "system"
mensaje_sistema["content"] = "Actua como un script de terminal enfocado en TCG Pokemon. No uses saludos, despedidas ni lenguaje conversacional. Devuelve unicamente los datos procesados, listas y valores numericos. Transcribe la informacion de las herramientas directamente."
mensajes_chat.append(mensaje_sistema)

def preguntar_a_ia(pregunta_usuario):
    nuevo_mensaje = dict()
    nuevo_mensaje["role"] = "user"
    nuevo_mensaje["content"] = pregunta_usuario
    mensajes_chat.append(nuevo_mensaje)

    respuesta = cliente.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=mensajes_chat,
        tools=herramientas_disponibles,
        tool_choice="auto"
    )
    
    cero = int("0")
    mensaje_ia = respuesta.choices[cero].message
    
    if mensaje_ia.tool_calls:
        for tool_call in mensaje_ia.tool_calls:
            argumentos = json.loads(tool_call.function.arguments)
            nombre_a_buscar = argumentos.get("nombre_carta")
            
            if tool_call.function.name == "buscar_carta_pokemon":
                resultado_datos = buscar_carta_pokemon(nombre_a_buscar)
            elif tool_call.function.name == "analizar_tendencia_inversion":
                resultado_datos = analizar_tendencia_inversion(nombre_a_buscar)
            
            mensajes_chat.append(mensaje_ia)
            
            mensaje_herramienta = dict()
            mensaje_herramienta["tool_call_id"] = tool_call.id
            mensaje_herramienta["role"] = "tool"
            mensaje_herramienta["name"] = tool_call.function.name
            mensaje_herramienta["content"] = str(resultado_datos)
            mensajes_chat.append(mensaje_herramienta)
            
            respuesta_final = cliente.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=mensajes_chat
            )
            
            respuesta_texto = respuesta_final.choices[cero].message.content
            
            mensaje_asistente = dict()
            mensaje_asistente["role"] = "assistant"
            mensaje_asistente["content"] = respuesta_texto
            mensajes_chat.append(mensaje_asistente)
            
            return respuesta_texto
            
    respuesta_texto_normal = mensaje_ia.content
    
    mensaje_asistente_normal = dict()
    mensaje_asistente_normal["role"] = "assistant"
    mensaje_asistente_normal["content"] = respuesta_texto_normal
    mensajes_chat.append(mensaje_asistente_normal)
    
    return respuesta_texto_normal

if __name__ == "__main__":
    print("TCG Agent CLI v1.0.0")
    print("Type 'exit' to quit.\n")
    
    while True:
        mi_pregunta = input("> ")
        
        if mi_pregunta.lower() in ["salir", "exit", "quit"]:
            break
            
        respuesta_agente = preguntar_a_ia(mi_pregunta)
        print(f"\n{respuesta_agente}\n")