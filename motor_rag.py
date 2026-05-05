import chromadb
from chromadb.utils import embedding_functions
import os
import warnings
import logging

os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def inicializar_base_vectorial():
    print("[*] Sincronizando Base de Datos Vectorial...")
    cliente_chroma = chromadb.PersistentClient(path="./bd_vectorial")
    funcion_embedding = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    coleccion = cliente_chroma.get_or_create_collection(
        name="tcg_privado",
        embedding_function=funcion_embedding
    )

    if not os.path.exists("documentacion_privada.txt"):
        print("[WARN] No se encontró documentacion_privada.txt")
        return

    with open("documentacion_privada.txt", "r", encoding="utf-8") as f:
        contenido = f.read()

    fragmentos = [p.strip() for p in contenido.split('\n\n') if p.strip()]
    ids = [f"id_{i}" for i in range(len(fragmentos))]

    # FIX: upsert en lugar de add.
    # add() falla si los IDs ya existen (cada arranque del agente intentaba reinsertar).
    # upsert() inserta si no existe, actualiza si existe. Idempotente por diseño.
    coleccion.upsert(documents=fragmentos, ids=ids)
    print(f"[INFO] Memoria privada sincronizada ({len(fragmentos)} fragmentos).")


def consultar_rag(pregunta: str) -> str:
    cliente_chroma = chromadb.PersistentClient(path="./bd_vectorial")
    funcion_embedding = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    try:
        coleccion = cliente_chroma.get_collection(
            name="tcg_privado",
            embedding_function=funcion_embedding
        )
        query = coleccion.query(query_texts=[pregunta], n_results=1)

        if query['documents'] and query['documents'][0]:
            return f"\n[FUENTE INTERNA ADJUNTA]\n{query['documents'][0][0]}\n"

    # FIX: bare except reemplazado por Exception con log.
    # Un except vacío traga cualquier error — incluyendo bugs reales — en silencio.
    # Así al menos sabes QUÉ falló cuando el RAG devuelve vacío inesperadamente.
    except Exception as e:
        print(f"[WARN] RAG no disponible: {e}")

    return ""


if __name__ == "__main__":
    inicializar_base_vectorial()