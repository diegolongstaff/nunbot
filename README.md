# NUNBot - Buscador Inteligente de Códigos NUN

## ¿Qué es NUNBot?

NUNBot es una aplicación web desarrollada en Streamlit que ayuda a médicos traumatólogos a encontrar códigos del **Nomenclador Único Nacional (NUN)** utilizando descripciones naturales de procedimientos quirúrgicos.

## ¿Para qué sirve?

- **Búsqueda inteligente**: Escriba una descripción libre como "fractura de cadera con enclavado" y obtenga los códigos NUN más relevantes
- **Identificación anatómica**: El sistema identifica automáticamente la región anatómica basándose en la descripción
- **Optimización de tokens**: Utiliza un sistema de dos pasos para reducir el consumo de tokens de OpenAI
- **Información completa**: Muestra código, descripción, honorarios de cirujano y ayudantes

## Regiones Anatómicas Soportadas

- **MS** → Miembro Superior (hombro, húmero, codo, antebrazo, muñeca, mano, dedos)
- **CO** → Columna (cervical, dorsal, lumbar, sacra)
- **PC** → Pelvis y Cadera (fémur proximal, acetábulo, sacro)
- **RO** → Rodilla (patela, cóndilos femorales, platillos tibiales, ligamentos cruzados)
- **PP** → Pierna y Pie (tibia, peroné, tobillo, calcáneo, astrágalo, metatarsianos, falanges)

## Instalación Local

### Prerrequisitos

- Python 3.11 o superior
- Clave API de OpenAI

### Pasos de instalación

1. **Clonar el repositorio**:
```bash
git clone https://github.com/diegolongstaff/nunbot.git
cd nunbot
```

2. **Crear entorno virtual**:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configurar Streamlit (opcional)**:
```bash
mkdir -p .streamlit
cp streamlit_config.toml .streamlit/config.toml
```

5. **Configurar variables de entorno**:
```bash
export OPENAI_API_KEY="tu_clave_api_aqui"
```

6. **Ejecutar la aplicación**:
```bash
streamlit run app.py
```

7. **Abrir en el navegador**:
   - La aplicación se abrirá automáticamente en `http://localhost:8501`

## Uso

1. **Describir el procedimiento**: Ingrese una descripción libre del procedimiento quirúrgico
2. **Buscar códigos**: Haga clic en "Buscar Códigos NUN"
3. **Revisar resultados**: El sistema mostrará:
   - Región anatómica identificada
   - 3-5 códigos más relevantes
   - Nivel de confianza para cada sugerencia
   - Honorarios asociados

### Ejemplos de búsqueda

- "fractura de cadera con reducción abierta"
- "forage de cadera"
- "fractura de muñeca con osteosíntesis"
- "luxación de rodilla con reparación ligamentaria"

## Dependencias

- **streamlit** >= 1.47.0: Framework para aplicaciones web
- **pandas** >= 2.3.1: Manipulación y análisis de datos
- **openai** >= 1.97.0: Integración con la API de OpenAI

## Configuración de OpenAI

1. Obtener clave API en [OpenAI Platform](https://platform.openai.com/api-keys)
2. Configurar como variable de entorno `OPENAI_API_KEY`
3. La aplicación utiliza el modelo GPT-4o para análisis inteligente

## Arquitectura

### Flujo de trabajo optimizado en dos pasos:

1. **Identificación de región**: El sistema determina la región anatómica usando un prompt ligero
2. **Búsqueda filtrada**: Filtra los procedimientos por región y busca códigos específicos

### Optimización de tokens:

- Reduce el uso de tokens en ~70% usando formato compacto
- Evita errores de límite de tokens (429) de OpenAI
- Procesa solo procedimientos de la región relevante

## Estructura del Proyecto

```
nunbot/
├── app.py                 # Aplicación principal
├── nun_procedimientos.csv # Base de datos de códigos NUN
├── requirements.txt       # Dependencias Python
├── README.md             # Documentación
├── .gitignore            # Archivos ignorados por Git
└── .streamlit/
    └── config.toml       # Configuración de Streamlit
```

## Contribución

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Cree una rama para su feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit sus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Cree un Pull Request

## Licencia

Este proyecto está bajo la licencia MIT.

## Contacto

Para preguntas o soporte, contacte a [@diegolongstaff](https://github.com/diegolongstaff).

---

**Desarrollado especialmente para profesionales de la traumatología y ortopedia**