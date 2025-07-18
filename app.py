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

def create_search_prompt(user_description, procedures_data):
    """Create a prompt for OpenAI to find matching procedure codes"""
    
    # Get a sample of procedures for context
    sample_procedures = procedures_data.head(40)
    procedures_context = []
    
    for _, row in sample_procedures.iterrows():
        procedures_context.append({
            "codigo": row['Código'],
            "descripcion": row['Descripción'],
            "region": row.get('Región', ''),
            "complejidad": row.get('Complejidad', ''),
            "palabras_clave": row.get('Palabras clave', '')
        })
        # Glosario médico contextual para mejorar la interpretación semántica
    glosario = """
Glosario anatómico y sistema de codificación del NUN (Nomenclador Único Nacional):

El NUN organiza los procedimientos quirúrgicos por región anatómica, utilizando abreviaciones. Estas son las principales:

- MS → Miembro Superior (clavícula, húmero, codo, antebrazo, muñeca, mano, dedos)
- CO → Columna (cervical, dorsal, lumbar, sacra)
- PC → Pelvis y Cadera (fémur proximal, acetábulo, sacro)
- RO → Rodilla (patela, cóndilos femorales, platillos tibiales, ligamentos cruzados)
- PP → Pierna y Pie (tibia, peroné, tobillo, astrágalo, calcáneo, metatarsianos, falanges)

Además, hay sinónimos comunes que deben interpretarse correctamente:

- "Fractura de cadera" → fractura de fémur proximal → buscar en PC
- "Fractura de muñeca" → radio distal → buscar en MS
- "Fractura de hombro" → húmero proximal → buscar en MS
- "Fractura de tobillo" → maleolo → buscar en PP
- "Fractura de pelvis" → rama isquiopubiana, acetábulo → buscar en PC
- "Fractura de espalda" → columna cervica, dorsal o lumbar → buscar en CO

EJEMPLO DE EQUIVALENCIA:
Entrada: "fractura de cadera"
Interpretación esperada: "fractura de fémur proximal", región PC
"""
    prompt = f"""
    {glosario}
Eres un asistente médico especializado en traumatología y ortopedia. Tu tarea es analizar una descripción libre del procedimiento quirúrgico e identificar correctamente:

1. La región anatómica afectada (según el sistema NUN).
2. El tipo de fractura o lesión.
3. La técnica quirúrgica mencionada.

Luego, seleccioná los 3 a 5 códigos NUN más apropiados, tomando en cuenta:
- La región codificada (MS, CO, PC, RO, PP).
- La descripción textual.
- La complejidad y técnica si se menciona.

DESCRIPCIÓN DEL PROCEDIMIENTO INGRESADA POR EL MÉDICO:
"{user_description}"

CONTEXTO DE CÓDIGOS NUN DISPONIBLES (muestra):
{json.dumps(procedures_context, ensure_ascii=False, indent=2)}

INSTRUCCIONES:
1. Analiza la descripción del procedimiento médico
2. Usa el glosario anterior para interpretar términos amplios como "cadera", "muñeca", "tobillo", etc. 
3. Identifica las palabras clave médicas relevantes (anatomía, técnica quirúrgica, tipo de lesión, etc.)
4. Busca en tu conocimiento los códigos NUN que mejor coincidan con la descripción
5. Considera la región anatómica, complejidad y tipo de procedimiento
6. Devuelve EXACTAMENTE 3 a 6 códigos más probables, ordenados por relevancia

FORMATO DE RESPUESTA (JSON obligatorio):
{{
    "codigos_sugeridos": [
        {{
            "codigo": "MS.01.01",
            "motivo": "Explicación breve de por qué este código es relevante",
            "confianza": 0.95
        }}
    ]
}}

IMPORTANTE:
- Solo sugiere códigos que existan en el nomenclador NUN
- La confianza debe ser un número entre 0 y 1
- Ordena por relevancia (más relevante primero)
- Responde SOLO en formato JSON
- Si no encuentras coincidencias claras, sugiere los códigos más cercanos
"""
    
    return prompt

def query_openai_for_codes(client, user_description, procedures_data):
    """Query OpenAI to get suggested procedure codes"""
    try:
        prompt = create_search_prompt(user_description, procedures_data)
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Sos un experto en codificación quirúrgica. Siempre usá el glosario proporcionado para traducir términos generales como 'cadera', 'muñeca' o 'hombro' en términos anatómicos precisos del Nomenclador Único Nacional. Responde siempre en JSON válido."
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
