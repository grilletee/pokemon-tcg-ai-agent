# TCG Agent — Analista Autónomo para Pokémon TCG

Agente de inteligencia artificial autónomo que actúa como consultor financiero y experto en el metajuego de **Pokémon Trading Card Game**. Integra un modelo de lenguaje con herramientas externas reales: API oficial de cartas, búsqueda web en tiempo real y una memoria privada vectorial con los datos del usuario.

Expuesto como API REST consumible desde un frontend web incluido en el proyecto.

---

## Stack Tecnológico

| Capa | Tecnología |
|---|---|
| LLM | Google Gemini 2.5 Flash (via `google-genai`) |
| Backend API | FastAPI + Uvicorn |
| Motor RAG | ChromaDB + Sentence Transformers (`all-MiniLM-L6-v2`) |
| Datos de cartas | [pokemontcg.io](https://pokemontcg.io) |
| Búsqueda web | DuckDuckGo Search (`duckduckgo-search`) |
| Frontend | HTML / CSS / JS (sin frameworks) |

---

## Arquitectura

```
index.html  (Frontend)
     │
     │  POST /chat  {mensaje, session_id}
     ▼
servidor.py  (FastAPI)
     │  Gestión de sesiones en memoria
     │  asyncio.to_thread → no bloquea el event loop
     ▼
agente.py  (AgenteTCG)
     │  Bucle de razonamiento multi-ronda con Gemini
     │  Retry automático con backoff exponencial (503)
     ├──▶ motor_rag.py       → ChromaDB (memoria privada del usuario)
     └──▶ herramientas.py    → pokemontcg.io + DuckDuckGo
```

### Módulos

- **`agente.py`** — Núcleo del agente. Gestiona el historial de conversación, el bucle de tool calling multi-ronda y la resiliencia ante errores de la API (retry con backoff exponencial para errores 503).
- **`servidor.py`** — Capa HTTP. Expone los endpoints REST, gestiona múltiples sesiones en paralelo (una instancia de `AgenteTCG` por `session_id`) e inicializa el RAG una sola vez al arrancar.
- **`herramientas.py`** — Capa de servicios. Encapsula las llamadas a la API de Pokémon TCG y la lógica de búsqueda web. El pipeline de análisis de inversión cruza datos de la API con ventas reales del mercado secundario (PriceCharting).
- **`motor_rag.py`** — Motor de memoria privada. Vectoriza `documentacion_privada.txt` con embeddings semánticos y expone una función de búsqueda por similitud. Usa `upsert` para ser idempotente entre reinicios.
- **`index.html`** — Frontend completo en un único archivo estático. Gestiona el `session_id`, el indicador de carga y la limpieza de sesión contra el endpoint `DELETE /session/{id}`.

---

## Funcionalidades

- **Consulta de cartas** — Metadatos, rarezas y precios Raw desde la API oficial de pokemontcg.io con fuzzy search.
- **Análisis de inversión** — Estimación de valor gradado (PSA 8 / PSA 9 / PSA 10) cruzando datos de la API con ventas reales en el mercado secundario.
- **Búsqueda en tiempo real** — Torneos, ganadores de mundiales y tendencias del metajuego vía DuckDuckGo.
- **Memoria privada (RAG)** — El agente consulta primero los datos personales del usuario (colección, precios de compra, estrategia de torneo) antes de buscar en fuentes externas.
- **Multi-sesión** — El servidor gestiona conversaciones paralelas aisladas, cada una con su propio historial.

---

## Requisitos

- Python 3.10+
- Google AI Studio API Key (gratuita en [aistudio.google.com](https://aistudio.google.com))

---

## Instalación

```bash
git clone https://github.com/grilletee/pokemon-tcg-ai-agent
cd pokemon-tcg-ai-agent

python -m venv env
# Windows:
env\Scripts\activate
# macOS/Linux:
source env/bin/activate

pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz:

```
GOOGLE_API_KEY=tu_api_key_de_google_ai_studio
```

Inicializa la base de datos vectorial con tu memoria privada:

```bash
python motor_rag.py
```

---

## Ejecución

### Modo API + Frontend (recomendado)

```bash
uvicorn servidor:app --reload
```

Abre `index.html` en el navegador. El frontend se conecta automáticamente al servidor en `localhost:8000`.

### Modo CLI

```bash
python agente.py
```

---

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del servidor y sesiones activas |
| `POST` | `/chat` | Envía un mensaje al agente |
| `DELETE` | `/session/{id}` | Elimina una sesión y libera su memoria |

### Ejemplo de petición

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje": "¿Cuánto vale mi Umbreon PSA 9?", "session_id": ""}'
```

```json
{
  "respuesta": "Según tus registros, tu Umbreon VMAX Alt Art PSA 9 fue comprado por 1000€...",
  "session_id": "1b503ccc-9311-4cfe-b069-9c8c1e0ced28"
}
```

---

## Memoria Privada

El archivo `documentacion_privada.txt` contiene los datos personales del usuario: colección de cartas, precios de compra y estrategia competitiva. El agente lo consulta siempre antes de buscar en fuentes externas.

Para actualizar la memoria tras modificar el archivo:

```bash
# Elimina la base vectorial anterior y regenera
python motor_rag.py
```

---

## Decisiones Técnicas

**¿Por qué `asyncio.to_thread()` en lugar de reescribir el agente como async?**
El cliente de Gemini es síncrono. Envolverlo en `to_thread` desacopla la capa de transporte (FastAPI async) de la lógica de negocio sin obligar a reescribir el agente completo.

**¿Por qué ChromaDB local en lugar de una solución cloud?**
Para un caso de uso personal con documentos privados, una base vectorial local persistente es más simple, más privada y suficiente. No hay dependencia de servicios externos para la memoria.

**¿Por qué gestión de sesiones en memoria en lugar de base de datos?**
El historial de conversación es efímero por diseño — no necesita persistir entre reinicios del servidor para este caso de uso. Un diccionario en memoria es la solución más simple que resuelve el problema.