# CI/CD con GitHub Actions (Fases 10 y 11)

## Archivo

`.github/workflows/ci-cd.yml` en `financia-back-prats`.

## Estructura (dos jobs separados — la teoría CI vs CD)

**Job `ci`** (corre SIEMPRE en cada push a main — no usa secretos):
1. `actions/checkout` — baja el código.
2. `actions/setup-java` (temurin 21, cache Maven).
3. **PostgreSQL como service container** (postgres:17-alpine con healthcheck) — el test
   `contextLoads` necesita BD real; no se desactivaron tests.
4. `./mvnw -B test`.
5. `docker buildx build --platform linux/amd64 --load` con etiquetas OCI (SHA del commit).
6. **Grype** (`anchore/scan-action`) con `severity-cutoff: critical` — el pipeline
   **falla si aparecen vulnerabilidades críticas**.

**Job `cd`** (corre SOLO bajo condición explícita — usa los secrets):
1. `azure/login` con el Service Principal (`secrets.AZURE_CREDENTIALS`).
2. `az acr login` + `docker buildx build --push` → imagen `crfinancia.azurecr.io/financia-back:<sha>`.
3. `az containerapp update --image <nueva>` — **solo la imagen**: las variables de entorno
   y secretos de la app persisten entre revisiones (el ambiente express no acepta
   parchear secretos; eso simplificó el paso y evitó otro error).
4. Verificación: bucle que espera `/api/v1/health` = 200.

## Los tres casos (requisito del parcial)

| Caso | Disparador | Resultado |
|---|---|---|
| A — CI sin deploy | push normal (mensaje sin `[deploy]`) | imagen construida y escaneada; CD "skipped" |
| B — CI + CD | commit con `[deploy]` en el mensaje | pipeline completo hasta la verificación en Azure |
| C — manual | pestaña Actions → "Run workflow" → marcar **deploy** | igual que B, sin tocar código |

La condición en el workflow:

```yaml
if: |
  (github.event_name == 'workflow_dispatch' && inputs.deploy) ||
  (github.event_name == 'push' && contains(github.event.head_commit.message, '[deploy]'))
```

## Secretos de GitHub (repo → Settings → Secrets and variables → Actions)

| Secret | Contenido | Quién lo usa |
|---|---|---|
| `AZURE_CREDENTIALS` | JSON `{clientId, clientSecret, subscriptionId, tenantId}` del SP | `azure/login` (job cd) |
| `AZURE_DB_PASSWORD` | password del PostgreSQL de Azure | (reservado; hoy el deploy no la reenvía porque persiste en la app) |
| `AZURE_JWT_SECRET` | clave JWT de producción | ídem |

Los secretos nunca aparecen en logs: GitHub los muestra como `***`.

## Versionado de imágenes

- Tag = **SHA corto del commit** (`financia-back:<sha>`), sin `latest`.
- El deploy manual de F9 usó el MISMO esquema (`890664f`) → manual y CI compatibles
  (el problema de la cursada — script con tags del .env vs CI con SHA — no existe acá).
- Historial real en ACR: `890664f` (manual), `cffd85c`, `a192b14`, `2cf39a5`,
  `0705a0d`, `3ceb31d` (CI).

## Errores reales del pipeline (todos documentados para la defensa)

1. **`with:` no expande shell**: `image: ...:${GITHUB_SHA::7}` llegó literal a Grype →
   fail. Fix: paso "Calcular SHA corto" con `echo "short=${GITHUB_SHA::7}" >> $GITHUB_OUTPUT`
   y uso de `${{ steps.sha.outputs.short }}`.
2. **`--secret` sin repetir el flag**: `--secret db-pass=... jwt-secret=...` → el CLI
   rechazó `jwt-secret` como argumento. Fix: `--secret` repetido por cada valor.
3. **Express no acepta parchear secretos** (`ExpressEnvironmentFeatureNotSupported`):
   el fix final fue simplificar el deploy a solo `--image`.
4. Avisos cosméticos resueltos: `actions/checkout@v5`, `actions/setup-java@v5`,
   `azure/login@v3` (Node 20 deprecado).

## Cómo leer una ejecución

Repo → pestaña **Actions** → run → jobs en columna izquierda → click en un job →
pasos con logs expandibles. Un paso rojo = pipeline fallido; el log indica la causa.
"Rerun all jobs" / "Re-run failed jobs" permite reintentar sin re-pushear.

## Historia de runs (evidencia)

| Run | Qué pasó |
|---|---|
| #1 (`5802167`) | primer workflow → CI falló en Grype (bug del `with:`) |
| #2 (`bf1a4f9`) | fix del SHA → **CI verde, CD skipped** (CASO A) |
| `cffd85c` | primer `[deploy]` → CD falló en `--secret` |
| `a192b14` | fix del flag → deploy no llegó a aplicarse (la app siguió en `890664f`) |
| `2cf39a5` | CD falló en patch de secrets del ambiente express |
| `0705a0d` | deploy simplificado a `--image` → **CASO B verde**, health con mensaje nuevo |
| CASO C | disparo manual con la casilla deploy → verde |
| `3ceb31d` | Fase 13 (observabilidad) → verde, health público con db UP |
