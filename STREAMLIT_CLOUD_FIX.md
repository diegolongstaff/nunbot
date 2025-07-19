# Solución al Error de Streamlit Cloud

## Problema Original
```
📦 WARN: More than one requirements file detected in the repository. 
Available options: uv-sync /mount/src/nunbot/uv.lock, uv /mount/src/nunbot/requirements.txt, poetry /mount/src/nunbot/pyproject.toml. 
Used: uv-sync with /mount/src/nunbot/uv.lock

❗️ The service has encountered an error while checking the health of the Streamlit app: 
Get "http://localhost:8501/healthz": dial tcp 127.0.0.1:8501: connect: connection refused
```

## Soluciones Implementadas

### ✅ 1. Limpieza de Archivos Conflictivos
- **Eliminado**: `pyproject.toml` (generado por Replit)
- **Eliminado**: `uv.lock` (generado por uv package manager)
- **Conservado**: `requirements.txt` con versiones estables

### ✅ 2. Configuración de Puerto Correcto
- **Creado**: `.streamlit/config.toml` con puerto 8501 (estándar de Streamlit Cloud)
- **Eliminado**: `streamlit_config.toml` (no necesario)

### ✅ 3. Compatibilidad con OpenAI SDK v0.28.1
- **Problema**: App usaba OpenAI SDK v1.3.9 pero código era para v1.0+
- **Solución**: Adaptado código para usar OpenAI SDK v0.28.1 (clásico)
- **Cambios**: 
  - `OpenAI(api_key=...)` → `openai.api_key = ...`
  - `client.chat.completions.create()` → `openai.ChatCompletion.create()`
  - `response.choices[0].message.content` → `response.choices[0].message["content"]`
  - Modelo `gpt-4o` → `gpt-4` (compatible con v0.28.1)

### ✅ 4. .gitignore Actualizado
- Agregado `pyproject.toml` y `uv.lock` para evitar conflictos futuros
- Simplificado para despliegue limpio

### ✅ 5. Documentación Actualizada
- README.md corregido sin referencias a archivos eliminados
- DEPLOYMENT.md actualizado con comandos git correctos
- git_commands.txt actualizado para incluir `.streamlit/config.toml`

## Archivos Listos para GitHub

### Archivos Principales
- ✅ `app.py` - Aplicación principal
- ✅ `nun_procedimientos.csv` - Base de datos NUN (665 procedimientos)
- ✅ `requirements.txt` - Dependencias con versiones estables
- ✅ `.streamlit/config.toml` - Configuración para Streamlit Cloud

### Documentación
- ✅ `README.md` - Instalación y uso
- ✅ `DEPLOYMENT.md` - Guía completa de despliegue
- ✅ `.gitignore` - Archivos excluidos correctamente

## Próximos Pasos

1. **Commit y Push**:
```bash
git add README.md requirements_fixed.txt .gitignore .streamlit/config.toml DEPLOYMENT.md git_commands.txt STREAMLIT_CLOUD_FIX.md app.py
git commit -m "fix: Resolver conflictos de despliegue y compatibilidad OpenAI

- Eliminar archivos conflictivos (uv.lock, pyproject.toml)
- Configurar puerto 8501 para Streamlit Cloud
- Migrar código a OpenAI SDK v0.28.1 (clásico)
- Actualizar app.py para compatibilidad con versión antigua
- Usar gpt-4 en lugar de gpt-4o"
git push origin main
```

2. **Desplegar en Streamlit Cloud**:
   - Ir a [share.streamlit.io](https://share.streamlit.io)
   - Conectar repositorio GitHub
   - Configurar `OPENAI_API_KEY` en secrets
   - Deploy automático

## Resultado Esperado
- ✅ Sin conflictos de dependencias
- ✅ Puerto correcto (8501)
- ✅ Health check exitoso
- ✅ Aplicación funcionando en Streamlit Cloud