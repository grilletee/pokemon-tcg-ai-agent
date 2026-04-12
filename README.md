# TCG-Agent: Analista Autónomo para Pokémon TCG

Este proyecto consiste en un agente de inteligencia artificial autónomo diseñado para operar a través de terminal. Su función principal es actuar como un consultor financiero y experto en el metajuego de Pokémon Trading Card Game (TCG), integrando datos de APIs oficiales y búsquedas en tiempo real.

El agente utiliza el modelo **Llama-3.3-70b-versatile** a través de la infraestructura de Groq para procesar el lenguaje natural y ejecutar llamadas a herramientas de forma dinámica (Tool Use).

## Arquitectura del Sistema

La aplicación se ha diseñado siguiendo principios de modularidad para separar la lógica de razonamiento de las integraciones externas:

* **agente.py**: Contiene la lógica del cerebro del agente, la gestión del historial de conversación y los mecanismos de recuperación ante errores (error handling). Implementa un sistema de limpieza de estado para evitar la corrupción del contexto en caso de respuestas malformadas por parte del LLM.
* **herramientas.py**: Define la capa de servicios e integración. Centraliza las llamadas a la API de Pokémon TCG y la lógica de scraping/búsqueda mediante DuckDuckGo.

## Funcionalidades Principales

1. **Consulta de Cartas**: Acceso directo a la base de datos oficial de pokemontcg.io para obtener metadatos de cartas, rarezas y fechas de lanzamiento.
2. **Análisis de Inversión**: Pipeline que cruza datos de precios base (Raw) con registros de ventas reales en el mercado secundario (PriceCharting) para estimar el valor de cartas gradadas (PSA/BGS).
3. **Búsqueda en Tiempo Real**: Capacidad de monitorizar torneos internacionales, ganadores de mundiales y tendencias actuales del metajuego mediante navegación autónoma.
4. **Sistema de Resiliencia**: El agente incluye filtros por expresiones regulares para interceptar y corregir alucinaciones de formato (XML/JSON) típicas en modelos de lenguaje de gran tamaño.

## Requisitos Técnicos

* Python 3.10 o superior.
* Groq API Key (configurada en el entorno).
* Librerías: `groq`, `requests`, `python-dotenv`, `duckduckgo-search`.

## Instalación y Configuración

1. Clonar el repositorio:
```bash
git clone [https://github.com/grilletee/pokemon-tcg-ai-agent](https://github.com/grilletee/pokemon-tcg-ai-agent)
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
Crear un archivo `.env` en la raíz con el siguiente contenido:
```text
GROQ_API_KEY=tu_api_key_aqui
```

## Ejecución

Para iniciar el agente en modo interactivo:

```bash
python agente.py
```

## Notas de Desarrollo

* **Gestión de Contexto**: Se ha implementado un sistema de anclaje temporal para que el agente reconozca el año actual y evite sesgos de información obsoleta o contenido basura (SEO spam).
* **Modularidad**: El diseño permite añadir nuevas herramientas en `herramientas.py` y darlas de alta en el diccionario del agente sin necesidad de refactorizar el flujo principal de ejecución.