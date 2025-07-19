# Force Push para Reemplazar Repositorio Remoto

## Comandos para Ejecutar

```bash
# 1. Verificar que todos los archivos están agregados
git status

# 2. Force push para reemplazar todo el contenido remoto
git push --force origin main
```

## ⚠️ Importante
- Esto sobrescribirá completamente el repositorio remoto
- Se perderán todos los cambios que estén en GitHub pero no localmente
- Es exactamente lo que necesitas para tener tus archivos actualizados

## Alternativa (si prefieres ser más explícito)
```bash
git push --force-with-lease origin main
```

## Resultado Esperado
Después del force push, el repositorio GitHub tendrá exactamente:
- ✅ app.py (funcionando con OpenAI SDK v1.0+)
- ✅ nun_procedimientos.csv (665 procedimientos)
- ✅ requirements_fixed.txt (dependencias correctas)
- ✅ .streamlit/config.toml (puerto 8501)
- ✅ README.md y documentación
- ✅ Archivos de configuración (.gitignore, etc.)

**Ejecuta**: `git push --force origin main`