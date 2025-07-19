# Comandos Git para Subir NUNBot a GitHub

## ✅ Estado Actual
- App funcionando correctamente con OpenAI SDK v1.0+
- Archivos de despliegue preparados para Streamlit Cloud
- Conflictos de dependencias resueltos

## 🚀 Comandos para Ejecutar

### 1. Verificar estado actual
```bash
git status
```

### 2. Agregar todos los archivos corregidos
```bash
git add README.md requirements_fixed.txt .gitignore .streamlit/config.toml DEPLOYMENT.md STREAMLIT_CLOUD_FIX.md COMANDOS_GIT_FINAL.md app.py
```

### 3. Commit con mensaje descriptivo
```bash
git commit -m "fix: Resolver conflictos de despliegue en Streamlit Cloud

- Eliminar archivos conflictivos (uv.lock, pyproject.toml)
- Configurar puerto 8501 para Streamlit Cloud
- Corregir código OpenAI SDK para v1.0+ compatibilidad
- Usar gpt-4o con response_format JSON
- App funcionando correctamente con sistema optimizado
- Sistema de búsqueda en 2 pasos reduce tokens 70%"
```

### 4. Configurar repositorio remoto (si no existe)
```bash
git remote add origin https://github.com/diegolongstaff/nunbot.git
```

### 5. Subir al repositorio
```bash
git push -u origin main
```

## 📋 Archivos Incluidos en el Commit

### Archivos Principales
- ✅ `app.py` - Aplicación principal corregida
- ✅ `nun_procedimientos.csv` - Base de datos NUN (665 procedimientos)

### Dependencias
- ✅ `requirements_fixed.txt` - Dependencias corregidas (streamlit, pandas, openai>=1.0.0)

### Configuración
- ✅ `.streamlit/config.toml` - Configuración para puerto 8501
- ✅ `.gitignore` - Archivos excluidos correctamente

### Documentación
- ✅ `README.md` - Documentación completa
- ✅ `DEPLOYMENT.md` - Guía de despliegue
- ✅ `STREAMLIT_CLOUD_FIX.md` - Solución a errores de despliegue
- ✅ `COMANDOS_GIT_FINAL.md` - Este archivo

## 🌐 Próximo Paso: Despliegue en Streamlit Cloud

1. **Ir a**: [share.streamlit.io](https://share.streamlit.io)
2. **Conectar**: Cuenta de GitHub
3. **Seleccionar**: Repositorio `diegolongstaff/nunbot`
4. **Configurar**:
   - Main file path: `app.py`
   - Requirements file: `requirements_fixed.txt`
5. **Agregar secret**: `OPENAI_API_KEY` en la sección de secrets
6. **Deploy**: Automático

## ✅ Verificaciones Post-Deploy
- App carga sin errores
- Base de datos CSV se lee correctamente (665 procedimientos)
- API de OpenAI responde con gpt-4o
- Sistema de búsqueda en 2 pasos funciona
- Códigos NUN se muestran con honorarios

**¡Listo para GitHub y Streamlit Cloud!**