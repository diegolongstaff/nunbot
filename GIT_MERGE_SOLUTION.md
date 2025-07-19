# Solución al Error de Git Push

## Problema
```
! [rejected] main -> main (fetch first)
error: failed to push some refs to 'https://github.com/diegolongstaff/nunbot.git'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

## Solución: Pull y Merge

### Opción 1: Pull con Merge (Recomendado)
```bash
# 1. Hacer pull de los cambios remotos
git pull origin main

# 2. Si hay conflictos, git te mostrará los archivos en conflicto
# Resolver manualmente si es necesario

# 3. Una vez resuelto, push nuevamente
git push origin main
```

### Opción 2: Pull con Rebase (Alternativo)
```bash
# 1. Pull con rebase para mantener historial limpio
git pull --rebase origin main

# 2. Si hay conflictos, resolver y continuar
git rebase --continue

# 3. Push final
git push origin main
```

### Opción 3: Force Push (Solo si estás seguro)
```bash
# ⚠️ CUIDADO: Esto sobrescribe el repositorio remoto
git push --force origin main
```

## Comandos Paso a Paso (Recomendado)

```bash
# 1. Ver el estado actual
git status

# 2. Pull de cambios remotos
git pull origin main

# 3. Si no hay conflictos, hacer push
git push origin main
```

## Si Hay Conflictos de Merge

Si git te muestra conflictos, verás algo como:
```
Auto-merging archivo.txt
CONFLICT (content): Merge conflict in archivo.txt
```

Para resolverlos:
```bash
# 1. Ver archivos en conflicto
git status

# 2. Editar manualmente los archivos marcados
# Buscar líneas con <<<<<<, ======, >>>>>>

# 3. Después de resolver, agregar los archivos
git add archivo_resuelto.txt

# 4. Completar el merge
git commit -m "Resolver conflictos de merge"

# 5. Push final
git push origin main
```

## Ejecutar Ahora

Te recomiendo ejecutar esta secuencia:

```bash
git pull origin main
git push origin main
```

Si hay conflictos, git te guiará en el proceso de resolución.