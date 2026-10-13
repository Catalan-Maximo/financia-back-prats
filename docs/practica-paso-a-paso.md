# Manual de práctica — todo lo que hicimos, paso a paso (para re-practicar desde cero)

> Este manual asume que no te acordás de nada. Cada comando dice **qué hace**, **dónde se escribe**
> y **qué tenés que ver** al ejecutarlo. Está ordenado por fases, como lo hicimos en el proyecto.
> Todo lo que está en Azure YA EXISTE: no hay que volver a crearlo — acá se practica usarlo.

---

## 0. Las tres "terminales" que vas a usar

| Dónde | Qué es | Para qué se usa |
|---|---|---|
| **Terminal de la Mac** (app Terminal, o la terminal integrada de VS Code) | La consola de tu computadora | git, docker, maven, psql, az, grype — el 95% de la práctica |
| **Cloud Shell de Azure** (icono `>_` arriba en el portal) | Un Linux dentro del navegador | Solo cosas puntuales de Azure (nosotros la usamos para crear el SP). No la necesitás para el día a día |
| **Postman** | App gráfica para probar APIs | Probar login/JWT contra local o Azure |

**Regla**: si un comando empieza con `cd ~/Documents/GitHub/...` es para la **Terminal de la Mac**. Si empieza con `az ...` también (tu Mac tiene `az` logueado). Lo del portal se hace en el navegador.

**Antes de empezar, verificá que las herramientas andan** (Terminal de la Mac):

```bash
docker --version      # debe mostrar algo como "Docker version 29.x"
az --version          # debe mostrar "azure-cli 2.89.x"
grype version         # debe mostrar una versión
```

Si `az` no está logueado: `az login` (se abre el navegador → entrá con tu cuenta de la universidad).

---

## FASE 1 — Compilar y arrancar el backend

**Qué hicimos**: arreglamos el wrapper de Maven, separamos la config en perfiles (dev/prod) y sacamos las credenciales del código a `.env`.

```bash
cd ~/Documents/GitHub/financia-back-prats   # entrar al proyecto (SIEMPRE primero)
./mvnw test                                 # compila y corre los tests (necesita la BD del contenedor y el .env)
```

**Qué es cada cosa**:
- `cd` = "cambiá al directorio" del proyecto.
- `./mvnw` = el wrapper de Maven (descarga Maven solo si hace falta; no requiere instalación global).
- `test` = compila + ejecuta los tests (`contextLoads` contra la BD local).

**Qué tenés que ver**: al final `BUILD SUCCESS`.

---

## FASE 2 — JWT con Postman

**Qué hicimos**: login con JWT, endpoints protegidos, `/auth/validate`, y ocultamos el hash de las respuestas.

**Práctica** (con el backend corriendo — ver Fase 5):
1. Abrí Postman → **Import** → `postman/FinancIA-Backend-JWT.postman_collection.json`.
2. Ejecutá los requests **01 → 08 en orden**.
3. Resultados esperados: 01=200 · 02=200 o 400 (si el email ya existe) · 03=200 con token · 04=**401** · 05=200 · 06=200 · 07=**401** · 08=**401**.
4. Pegá el token del 03 en [jwt.io](https://jwt.io) → se ven header, payload y firma.

---

## FASE 3 — HikariCP (el pool de conexiones)

**Qué hicimos**: configuramos el pool (10 conexiones máx, timeout de 5 s) y demostramos que la app **se recupera sola** cuando la BD vuelve.

**Práctica** (con el backend y la BD corriendo):
```bash
docker stop financia-db        # apagá la BD del contenedor
# → en Postman, un endpoint de datos da 500 (falla rápido, no cuelga)
docker start financia-db       # prendé la BD de nuevo
# → esperá ~10 segundos y el mismo request da 200 otra vez (sin reiniciar la app)
```

**Explicación**: HikariCP reutiliza conexiones; cuando la BD no responde, la petición falla a los 5 s (en vez de los 30 del default) y el pool se reconstruye solo.

---

## FASE 4 — Docker (la imagen)

**Qué hicimos**: Dockerfile multietapa (Maven → distroless nonroot) + etiquetas OCI + amd64 para Azure.

```bash
cd ~/Documents/GitHub/financia-back-prats

# Construir la imagen para TU Mac (arm64) con etiquetas OCI:
docker build \
  --build-arg VERSION=prueba --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  -t financia-back:prueba .

# Inspeccionarla (usuario + etiquetas):
docker image inspect financia-back:prueba --format '{{.Config.User}}'

# Construir para AZURE (amd64) — corre bajo emulación, tarda:
docker buildx build --platform linux/amd64 --load -t financia-back:amd64 .

# Borrar la imagen de prueba cuando termines:
docker rmi financia-back:prueba
```

**Qué tenés que ver**: build sin errores; el inspect muestra `nonroot`; la imagen amd64 existe (`docker images`).

---

## FASE 5 — Docker Compose (backend + BD juntos)

**Qué hicimos**: el stack local completo con persistencia y healthcheck.

```bash
cd ~/Documents/GitHub/financia-back-prats

docker compose up -d --build   # arranca BD (5433) + backend (8080). -d = en segundo plano
docker compose ps              # estado de los dos servicios (db debe decir "healthy")
curl http://localhost:8080/api/v1/health    # la app responde
docker compose logs -f api     # logs en vivo (salí con Ctrl+C, NO frena nada)
docker compose stop            # frena sin borrar
docker compose start           # vuelve a arrancar
docker compose down            # frena y borra contenedores (los DATOS no se pierden)
# ⚠️ docker compose down -v    # borra TAMBIÉN los datos de la BD — solo si querés cero
```

**Regla de oro**: `down` no pierde datos; `down -v` sí.

---

## FASE 6 — Grype (vulnerabilidades)

**Qué hicimos**: escaneo de la imagen, correcciones (188 → 68 hallazgos) y escaneo automático en CI.

```bash
cd ~/Documents/GitHub/financia-back-prats
grype financia-back:amd64 -o table     # tabla de hallazgos
# (la primera vez descarga la base de vulnerabilidades, tarda un poco)
```

**Qué tenés que ver**: ~68 hallazgos, **0 críticas**. El antes/después está en `docs/grype/comparativa.md`.

---

## FASE 7 — Explorar Azure desde el PORTAL (todo ya existe)

> Práctica pedida: encontrar cada recurso SIN ayuda. Navegación exacta abajo en "Práctica de portal".

**Verificaciones por CLI** (Terminal de la Mac):
```bash
az account show --query name -o tsv                 # suscripción activa
az group list -o table                              # grupos (rg-financia)
az resource list -g rg-financia -o table            # TODO lo de FinancIA
```

---

## FASE 8 — El Service Principal (verificarlo, no crearlo)

**Qué es**: el "usuario robot" que usa GitHub Actions para entrar a Azure.

```bash
# Ver el robot y su ID:
az ad sp list --display-name sp-financia-ci --query "[].appId" -o tsv
# Ver su rol (Contributor SOLO sobre rg-financia):
az role assignment list --assignee da176e24-6b8a-402b-ae5c-168506d0560c \
  --scope /subscriptions/14894dfa-95c3-4525-aa09-3766e96ec070/resourceGroups/rg-financia \
  --query "[].roleDefinitionName" -o tsv
```

**En GitHub**: repo → **Settings → Secrets and variables → Actions** → se ven los 3 secrets (nunca sus valores).

---

## FASE 9 — Despliegue manual (lo que hoy hace el CI solo)

⚠️ **Ojo**: esto CAMBIA la app desplegada. Practicalo solo si después sabés volver (ver Fase 12 — rollback). Lo seguro es practicar solo el build y el push (que no tocan la app):

```bash
cd ~/Documents/GitHub/financia-back-prats

# 1. Construir amd64 y etiquetarla con el SHA del commit:
docker buildx build --platform linux/amd64 --load \
  --build-arg VERSION=$(git rev-parse --short HEAD) \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  -t crfinancia.azurecr.io/financia-back:$(git rev-parse --short HEAD) .

# 2. Entrar al ACR (usa tu sesión de az de la Mac):
az acr login --name crfinancia

# 3. Publicar la imagen (NO despliega):
docker push crfinancia.azurecr.io/financia-back:$(git rev-parse --short HEAD)

# 4. Verificar que está en el registro:
az acr repository show-tags --name crfinancia --repository financia-back -o table
```

---

## FASE 10/11 — Git y los 3 casos del CI/CD

**Cómo subir cambios** (Terminal de la Mac, en la carpeta del backend):
```bash
cd ~/Documents/GitHub/financia-back-prats
git status                      # qué archivos cambiaron (nunca commitear sin mirar)
git add -A                      # preparar TODO
git commit -m "demo: cambio sin deploy"   # CASO A: solo CI
git push                        # subir → dispara el workflow
```

**Los 3 casos**:
| Caso | Cómo | Qué pasa en Actions |
|---|---|---|
| A | commit SIN `[deploy]` | CI verde (publica imagen en ACR) + CD **skipped** → app intacta |
| B | commit CON `[deploy]` en el mensaje | CI + CD → la app se actualiza |
| C | Actions → workflow → **Run workflow** → marcar **deploy** → Run | igual que B, sin tocar código |

**Mirar una ejecución**: repo → pestaña **Actions** → click en el run → click en el job → pasos con logs. Paso rojo = falló; expandirlo para ver el error.

**Cómo saber qué versión está desplegada**:
```bash
az containerapp show -n financia-back -g rg-financia \
  --query "properties.template.containers[0].image" -o tsv
# → crfinancia.azurecr.io/financia-back:<sha>  (cruzá el sha con git log)
```

---

## FASE 12 — Administrar la app (rollback, stop/start, logs)

**Rollback (volver a una versión anterior)** — Terminal de la Mac:
```bash
# 1. Ver versiones disponibles:
az acr repository show-tags --name crfinancia --repository financia-back -o table

# 2. Apuntar la app a una versión anterior (p. ej. la del deploy manual):
az containerapp update -n financia-back -g rg-financia \
  --image crfinancia.azurecr.io/financia-back:890664f

# 3. Comprobar (~30 s después):
curl https://financia-back.wonderfulpond-2573e809.southcentralus.azurecontainerapps.io/api/v1/health
# 4. VOLVER a la versión actual cuando termines (con el sha más nuevo).
```

**Stop/Start** (PORTAL, el CLI no lo soporta en express):
- App: *Container apps → `financia-back` → Overview → **Stop / Start***.
- BD: *Azure Database for PostgreSQL flexible servers → `financia-pg` → Overview → **Stop / Start***.
- ⚠️ La BD frenada se reinicia sola a los 7 días.
- Stop = cero cómputo; los datos NO se pierden.

**Logs** (PORTAL): *Container apps → `financia-back` → Monitoring → **Log stream*** → mandá requests desde Postman y mirá las líneas `MÉTODO path -> 200 (X ms)`.

---

## FASE 13 — Monitoreo

```bash
URL=https://financia-back.wonderfulpond-2573e809.southcentralus.azurecontainerapps.io

# Health público (anónimo solo ve el status):
curl -s $URL/actuator/health
# Métricas SIN token → 401 (protegidas):
curl -s -o /dev/null -w "%{http_code}\n" $URL/actuator/metrics
# Métricas CON token (login primero):
TOKEN=$(curl -s -X POST $URL/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"alumno-demo@financia.com","password":"claveDePrueba123"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
curl -s -H "Authorization: Bearer $TOKEN" $URL/actuator/metrics/hikaricp.connections.active
```

**En el portal**: Overview (gráficos de requests/CPU) · Monitoring → Log stream · Monitoring → **Logs** con KQL:

```kusto
ContainerAppConsoleLogs
| where ContainerAppName == "financia-back"
| project TimeGenerated, Log
| order by TimeGenerated desc
| take 25
```

---

## FASE 15 — La app del celu contra Azure

```bash
cd ~/Documents/GitHub/financia-front-prats
cp .env.example .env        # apunta la app a Azure (si no existe .env)
npx expo start              # escaneá el QR con Expo Go
```
Login de prueba: `alumno-demo@financia.com` / `claveDePrueba123`.
**Demo definitiva**: con la app andando en el celu, `docker compose stop api` en la Mac → la app sigue funcionando (habla con Azure, no con tu Mac).
**Volver a dev**: `rm .env` en la carpeta del front y reiniciar Expo.

---

## PRÁCTICA DE AZURE PORTAL (encontrar todo sin ayuda)

1. **Suscripción activa**: portal.azure.com → click en tu cuenta/icono ⚙️ arriba a la derecha → *"Cost Management + Billing"* o en cualquier recurso mirá el campo *Subscription*. Debe decir **Azure for Students** (la activa; hay otra igual de la cursada vieja que está en solo lectura).
2. **Grupo `rg-financia`**: menú ☰ → **Resource groups** → `rg-financia`. Adentro se ven los 4-5 recursos del proyecto.
3. **Imágenes en `crfinancia`**: menú ☰ → **Container registries** → `crfinancia` → menú izquierdo **Repositories** → `financia-back` → lista de tags (cada tag = un SHA de commit).
4. **Aplicación `financia-back`**: menú ☰ → **Container apps** → `financia-back` → **Overview** (estado, URL, imagen actual, gráficos).
5. **Servidor `financia-pg`**: menú ☰ → **Azure Database for PostgreSQL flexible servers** → `financia-pg` → **Overview** (estado, versión, nombre del host).
6. **Logs y métricas**: dentro de `financia-back` → **Monitoring → Log stream** (en vivo) y **Monitoring → Logs** (consultas KQL); métricas en el **Overview**.
7. **Imagen actualmente desplegada**: `financia-back` → **Overview** → campo **Image** (o el comando `az containerapp show --query ...image` de la Fase 10/11).

---

## Comandos que más vas a repetir (chuleta)

```bash
# Docker local
docker compose up -d --build | docker compose ps | docker compose logs -f api | docker compose down

# Git
git status | git add -A | git commit -m "..." | git push

# Azure (Mac)
az containerapp show -n financia-back -g rg-financia --query "properties.template.containers[0].image" -o tsv
az acr repository show-tags --name crfinancia --repository financia-back -o table
az containerapp update -n financia-back -g rg-financia --image crfinancia.azurecr.io/financia-back:<sha>

# Verificación
curl https://financia-back.wonderfulpond-2573e809.southcentralus.azurecontainerapps.io/api/v1/health
```
