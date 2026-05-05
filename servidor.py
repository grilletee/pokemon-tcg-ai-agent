import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agente import AgenteTCG
from motor_rag import inicializar_base_vectorial


# ---------------------------------------------------------------------------
# Modelos de datos (contratos de la API)
# ---------------------------------------------------------------------------

class PeticionChat(BaseModel):
    mensaje: str
    # Si el cliente no manda session_id, generamos uno nuevo automáticamente.
    session_id: str = ""


class RespuestaChat(BaseModel):
    respuesta: str
    session_id: str  # Siempre devolvemos el session_id para que el cliente lo persista


# ---------------------------------------------------------------------------
# Estado global de sesiones
# ---------------------------------------------------------------------------

# Diccionario que mapea session_id → instancia de AgenteTCG.
# Cada sesión tiene su propio historial de conversación aislado.
sesiones: dict[str, AgenteTCG] = {}


def obtener_o_crear_sesion(session_id: str) -> tuple[AgenteTCG, str]:
    """
    Devuelve la sesión existente o crea una nueva.
    Retorna tupla (agente, session_id) porque el session_id puede haber
    sido generado aquí si el cliente no mandó uno.
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    if session_id not in sesiones:
        print(f"[*] Nueva sesión creada: {session_id[:8]}...")
        sesiones[session_id] = AgenteTCG()

    return sesiones[session_id], session_id


# ---------------------------------------------------------------------------
# Lifespan: código que corre al arrancar y al cerrar el servidor
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializamos el RAG una sola vez al levantar el servidor.
    # Si lo hiciéramos en cada AgenteTCG.__init__() cargaríamos el modelo
    # de embeddings repetidamente — un coste innecesario.
    print("[*] Arrancando servidor TCG Agent...")
    inicializar_base_vectorial()
    print("[*] Servidor listo.\n")
    yield
    print("\n[*] Cerrando servidor...")


# ---------------------------------------------------------------------------
# Aplicación FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="TCG Agent API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS: permite peticiones desde cualquier origen en desarrollo.
# En producción sustituye ["*"] por tu dominio concreto.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Comprueba que el servidor está vivo y cuántas sesiones hay activas."""
    return {
        "estado": "ok",
        "sesiones_activas": len(sesiones)
    }


@app.post("/chat", response_model=RespuestaChat)
async def chat(peticion: PeticionChat):
    """
    Endpoint principal. Recibe un mensaje y devuelve la respuesta del agente.

    El cliente debe persistir el session_id que recibe en la primera respuesta
    y mandarlo en todas las peticiones siguientes para mantener el contexto.
    """
    if not peticion.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    agente, session_id = obtener_o_crear_sesion(peticion.session_id)

    # asyncio.to_thread ejecuta la función síncrona bloqueante en un thread
    # separado, liberando el event loop de FastAPI para otras peticiones.
    respuesta = await asyncio.to_thread(agente.preguntar_a_ia, peticion.mensaje)

    return RespuestaChat(respuesta=respuesta, session_id=session_id)


@app.delete("/session/{session_id}")
async def eliminar_sesion(session_id: str):
    """
    Elimina una sesión y libera su historial de memoria.
    El frontend lo llama cuando el usuario pulsa 'Nueva conversación'.
    """
    if session_id not in sesiones:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")

    del sesiones[session_id]
    print(f"[*] Sesión eliminada: {session_id[:8]}...")
    return {"detail": "Sesión eliminada correctamente."}