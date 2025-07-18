import streamlit as st
import pandas as pd
import os
import json
from openai import OpenAI
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Buscador de Códigos NUN",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

def determine_anatomical_region(client, user_description):
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
        response = client.chat.completions.create(
            model="gpt-4o",
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
    
    # Convert filtered procedures to context
    procedures_context = []
    for _, row in filtered_procedures.iterrows():
        procedures_context.append({
            "codigo": row['Código'],
            "descripcion": row['Descripción'],
            "region": row.get('Región', ''),
            "complejidad": row.get('Complejidad', ''),
            "palabras_clave": row.get('Palabras clave', '')
        })
    
    prompt = f"""
Eres un asistente médico especializado en traumatología y ortopedia. Tu tarea es encontrar los códigos NUN más apropiados para el procedimiento descrito.

DESCRIPCIÓN DEL PROCEDIMIENTO:
"{user_description}"

CÓDIGOS NUN DISPONIBLES EN LA REGIÓN ANATÓMICA IDENTIFICADA:
{json.dumps(procedures_context, ensure_ascii=False, indent=2)}

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

def query_openai_for_codes(client, user_description, procedures_data):
    """Two-step process: 1) Determine region, 2) Search filtered codes"""
    
    # Step 1: Determine anatomical region
    with st.spinner("🔍 Identificando región anatómica..."):
        region, confidence, reason = determine_anatomical_region(client, user_description)
        
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
    
    # Step 3: Search within filtered procedures
    try:
        prompt = create_search_prompt(user_description, filtered_procedures)
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
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
            
            # Create an expander for each result
            with st.expander(f"🔍 **{i}. {codigo}** - Confianza: {confianza:.0%}", expanded=(i <= 2)):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**📄 Descripción:**")
                    st.write(row['Descripción'])
                    
                    st.markdown(f"**🎯 Motivo de sugerencia:**")
                    st.write(motivo)
                    
                    if 'Región' in row:
                        st.markdown(f"**🗺️ Región:** {row['Región']}")
                    if 'Complejidad' in row:
                        st.markdown(f"**⚙️ Complejidad:** {row['Complejidad']}")
                
                with col2:
                    st.markdown("**💰 Honorarios**")
                    
                    cirujano = row.get('Cirujano', 0)
                    ayudantes = row.get('Ayudantes', 0)
                    total = row.get('Total', 0)
                    
                    if cirujano > 0:
                        st.metric("👨‍⚕️ Cirujano", f"${cirujano:,.0f}")
                    if ayudantes > 0:
                        st.metric("🤝 Ayudantes", f"${ayudantes:,.0f}")
                    if total > 0:
                        st.metric("💎 Total", f"${total:,.0f}")
                
                # Add separator
                if i < len(suggested_codes):
                    st.divider()
        else:
            st.error(f"❌ Código {codigo} no encontrado en la base de datos")

def main():
    """Main application function"""
    # Initialize
    client = init_openai_client()
    procedures_data = load_nun_data()
    
    # Header
    st.title("🏥 Buscador de Códigos NUN")
    st.markdown("**Sistema de búsqueda inteligente para códigos del Nomenclador Único Nacional**")
    st.markdown("*Especialmente diseñado para traumatología y ortopedia*")
    
    st.divider()
    
    # Input section
    st.subheader("🔍 Descripción del Procedimiento")
    st.markdown("Ingrese una descripción libre del procedimiento quirúrgico:")
    
    # Text area for procedure description
    user_input = st.text_area(
        "Descripción del procedimiento:",
        placeholder="Ejemplo: fractura desplazada de cúbito y radio con reducción y osteosíntesis con placa",
        height=120,
        help="Describa el procedimiento quirúrgico con el mayor detalle posible incluyendo anatomía, tipo de lesión y técnica quirúrgica"
    )
    
    # Search button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_button = st.button("🔍 Buscar Códigos NUN", type="primary", use_container_width=True)
    
    # Process search
    if search_button:
        if not user_input.strip():
            st.warning("⚠️ Por favor ingrese una descripción del procedimiento")
            return
        
        with st.spinner("🤖 Analizando descripción y buscando códigos relevantes..."):
            suggested_codes = query_openai_for_codes(client, user_input, procedures_data)
            
        if suggested_codes:
            display_results(suggested_codes, procedures_data)
        else:
            st.error("❌ Error al procesar la búsqueda. Verifique su conexión a internet y la configuración de la API.")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    💡 Sistema de búsqueda inteligente de códigos NUN | Desarrollado para profesionales de la traumatología
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
