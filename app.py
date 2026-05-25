import logging
import os
import re
import time
import uuid
from typing import Any

import streamlit as st
from openai import OpenAI

from nunbot_core import (
    check_runtime_health,
    load_nun_data as core_load_nun_data,
    normalize_search_query,
    search_nun_codes,
    validate_search_query,
)

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Buscador de Códigos NUN",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def init_openai_client():
    """Initialize OpenAI client with API key from environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("⚠️ API Key de OpenAI no encontrada. Verifique la variable de entorno OPENAI_API_KEY")
        st.stop()
    return OpenAI(api_key=api_key)


@st.cache_data(show_spinner=False)
def load_nun_data():
    """Load and cache the NUN dataset."""
    try:
        df = core_load_nun_data()
        logger.info("Loaded %s procedures from CSV", len(df))
        return df
    except FileNotFoundError:
        st.error("❌ Archivo 'nun_procedimientos.csv' no encontrado")
        st.stop()
    except Exception as exc:
        st.error(f"❌ Error al cargar el archivo CSV: {exc}")
        st.stop()


def _get_search_cache() -> dict[tuple[Any, ...], tuple[str, float, str, list[dict[str, Any]], list[dict[str, Any]], bool]]:
    if "nunbot_search_cache" not in st.session_state:
        st.session_state["nunbot_search_cache"] = {}
    return st.session_state["nunbot_search_cache"]


def _build_search_cache_key(user_input: str, procedures_data) -> tuple[Any, ...]:
    normalized_input = normalize_search_query(user_input)
    code_signature = hash(tuple(procedures_data["Código"].astype(str).tolist())) if "Código" in procedures_data.columns else 0
    return (normalized_input, os.getenv("NUNBOT_MODEL", "gpt-4o"), len(procedures_data), code_signature)


def _preview_query(text: str, limit: int = 120) -> str:
    normalized = normalize_search_query(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"


def _parse_intish(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    try:
        return int(float(text.replace(",", "")))
    except (TypeError, ValueError):
        return None


def _format_currency(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def _resolve_helper_pricing(row) -> tuple[int, float, float]:
    complexity = _parse_intish(row.get("Complejidad"))
    explicit_count = _parse_intish(row.get("Cantidad de ayudantes"))
    helper_count = explicit_count if explicit_count is not None else 0

    if helper_count == 0 and complexity is not None:
        if complexity <= 1:
            helper_count = 0
        elif complexity <= 4:
            helper_count = 1
        else:
            helper_count = 2

    total_helpers_amount = row.get("Total ayudantes", row.get("Ayudantes", 0))
    per_helper_amount = row.get("Honorario por ayudante", None)

    if per_helper_amount in (None, ""):
        per_helper_amount = 0.0
        if helper_count > 0:
            try:
                per_helper_amount = float(total_helpers_amount) / helper_count
            except (TypeError, ValueError, ZeroDivisionError):
                per_helper_amount = 0.0
    else:
        try:
            per_helper_amount = float(per_helper_amount)
        except (TypeError, ValueError):
            per_helper_amount = 0.0

    try:
        total_helpers_amount = float(total_helpers_amount)
    except (TypeError, ValueError):
        total_helpers_amount = 0.0

    return helper_count, per_helper_amount, total_helpers_amount


def display_results(suggested_codes, procedures_data):
    """Display the search results in a formatted way."""
    if not suggested_codes:
        st.warning("⚠️ No se encontraron códigos sugeridos. Intente con una descripción más específica.")
        return

    st.subheader("📋 Códigos NUN Sugeridos")

    for i, suggestion in enumerate(suggested_codes, 1):
        codigo = suggestion.get("codigo", "")
        motivo = suggestion.get("motivo", "")
        confianza = float(suggestion.get("confianza", 0) or 0)

        procedure_row = procedures_data[procedures_data["Código"].astype(str) == str(codigo)]

        if not procedure_row.empty:
            row = procedure_row.iloc[0]

            with st.expander(f"🔍 **{i}. {codigo}** - Confianza: {confianza:.0%}", expanded=(i <= 2)):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown("**📄 Descripción:**")
                    st.write(row["Descripción"])

                    st.markdown("**🎯 Motivo de sugerencia:**")
                    st.write(motivo)

                    if "Región" in row:
                        st.markdown(f"**🗺️ Región:** {row['Región']}")
                    if "Complejidad" in row:
                        st.markdown(f"**⚙️ Complejidad:** {row['Complejidad']}")

                with col2:
                    st.markdown("**💰 Honorarios**")

                    cirujano = row.get("Cirujano", 0)
                    total = row.get("Total", 0)
                    helper_count, per_helper_amount, total_helpers_amount = _resolve_helper_pricing(row)

                    if cirujano > 0:
                        st.metric("👨‍⚕️ Cirujano", _format_currency(cirujano))

                    if helper_count == 0:
                        st.info("Sin ayudantes")
                    elif helper_count == 1:
                        st.metric("🤝 Ayudante", _format_currency(per_helper_amount))
                    else:
                        st.caption(f"{helper_count} ayudantes — cada uno cobra {_format_currency(per_helper_amount)}")
                        helper_cols = st.columns(helper_count)
                        for idx in range(helper_count):
                            with helper_cols[idx]:
                                st.metric(f"🤝 Ayudante {idx + 1}", _format_currency(per_helper_amount))
                        st.caption(f"Total ayudantes: {_format_currency(total_helpers_amount)}")

                    if total > 0:
                        st.metric("💎 Total", _format_currency(total))

                if i < len(suggested_codes):
                    st.divider()
        else:
            st.error(f"❌ Código {codigo} no encontrado en la base de datos")


def main():
    """Main application function."""
    render_count = st.session_state.get("nunbot_render_count", 0) + 1
    st.session_state["nunbot_render_count"] = render_count
    logger.info("app_rendered count=%s", render_count)

    st.title("Buscador de Códigos NUN")
    st.markdown("**Sistema de búsqueda inteligente para códigos del Nomenclador Único Nacional**")
    st.markdown("*Especialmente diseñado para traumatología y ortopedia*")
    st.caption("La interfaz aparece primero; la base de datos y la API se cargan solo cuando buscás.")

    health_issues = check_runtime_health(require_openai_key=False)
    data_path_issue = next((issue for issue in health_issues if issue.startswith("No se encontró el archivo de datos NUN")), None)
    if data_path_issue:
        st.error(data_path_issue)
        st.stop()

    st.divider()

    st.subheader("Descripción del Procedimiento")
    st.markdown("Ingrese una descripción libre del procedimiento quirúrgico:")

    with st.form("nunbot_search_form", clear_on_submit=False):
        user_input = st.text_area(
            "Descripción del procedimiento:",
            placeholder="Ejemplo: fractura desplazada de cúbito y radio con reducción y osteosíntesis con placa",
            height=120,
            help="Describa el procedimiento quirúrgico con el mayor detalle posible incluyendo anatomía, tipo de lesión y técnica quirúrgica",
        )
        search_button = st.form_submit_button("🔍 Buscar Códigos NUN", type="primary", use_container_width=True)

    if search_button:
        search_id = uuid.uuid4().hex[:8]
        query_preview = _preview_query(user_input)
        logger.info("search_started id=%s query=%r", search_id, query_preview)

        is_valid, validation_message = validate_search_query(user_input)
        if not is_valid:
            logger.info("search_rejected id=%s reason=%r query=%r", search_id, validation_message, query_preview)
            st.warning(f"⚠️ {validation_message}")
            return

        client = init_openai_client()
        procedures_data = load_nun_data()
        cache_key = _build_search_cache_key(user_input, procedures_data)
        search_cache = _get_search_cache()
        cached_result = search_cache.get(cache_key)

        try:
            if cached_result is not None:
                region, confidence, reason, suggested_codes, local_candidates, used_fallback = cached_result
                logger.info(
                    "search_cache_hit id=%s query=%r region=%s suggestions=%s fallback=%s",
                    search_id,
                    query_preview,
                    region or "",
                    len(suggested_codes),
                    used_fallback,
                )
                st.caption("Resultados reutilizados desde la caché de la sesión.")
            else:
                with st.spinner("🤖 Analizando descripción y buscando códigos relevantes..."):
                    start = time.perf_counter()
                    cached_result = search_nun_codes(
                        client,
                        user_input,
                        procedures_data,
                    )
                    elapsed = time.perf_counter() - start
                search_cache[cache_key] = cached_result
                region, confidence, reason, suggested_codes, local_candidates, used_fallback = cached_result
                logger.info(
                    "search_completed id=%s query=%r elapsed=%.2fs region=%s confidence=%.2f suggestions=%s local_candidates=%s fallback=%s",
                    search_id,
                    query_preview,
                    elapsed,
                    region or "",
                    confidence,
                    len(suggested_codes),
                    len(local_candidates),
                    used_fallback,
                )
        except Exception:
            logger.exception("search_failed id=%s query=%r", search_id, query_preview)
            st.error("❌ Ocurrió un error interno durante la búsqueda. Revisá los logs del contenedor.")
            return

        if region:
            st.info(f"🎯 **Región identificada:** {region} (Confianza: {confidence:.0%})")
            if reason:
                st.write(f"**Motivo:** {reason}")

        if local_candidates:
            st.caption(f"Se prepararon {len(local_candidates)} candidatos locales antes de consultar al modelo.")

        if used_fallback:
            st.warning("⚠️ Se usó un respaldo determinístico porque la respuesta del modelo fue incompleta o inválida.")

        if suggested_codes:
            display_results(suggested_codes, procedures_data)
        else:
            logger.warning("search_empty_results query=%r region=%s fallback=%s", query_preview, region or "", used_fallback)
            st.error("❌ Error al procesar la búsqueda. Verifique su conexión a internet y la configuración de la API.")

    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 0.8em;'>
        💡 Sistema de búsqueda inteligente de códigos NUN | Desarrollado para profesionales de la traumatología
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
