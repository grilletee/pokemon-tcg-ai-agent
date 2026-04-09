import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

cliente = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def preguntar_a_ia(pregunta_usuario):
    print("Pensando...")
    
    respuesta = cliente.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "Eres un asistente de Inteligencia Artificial experto, útil y que responde de forma concisa."
            },
            {
                "role": "user",
                "content": pregunta_usuario
            }
        ],
        model="llama-3.3-70b-versatile", 
    )
    
    return respuesta.choices[0].message.content

# --- ZONA DE PRUEBAS ---
if __name__ == "__main__":
    print("=== Mi Primer Agente IA ===")
    print("(Escribe 'salir' para cerrar el programa)\n")
    
    while True:
        mi_pregunta = input("👤 Tú: ")
        
        if mi_pregunta.lower() == "salir":
            print("IA: ¡Hasta la próxima! Ha sido un placer.")
            break
            
        respuesta_agente = preguntar_a_ia(mi_pregunta)
        print(f"IA: {respuesta_agente}\n")