import streamlit as st
import pandas as pd
import os
import json
from openai import OpenAI
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration variables
USE_GPT4O = True  # Set to False to use GPT-3.5 for both region detection and code search

# Page configuration
st.set_page_config(
    page_title="Buscador de Códigos NUN",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Mobile-friendly viewport
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1">', unsafe_allow_html=True)

# Initialize OpenAI client
@st.cache_resource
def init_openai_client():
    """Initialize OpenAI client with API key from environment variables"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("⚠️ API Key de OpenAI no encontrada. Verifique la variable de entorno OPENAI_API_KEY")
        st.stop()
    return OpenAI(api_key=api_key)

# Load CSV data
@st.cache_data
def load_nun_data():
    """Load NUN procedures data from CSV file"""
    try:
        # Try to load the CSV file
        df = pd.read_csv('nun_procedimientos.csv')
        
        # Clean and standardize column names
        df.columns = df.columns.str.strip()
        
        # Handle currency formatting in fee columns
        fee_columns = ['Cirujano', 'Ayudantes', 'Total']
        for col in fee_columns:
            if col in df.columns:
                # Remove currency symbols and convert to numeric
                df[col] = df[col].astype(str).str.replace('$', '').str.replace(',', '').str.replace('"', '')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        logger.info(f"Loaded {len(df)} procedures from CSV")
        return df
    except FileNotFoundError:
        st.error("❌ Archivo 'nun_procedimientos.csv' no encontrado")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo CSV: {str(e)}")
        st.stop()

# Initialize session state for search history
def init_session_state():
    """Initialize session state variables"""
    if "historial" not in st.session_state:
        st.session_state["historial"] = []

@st.cache_data
def determine_anatomical_region(user_description, use_gpt4o=True):
    """Step 1: Determine the anatomical region from the medical description"""
    prompt = f"""
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
"""
    
    try:
        # Get client
        client = init_openai_client()
        
        # Choose model based on configuration
        model = "gpt-4o" if use_gpt4o else "gpt-3.5-turbo"
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en anatomía traumatológica. Responde siempre en formato JSON válido."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=500
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get("region", ""), result.get("confianza", 0), result.get("motivo", "")
        
    except Exception as e:
        logger.error(f"Error determining anatomical region: {e}")
        return "", 0, ""

def create_search_prompt(user_description, filtered_procedures):
    """Step 2: Create a prompt for OpenAI to find matching procedure codes from filtered region"""
    
    # Convert filtered procedures to compact text format
    procedures_list = []
    for _, row in filtered_procedures.iterrows():
        codigo = row['Código']
        descripcion = row['Descripción']
        # Create compact format: CODE - DESCRIPTION
        procedures_list.append(f"{codigo} - {descripcion}")
    
    # Join all procedures into a single string
    procedures_text = "\n".join(procedures_list)
    
    prompt = f"""
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
"""
    
    return prompt

@st.cache_data
def cached_query_openai_for_codes(user_description, procedures_text, use_gpt4o=True):
    """Cached function to query OpenAI for procedure codes"""
    try:
        # Get client
        client = init_openai_client()
        
        # Choose model based on configuration
        model = "gpt-3.5-turbo"  # Always use GPT-3.5 for code search as it's sufficient
        
        prompt = f"""
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
"""
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en códigos NUN para traumatología. Responde siempre en formato JSON válido."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1500
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get("codigos_sugeridos", [])
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON response: {e}")
        return []
    except Exception as e:
        logger.error(f"Error querying OpenAI: {e}")
        return []

def query_openai_for_codes(user_description, procedures_data):
    """Two-step process: 1) Determine region, 2) Search filtered codes"""
    
    # Step 1: Determine anatomical region (cached)
    with st.spinner("🔍 Identificando región anatómica..."):
        region, confidence, reason = determine_anatomical_region(user_description, USE_GPT4O)
        
        if not region:
            st.error("❌ No se pudo determinar la región anatómica")
            return []
        
        # Show region identification result
        st.info(f"🎯 **Región identificada:** {region} (Confianza: {confidence:.0%})")
        st.write(f"**Motivo:** {reason}")
    
    # Step 2: Filter procedures by region
    filtered_procedures = procedures_data[procedures_data['Región'] == region]
    
    if filtered_procedures.empty:
        st.warning(f"⚠️ No se encontraron procedimientos para la región {region}")
        return []
    
    st.info(f"🔎 Buscando entre {len(filtered_procedures)} procedimientos de la región {region}...")
    
    # Step 3: Search within filtered procedures (cached)
    # Log token optimization
    logger.info(f"Token optimization: Searching within {len(filtered_procedures)} procedures instead of full dataset ({len(procedures_data)} procedures)")
    
    # Convert filtered procedures to compact text format for caching
    procedures_list = []
    for _, row in filtered_procedures.iterrows():
        codigo = row['Código']
        descripcion = row['Descripción']
        procedures_list.append(f"{codigo} - {descripcion}")
    procedures_text = "\n".join(procedures_list)
    
    # 👇 Debug: Imprimir input y cantidad de códigos
    print("🟢 User description:")
    print(user_description)
    print("🔢 Códigos NUN que se mandan:")
    print(len(filtered_procedures))
    
    # Use cached function for OpenAI query
    suggested_codes = cached_query_openai_for_codes(user_description, procedures_text, USE_GPT4O)
    
    return suggested_codes, region

def display_results(suggested_codes, procedures_data):
    """Display the search results in a formatted way"""
    if not suggested_codes:
        st.warning("⚠️ No se encontraron códigos sugeridos. Intente con una descripción más específica.")
        return
    
    st.subheader("📋 Códigos NUN Sugeridos")
    
    for i, suggestion in enumerate(suggested_codes, 1):
        codigo = suggestion.get("codigo", "")
        motivo = suggestion.get("motivo", "")
        confianza = suggestion.get("confianza", 0)
        
        # Find the procedure in our data
        procedure_row = procedures_data[procedures_data['Código'] == codigo]
        
        if not procedure_row.empty:
            row = procedure_row.iloc[0]
            
            # Create an expander for each result - mobile friendly
            with st.expander(f"🔍 **{i}. {codigo}** - Confianza: {confianza:.0%}", expanded=(i <= 2)):
                # Mobile-friendly layout - stack vertically on small screens
                st.markdown(f"**📄 Descripción:**")
                st.write(row['Descripción'])
                
                st.markdown(f"**🎯 Motivo de sugerencia:**")
                st.write(motivo)
                
                if 'Región' in row:
                    st.markdown(f"**🗺️ Región:** {row['Región']}")
                if 'Complejidad' in row:
                    st.markdown(f"**⚙️ Complejidad:** {row['Complejidad']}")
                
                # Honorarios section
                st.markdown("**💰 Honorarios**")
                
                cirujano = row.get('Cirujano', 0)
                ayudantes = row.get('Ayudantes', 0)
                total = row.get('Total', 0)
                
                # Mobile-friendly metrics in columns only if needed
                if cirujano > 0 or ayudantes > 0 or total > 0:
                    col1, col2, col3 = st.columns(3)
                    if cirujano > 0:
                        col1.metric("👨‍⚕️ Cirujano", f"${cirujano:,.0f}")
                    if ayudantes > 0:
                        col2.metric("🤝 Ayudantes", f"${ayudantes:,.0f}")
                    if total > 0:
                        col3.metric("💎 Total", f"${total:,.0f}")
                
                # Add separator
                if i < len(suggested_codes):
                    st.divider()
        else:
            st.error(f"❌ Código {codigo} no encontrado en la base de datos")

def add_to_history(user_description, region, suggested_codes):
    """Add search to session history"""
    if "historial" not in st.session_state:
        st.session_state["historial"] = []
    
    # Create history entry
    history_entry = {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "descripcion": user_description,
        "region": region,
        "codigos": suggested_codes[:3]  # Store only top 3 codes
    }
    
    # Add to beginning of history (most recent first)
    st.session_state["historial"].insert(0, history_entry)
    
    # Keep only last 10 searches
    if len(st.session_state["historial"]) > 10:
        st.session_state["historial"] = st.session_state["historial"][:10]

def display_search_history():
    """Display search history in expandable section"""
    if "historial" not in st.session_state or not st.session_state["historial"]:
        return
    
    st.divider()
    
    with st.expander(f"📚 Historial de Búsquedas ({len(st.session_state['historial'])})", expanded=False):
        for i, entry in enumerate(st.session_state["historial"]):
            with st.container():
                st.markdown(f"**🕐 {entry['timestamp']}**")
                st.markdown(f"**Descripción:** {entry['descripcion']}")
                st.markdown(f"**Región:** {entry['region']}")
                
                if entry['codigos']:
                    st.markdown("**Códigos encontrados:**")
                    for j, codigo_info in enumerate(entry['codigos'], 1):
                        codigo = codigo_info.get('codigo', '')
                        confianza = codigo_info.get('confianza', 0)
                        st.write(f"  {j}. {codigo} (Confianza: {confianza:.0%})")
                
                if i < len(st.session_state["historial"]) - 1:
                    st.divider()

def main():
    """Main application function"""
    # Initialize session state
    init_session_state()
    
    # Load data
    procedures_data = load_nun_data()
    
    # Configuration info in sidebar (optional)
    with st.sidebar:
        st.markdown("### ⚙️ Configuración")
        current_model = "GPT-4o" if USE_GPT4O else "GPT-3.5 Turbo"
        st.info(f"**Modelo para región:** {current_model}")
        st.info(f"**Modelo para códigos:** GPT-3.5 Turbo")
        
        if st.button("🗑️ Limpiar Historial"):
            st.session_state["historial"] = []
            st.rerun()
    
    # Header
    st.title("🏥 Buscador de Códigos NUN")
    st.markdown("**Sistema de búsqueda inteligente para códigos del Nomenclador Único Nacional**")
    st.markdown("*Especialmente diseñado para traumatología y ortopedia*")
    
    st.divider()
    
    # Input section
    st.subheader("🔍 Descripción del Procedimiento")
    st.markdown("Ingrese una descripción libre del procedimiento quirúrgico:")
    
    # Text area for procedure description - mobile friendly
    user_input = st.text_area(
        "Descripción del procedimiento:",
        placeholder="Ejemplo: fractura desplazada de cúbito y radio con reducción y osteosíntesis con placa",
        height=120,
        help="Describa el procedimiento quirúrgico con el mayor detalle posible incluyendo anatomía, tipo de lesión y técnica quirúrgica"
    )
    
    # Search button - mobile friendly, full width
    search_button = st.button("🔍 Buscar Códigos NUN", type="primary", use_container_width=True)
    
    # Process search
    if search_button:
        if not user_input.strip():
            st.warning("⚠️ Por favor ingrese una descripción del procedimiento")
            return
        
        with st.spinner("🤖 Analizando descripción y buscando códigos relevantes..."):
            result = query_openai_for_codes(user_input, procedures_data)
            
            if result and len(result) == 2:
                suggested_codes, region = result
                
                if suggested_codes:
                    display_results(suggested_codes, procedures_data)
                    # Add to history
                    add_to_history(user_input, region, suggested_codes)
                else:
                    st.error("❌ Error al procesar la búsqueda. Verifique su conexión a internet y la configuración de la API.")
            else:
                st.error("❌ Error al procesar la búsqueda. Verifique su conexión a internet y la configuración de la API.")
    
    # Display search history
    display_search_history()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    💡 Sistema de búsqueda inteligente de códigos NUN | Desarrollado para profesionales de la traumatología
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
