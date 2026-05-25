from __future__ import annotations

import json
import logging
import os
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, cast

import pandas as pd
from openai import OpenAI

logger = logging.getLogger(__name__)

def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)


REGIONS = ("MS", "CO", "PC", "RO", "PP")
DEFAULT_MODEL = os.getenv("NUNBOT_MODEL", "gpt-4o")
DEFAULT_REGION_MAX_TOKENS = 250
DEFAULT_SEARCH_MAX_TOKENS = 1200
DEFAULT_TIMEOUT_SECONDS = _get_env_int("NUNBOT_TIMEOUT_SECONDS", 30)
DEFAULT_RETRY_ATTEMPTS = _get_env_int("NUNBOT_RETRY_ATTEMPTS", 2)
DEFAULT_MIN_QUERY_LENGTH = _get_env_int("NUNBOT_MIN_QUERY_LENGTH", 8)
DEFAULT_MAX_QUERY_LENGTH = _get_env_int("NUNBOT_MAX_QUERY_LENGTH", 500)
DEFAULT_TOP_CANDIDATES = _get_env_int("NUNBOT_TOP_CANDIDATES", 25)
DEFAULT_PROMPT_CANDIDATES = _get_env_int("NUNBOT_PROMPT_CANDIDATES", 12)

STOPWORDS = {
    "a",
    "al",
    "con",
    "de",
    "del",
    "el",
    "en",
    "la",
    "las",
    "los",
    "por",
    "para",
    "sin",
    "un",
    "una",
    "y",
}

REGION_HINTS = {
    "MS": {
        "hombro",
        "humero",
        "codo",
        "antebrazo",
        "muñeca",
        "muneca",
        "mano",
        "dedo",
        "clavicula",
        "clavícula",
        "radio",
        "cubito",
        "cúbito",
        "ulna",
    },
    "CO": {
        "columna",
        "cervical",
        "dorsal",
        "lumbar",
        "sacro",
        "vertebra",
        "vertebras",
        "vértebra",
        "vértebras",
    },
    "PC": {
        "pelvis",
        "cadera",
        "acetabulo",
        "acetábulo",
        "femur",
        "fémur",
        "coxofemoral",
        "trocanter",
        "trocánter",
    },
    "RO": {
        "rodilla",
        "rotula",
        "rótula",
        "patela",
        "femoral",
        "tibial",
        "menisco",
        "ligamento cruzado",
    },
    "PP": {
        "pierna",
        "pie",
        "tibia",
        "perone",
        "peroné",
        "peronee",
        "tobillo",
        "calcaneo",
        "calcáneo",
        "astragalo",
        "astrágalo",
        "metatarsiano",
        "falange",
        "talon",
        "talón",
    },
}


@dataclass(frozen=True)
class OpenAIResult:
    content: str
    raw: Any


def default_data_path() -> Path:
    return Path(__file__).resolve().with_name("nun_procedimientos.csv")


def check_runtime_health(
    data_path: str | Path | None = None,
    *,
    require_openai_key: bool = True,
) -> list[str]:
    issues: list[str] = []
    path = Path(data_path) if data_path else default_data_path()

    if not path.exists():
        issues.append(f"No se encontró el archivo de datos NUN en: {path}")

    if require_openai_key and not os.getenv("OPENAI_API_KEY"):
        issues.append("Falta la variable de entorno OPENAI_API_KEY.")

    return issues


def normalize_search_query(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_query(text: str) -> list[str]:
    tokens = [token for token in normalize_search_query(text).split() if token and token not in STOPWORDS]
    return tokens


def validate_search_query(
    text: str,
    min_length: int = DEFAULT_MIN_QUERY_LENGTH,
    max_length: int = DEFAULT_MAX_QUERY_LENGTH,
) -> tuple[bool, str]:
    normalized = normalize_search_query(text)
    if not normalized:
        return False, "Por favor ingrese una descripción del procedimiento."
    if len(normalized) < min_length or len(tokenize_query(normalized)) < 2:
        return False, "La descripción es demasiado breve. Intente con una búsqueda más específica."
    if len(normalized) > max_length:
        return False, "La descripción es demasiado larga. Intente resumirla y quedarse con los datos clínicos más importantes."
    if all(token.isdigit() for token in normalized.split()):
        return False, "La descripción es demasiado breve. Intente con una búsqueda más específica."
    return True, ""


def _clean_currency_column(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False).str.replace('"', "", regex=False)
    return pd.to_numeric(cleaned, errors="coerce").fillna(0)


def load_nun_data(csv_path: str | Path | None = None) -> pd.DataFrame:
    path = Path(csv_path) if csv_path else default_data_path()
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    for column in ("Cirujano", "Ayudantes", "Total"):
        if column in df.columns:
            df[column] = _clean_currency_column(df[column])

    return df


def _row_search_blob(row: pd.Series) -> str:
    parts = [str(row.get("Código", "")), str(row.get("Descripción", "")), str(row.get("Palabras clave", "")), str(row.get("Región", ""))]
    return normalize_search_query(" ".join(parts))


def _truncate_text(text: Any, max_length: int) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(value) <= max_length:
        return value
    return value[: max(0, max_length - 1)].rstrip() + "…"


def _format_candidate_row(row: dict[str, Any]) -> str:
    code = str(row.get("Código", "")).strip()
    description = _truncate_text(row.get("Descripción", ""), 110)
    keywords = _truncate_text(row.get("Palabras clave", ""), 70)

    parts = [code]
    if description:
        parts.append(description)
    if keywords:
        parts.append(f"Palabras clave: {keywords}")
    return " | ".join(parts)


def score_procedure_row(query: str, row: pd.Series, region: str | None = None) -> float:
    normalized_query = normalize_search_query(query)
    query_terms = tokenize_query(query)
    if not normalized_query or not query_terms:
        return 0.0

    description = normalize_search_query(str(row.get("Descripción", "")))
    keywords = normalize_search_query(str(row.get("Palabras clave", "")))
    code = normalize_search_query(str(row.get("Código", "")))
    row_region = str(row.get("Región", "")).strip().upper()
    blob = _row_search_blob(row)

    score = 0.0
    if region and row_region == region.upper():
        score += 3.0

    if normalized_query in description:
        score += 8.0
    if normalized_query in keywords:
        score += 6.0
    if normalized_query in code:
        score += 2.0

    description_terms = set(tokenize_query(str(row.get("Descripción", ""))))
    keyword_terms = set(tokenize_query(str(row.get("Palabras clave", ""))))
    overlap_description = description_terms.intersection(query_terms)
    overlap_keywords = keyword_terms.intersection(query_terms)

    score += len(overlap_description) * 1.5
    score += len(overlap_keywords) * 2.0

    # Mild boost for exact phrase fragments present anywhere in the row blob.
    for term in query_terms:
        if term in blob:
            score += 0.5

    return score


def rank_local_candidates(query: str, procedures_data: pd.DataFrame, region: str | None = None, limit: int = DEFAULT_TOP_CANDIDATES) -> list[dict[str, Any]]:
    if procedures_data.empty:
        return []

    working = procedures_data
    if region:
        working = working[working["Región"].astype(str).str.upper() == region.upper()]

    scored: list[tuple[float, int, dict[str, Any]]] = []
    for idx, (_, row) in enumerate(working.iterrows()):
        score = score_procedure_row(query, row, region=region)
        if score <= 0:
            continue
        scored.append((score, idx, row.to_dict()))

    if not scored:
        # Fallback to a safe slice of the region so the model still receives candidates.
        fallback = working.head(limit)
        return fallback.to_dict(orient="records")

    scored.sort(key=lambda item: (-item[0], str(item[2].get("Código", ""))))
    return [item[2] for item in scored[:limit]]


def determine_region_locally(query: str) -> tuple[str, float, str]:
    normalized = normalize_search_query(query)
    if not normalized:
        return "", 0.0, ""

    query_terms = set(tokenize_query(query))
    if not query_terms:
        return "", 0.0, ""

    best_region = ""
    best_score = 0
    for region, hints in REGION_HINTS.items():
        score = 0
        for hint in hints:
            normalized_hint = normalize_search_query(hint)
            if not normalized_hint:
                continue
            if normalized_hint in normalized:
                score += 2
            elif any(token == normalized_hint for token in query_terms):
                score += 1
        if score > best_score:
            best_score = score
            best_region = region

    if not best_region or best_score == 0:
        return "", 0.0, ""

    confidence = min(0.95, 0.45 + (best_score * 0.1))
    return best_region, round(confidence, 2), "Inferido localmente por coincidencia anatómica."


def validate_region_response(payload: dict[str, Any] | str | None) -> tuple[str, float, str]:
    if payload is None:
        return "", 0.0, ""

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return "", 0.0, ""

    if not isinstance(payload, dict):
        return "", 0.0, ""

    region = str(payload.get("region", "")).strip().upper()
    if region not in REGIONS:
        return "", 0.0, ""

    confidence = payload.get("confianza", 0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    reason = str(payload.get("motivo", "")).strip()
    return region, confidence, reason


def validate_suggested_codes(suggestions: Any, procedures_data: pd.DataFrame) -> list[dict[str, Any]]:
    if not isinstance(suggestions, list):
        return []

    allowed_codes = set(procedures_data["Código"].astype(str).tolist()) if "Código" in procedures_data.columns else set()
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in suggestions:
        if not isinstance(item, dict):
            continue
        code = str(item.get("codigo", "")).strip()
        if not code or code not in allowed_codes or code in seen:
            continue

        try:
            confidence = float(item.get("confianza", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        motive = str(item.get("motivo", "")).strip()
        cleaned.append({"codigo": code, "confianza": confidence, "motivo": motive})
        seen.add(code)
        if len(cleaned) >= 5:
            break

    return cleaned


def _with_timeout(client: OpenAI, timeout_seconds: int):
    if hasattr(client, "with_options"):
        return client.with_options(timeout=timeout_seconds)
    return client


def _parse_json_content(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def _chat_json_with_retry(
    client: OpenAI,
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
) -> dict[str, Any]:
    last_error: Exception | None = None
    request_client = _with_timeout(client, timeout_seconds)

    for attempt in range(retry_attempts + 1):
        try:
            completion_kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": temperature,
            }
            if str(model).startswith("gpt-5"):
                completion_kwargs["max_completion_tokens"] = max_tokens
            else:
                completion_kwargs["max_tokens"] = max_tokens

            response = request_client.chat.completions.create(**completion_kwargs)
            content = response.choices[0].message.content or "{}"
            return _parse_json_content(content)
        except Exception as exc:  # pragma: no cover - exercised via integration/runtime, not deterministic unit tests
            last_error = exc
            logger.warning("OpenAI request failed on attempt %s/%s: %s", attempt + 1, retry_attempts + 1, exc)
            if attempt < retry_attempts:
                time.sleep(0.5 * (2 ** attempt))

    if last_error:
        raise last_error
    return {}


def build_region_prompt(user_description: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "Eres un experto en anatomía traumatológica. Responde siempre en formato JSON válido.",
        },
        {
            "role": "user",
            "content": f"""
Eres un asistente médico especializado en traumatología y ortopedia. Tu tarea es determinar la región anatómica basándote en la descripción del procedimiento.

DESCRIPCIÓN DEL PROCEDIMIENTO:
"{user_description}"

GLOSARIO MÉDICO CONTEXTUAL - REGIONES ANATÓMICAS:
- **MS** → Miembro Superior (hombro, húmero, codo, antebrazo, muñeca, mano, dedos)
- **CO** → Columna (cervical, dorsal, lumbar, sacra, vertebras)
- **PC** → Pelvis y Cadera (fémur proximal, acetábulo, sacro, cadera)
- **RO** → Rodilla (patela, cóndilos femorales, platillos tibiales, ligamentos cruzados)
- **PP** → Pierna y Pie (tibia, peroné, tobillo, calcáneo, astrágalo, metatarsianos, falanges)

EJEMPLOS DE INTERPRETACIÓN:
- "fractura de cadera" → región PC
- "fractura de muñeca" → región MS
- "fractura de tobillo" → región PP
- "fractura de columna" → región CO
- "fractura de rodilla" → región RO
- "forage de cadera" → región PC

INSTRUCCIONES:
1. Analiza la descripción del procedimiento
2. Identifica la región anatómica más apropiada
3. Responde SOLO con el código de la región en formato JSON

FORMATO DE RESPUESTA (JSON obligatorio):
{{
    "region": "PC",
    "confianza": 0.95,
    "motivo": "Explicación breve de por qué esta región es correcta"
}}

IMPORTANTE:
- Responde SOLO en formato JSON
- La región debe ser exactamente: MS, CO, PC, RO, o PP
- La confianza debe ser un número entre 0 y 1
""".strip(),
        },
    ]


def build_search_prompt(user_description: str, candidate_procedures: pd.DataFrame | Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    if isinstance(candidate_procedures, pd.DataFrame):
        candidate_df = cast(pd.DataFrame, candidate_procedures)
        if "Código" in candidate_df.columns:
            rows = candidate_df.drop_duplicates(subset=["Código"], keep="first").to_dict(orient="records")
        else:
            rows = candidate_df.to_dict(orient="records")
    else:
        rows = list(candidate_procedures)

    compact_rows: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for row in rows:
        code = str(row.get("Código", "")).strip()
        if code and code in seen_codes:
            continue
        if code:
            seen_codes.add(code)
        compact_rows.append(row)

    procedures_text = "\n".join(_format_candidate_row(row) for row in compact_rows)

    return [
        {
            "role": "system",
            "content": "Eres un experto en códigos NUN para traumatología. Responde siempre en formato JSON válido.",
        },
        {
            "role": "user",
            "content": f"""
Eres un asistente médico especializado en traumatología y ortopedia. Tu tarea es encontrar los códigos NUN más apropiados para el procedimiento descrito.

DESCRIPCIÓN DEL PROCEDIMIENTO:
"{user_description}"

LISTA DE PROCEDIMIENTOS POSIBLES:
{procedures_text}

INSTRUCCIONES:
1. Analiza la descripción del procedimiento médico
2. Busca coincidencias EXACTAS en las descripciones primero
3. Identifica palabras clave médicas relevantes (anatomía, técnica quirúrgica, tipo de lesión, etc.)
4. Considera la complejidad y tipo de procedimiento
5. Devuelve EXACTAMENTE 3-5 códigos más probables, ordenados por relevancia y confianza

FORMATO DE RESPUESTA (JSON obligatorio):
{{
    "codigos_sugeridos": [
        {{
            "codigo": "PC.05.07",
            "motivo": "Explicación breve de por qué este código es relevante",
            "confianza": 0.95
        }}
    ]
}}

IMPORTANTE:
- Solo sugiere códigos que existan en la lista proporcionada
- Busca coincidencias EXACTAS en las descripciones antes que aproximadas
- La confianza debe ser un número entre 0 y 1
- Ordena por relevancia (más relevante primero)
- Responde SOLO en formato JSON
- Para "forage de cadera" busca específicamente códigos que contengan "forage" y "cadera"
""".strip(),
        },
    ]


def infer_region_with_openai(client: OpenAI, user_description: str, *, model: str = DEFAULT_MODEL) -> tuple[str, float, str]:
    payload = _chat_json_with_retry(
        client,
        model=model,
        messages=build_region_prompt(user_description),
        max_tokens=DEFAULT_REGION_MAX_TOKENS,
        temperature=0.2,
    )
    return validate_region_response(payload)


def rank_codes_with_openai(
    client: OpenAI,
    user_description: str,
    candidate_procedures: pd.DataFrame | Iterable[dict[str, Any]],
    *,
    model: str = DEFAULT_MODEL,
) -> list[dict[str, Any]]:
    payload = _chat_json_with_retry(
        client,
        model=model,
        messages=build_search_prompt(user_description, candidate_procedures),
        max_tokens=DEFAULT_SEARCH_MAX_TOKENS,
        temperature=0.3,
    )
    suggestions = payload.get("codigos_sugeridos", []) if isinstance(payload, dict) else []
    if not isinstance(suggestions, list):
        return []
    # We validate against the source dataframe in the caller.
    return suggestions


def search_nun_codes(
    client: OpenAI,
    user_description: str,
    procedures_data: pd.DataFrame,
    *,
    model: str = DEFAULT_MODEL,
    top_candidates: int = DEFAULT_TOP_CANDIDATES,
) -> tuple[str, float, str, list[dict[str, Any]], list[dict[str, Any]], bool]:
    used_fallback = False
    region, confidence, reason = determine_region_locally(user_description)
    if not region:
        try:
            region, confidence, reason = infer_region_with_openai(client, user_description, model=model)
        except Exception as exc:
            logger.warning("OpenAI region inference failed; using deterministic fallback: %s", exc)
            region, confidence, reason = "", 0.0, (
                "No se pudo inferir la región con OpenAI; se usará una búsqueda determinística de respaldo."
            )
            used_fallback = True

    if region:
        region_df = procedures_data[procedures_data["Región"].astype(str).str.upper() == region.upper()]
    else:
        region_df = procedures_data

    if "Código" in region_df.columns:
        region_df = region_df.drop_duplicates(subset=["Código"], keep="first")

    if region_df.empty:
        return region, confidence, reason, [], [], True

    local_candidates = rank_local_candidates(user_description, region_df, region=region, limit=top_candidates)
    prompt_limit = min(top_candidates, DEFAULT_PROMPT_CANDIDATES)
    prompt_candidates = local_candidates[:prompt_limit]
    candidate_df = pd.DataFrame(prompt_candidates) if prompt_candidates else region_df.head(prompt_limit)

    try:
        raw_suggestions = rank_codes_with_openai(client, user_description, candidate_df, model=model)
    except Exception as exc:  # pragma: no cover - integration/runtime path
        logger.warning("OpenAI ranking failed; using deterministic fallback: %s", exc)
        raw_suggestions = []
        used_fallback = True

    validated = validate_suggested_codes(raw_suggestions, procedures_data)
    if validated:
        return region, confidence, reason, validated, local_candidates, used_fallback

    # Fallback: use deterministic candidates when the model output is empty or malformed.
    fallback_candidates = candidate_df.head(5).to_dict(orient="records")
    fallback_results: list[dict[str, Any]] = []
    for row in fallback_candidates[:5]:
        fallback_results.append(
            {
                "codigo": str(row.get("Código", "")),
                "confianza": 0.5,
                "motivo": "Sugerencia de respaldo basada en coincidencia local determinística.",
            }
        )
    return region, confidence, reason, fallback_results, local_candidates, True
