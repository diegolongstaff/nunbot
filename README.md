# NUNBot - Buscador Inteligente de Códigos NUN

NUNBot es una aplicación web en Streamlit para buscar códigos del **Nomenclador Único Nacional (NUN)** a partir de descripciones quirúrgicas en lenguaje natural.

## Qué hace

- Busca códigos NUN relevantes para descripciones como *"fractura de cadera con reducción abierta"*.
- Identifica la región anatómica de forma automática.
- Usa filtrado determinístico antes de llamar a OpenAI para reducir costo y errores.
- Valida las respuestas del modelo antes de mostrarlas.
- Tiene fallback determinístico si OpenAI falla o devuelve algo inválido.
- Muestra el código, la descripción y los honorarios asociados.
- Los honorarios del dataset corresponden a los valores referenciales de *marzo 2026*.
- Los cambios importantes quedan resumidos en `CHANGELOG.md`.

## Requisitos

- Python 3.11 o superior
- Una clave de OpenAI en `OPENAI_API_KEY`
- El archivo `nun_procedimientos.csv` junto al código

## Variables de entorno

Archivo recomendado: `.env.example`

Variables soportadas:

- `OPENAI_API_KEY` - obligatoria
- `NUNBOT_MODEL` - modelo OpenAI usado para inferencia/ranking
- `NUNBOT_TIMEOUT_SECONDS` - timeout de las llamadas
- `NUNBOT_RETRY_ATTEMPTS` - reintentos ante fallos transitorios
- `NUNBOT_MIN_QUERY_LENGTH` - longitud mínima de búsqueda
- `NUNBOT_MAX_QUERY_LENGTH` - longitud máxima de búsqueda
- `NUNBOT_TOP_CANDIDATES` - candidatos locales máximos para ranking
- `NUNBOT_PROMPT_CANDIDATES` - candidatos máximos enviados al prompt final

## Instalación local

1. Clonar el repositorio:

```bash
git clone https://github.com/diegolongstaff/nunbot.git
cd nunbot
```

2. Crear y activar un entorno virtual:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Configurar la clave de OpenAI:

```bash
export OPENAI_API_KEY="tu_clave_aqui"
```

5. Ejecutar la app:

```bash
streamlit run app.py
```

La app abrirá en `http://localhost:8501`.

## Ejecución con Docker Compose

1. Copiar el ejemplo de variables de entorno:

```bash
cp .env.example .env
```

2. Editar `.env` y completar `OPENAI_API_KEY`.

3. Levantar el servicio:

```bash
docker compose up --build
```

La app quedará disponible en `http://localhost:8501`.

## Cómo funciona la búsqueda

1. El usuario escribe una descripción del procedimiento.
2. La app valida la entrada.
3. Se intenta detectar la región anatómica localmente.
4. Si hace falta, OpenAI ayuda con la región.
5. La base se filtra por región y se arma una lista corta de candidatos.
6. OpenAI rerankea solo esa lista corta.
7. La respuesta se valida antes de mostrarse.
8. Si algo falla, NUNBot devuelve un fallback determinístico en lugar de romperse.

## Qué pasa si algo falla

- Si falta `OPENAI_API_KEY`, la app no inicia y muestra un mensaje claro.
- Si falta `nun_procedimientos.csv`, la app no inicia y muestra un mensaje claro.
- Si OpenAI falla al inferir región, NUNBot usa una búsqueda determinística de respaldo.
- Si OpenAI falla al rankear, NUNBot muestra candidatos determinísticos.
- Si el modelo devuelve códigos inválidos, se filtran antes de mostrarlos.

## Deployment notes

### Replit / producción

- Verificar que `nun_procedimientos.csv` esté en el mismo directorio del proyecto.
- Configurar `OPENAI_API_KEY` en el entorno de despliegue.
- Revisar que `NUNBOT_MODEL` y los límites de timeout/reintentos sean adecuados.
- La configuración de Streamlit está en `.streamlit/config.toml`.
- El app usa caché de Streamlit para reducir costo y mejorar respuesta.

### Seguridad y operación

- No guardar claves API en el código.
- No registrar prompts completos en logs de producción.
- Mantener `showErrorDetails = false` en despliegue público.
- Mantener `gatherUsageStats = false` si no se quieren métricas de uso.

## Tests

Ejecutar la suite básica:

```bash
python3.11 -m pytest -q
```

Cobertura actual:

- validación de consultas
- ranking local determinístico
- validación de respuesta de región
- validación de códigos sugeridos
- fallback cuando OpenAI falla
- prompt compacto y sin duplicados
- health checks de arranque

## Estructura del proyecto

```text
nunbot/
├── app.py
├── nunbot_core.py
├── nun_procedimientos.csv
├── tests/
├── requirements.txt
├── requirements_fixed.txt
├── .env.example
└── .streamlit/
    └── config.toml
```

## Región anatómica soportada

- **MS** → Miembro Superior
- **CO** → Columna
- **PC** → Pelvis y Cadera
- **RO** → Rodilla
- **PP** → Pierna y Pie

## Ejemplos de búsqueda

- fractura de cadera con reducción abierta
- fracture/luxación de muñeca con osteosíntesis
- forage de cadera
- luxación de rodilla con reparación ligamentaria

## Licencia

MIT
