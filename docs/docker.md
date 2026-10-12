# Docker (Fases 4 y 5)

## Dockerfile multietapa

`Dockerfile` (raíz del repo `financia-back-prats`):

1. **Etapa build** (`maven:3.9-eclipse-temurin-21-noble`):
   - Copia primero SOLO `pom.xml` + wrapper Maven y ejecuta `./mvnw dependency:go-offline`
     → si el pom no cambia, esa capa queda cacheada y los builds no re-descargan dependencias.
   - Copia `src` y ejecuta `./mvnw package -DskipTests` (los tests corren en CI, no dentro de la imagen).
2. **Etapa runtime** (`gcr.io/distroless/java21-debian13:nonroot`):
   - JRE + certificados TLS. **Sin shell, sin apt, sin package manager** → menos superficie de ataque y menos CVEs.
   - Corre como usuario `nonroot` (UID 65532), **no como root**.
   - `EXPOSE 8080`; `ENTRYPOINT java -XX:MaxRAMPercentage=75.0 -jar /app/financia-api.jar`
     (la JVM respeta el límite de memoria que Azure asigne al contenedor).
3. **Etiquetas OCI** (trazabilidad): `VERSION`, `VCS_REF` (SHA del commit), `BUILD_DATE`, `SOURCE`
   — se inyectan con `--build-arg` (el CI y el deploy manual pasan los valores reales).

`pom.xml` fija `<finalName>financia-api</finalName>` para que el Dockerfile no dependa del nombre versionado.

### Nota sobre el "Dockerfile referencia java" del profesor
No se copió tal cual: hardcodeaba `target/app.jar` (inexistente), su ENTRYPOINT tenía restos inválidos
e instalaba `build-essential` sin necesidad. Tomamos la idea (maven → distroless) y corregimos los defectos.

## Arquitectura de CPUs (importante)

- La Mac es **Apple Silicon (arm64)**; Azure Container Apps ejecuta **linux/amd64**.
- Build local nativo: `docker build` (arm64).
- Build para Azure: `docker buildx build --platform linux/amd64 --load|--push`.
- En CI (Ubuntu) el build ya es amd64 nativo.

## Comandos esenciales

```bash
cd ~/Documents/GitHub/financia-back-prats

# Build local con etiquetas OCI
docker build --build-arg VERSION=dev --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) -t financia-back:local .

# Build amd64 (Azure)
docker buildx build --platform linux/amd64 --load -t financia-back:amd64 \
  --build-arg VERSION=dev --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) .

# Inspeccionar usuario y etiquetas
docker image inspect financia-back:local --format '{{.Config.User}}'

# Ejecutar local conectado a la BD del contenedor
docker run -d --name financia-back -p 8080:8080 --env-file .env \
  -e DB_URL=jdbc:postgresql://host.docker.internal:5433/financia financia-back:local
```

## Docker Compose (entorno local completo)

`docker-compose.yml` define dos servicios:
- **db**: `postgres:17-alpine`, puerto 5433 en la Mac, volumen `financia-db-data` (persistencia),
  healthcheck con `pg_isready`.
- **api**: construida desde el Dockerfile, puerto 8080, credenciales desde `.env` (nunca en el archivo),
  `depends_on: db: condition: service_healthy` (no arranca hasta que la BD responde).

```bash
docker compose up -d --build   # levantar todo (BD primero)
docker compose ps              # estado
docker compose logs -f api     # logs en vivo
docker compose down            # parar y borrar contenedores (NO pierde datos)
docker compose down -v         # borra también el volumen (¡datos incluidos!)
docker compose stop api        # parar sin borrar
```

Regla de oro: `down` no pierde datos; `down -v` sí.

## .dockerignore

Excluye del contexto de build: `.git`, `.env`, `target/`, docs, IDE, compose, workflows.
Verificado en F4: la imagen no contiene `.env`, código fuente ni credenciales
(0 ocurrencias de la password vieja dentro del jar).

## Verificaciones que quedaron hechas (F4/F5)

- Proceso en contenedor como UID 65532 (nonroot) — `docker top`/inspect.
- Imagen amd64 **ejecutada bajo emulación** en la Mac: health OK en ~15-25 s.
- Compose: persistencia verificada (`down` → `up` → datos intactos).
- Tamaño imagen: ~395 MB sin comprimir (menos al transferir a ACR).
