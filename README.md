# FinancIA — Backend (Spring Boot) + DevOps

Backend de FinancIA: app de finanzas personales (mercados, cripto, IA, packs de inversión).
**Spring Boot 4.0.8 · Java 21 · Maven · PostgreSQL · JWT · Docker · GitHub Actions · Azure.**

Frontend: [financia-front-prats](https://github.com/Catalan-Maximo/financia-front-prats) (React Native/Expo).

## Arquitectura desplegada

```
GitHub (push) → GitHub Actions (CI: test + build + Grype | CD: ACR + deploy condicionado)
             → crfinancia.azurecr.io/financia-back:<sha>
             → Container App financia-back (ambiente financia-env, South Central US)
             → Azure PostgreSQL financia-pg (TLS)
URL: https://financia-back.wonderfulpond-2573e809.southcentralus.azurecontainerapps.io
```

## Ejecución local

```bash
cp .env.example .env        # completar DB_PASSWORD y JWT_SECRET (mínimo 32 chars)
docker compose up -d --build   # postgres (5433) + backend (8080)
curl http://localhost:8080/api/v1/health
```

Compilar/testear sin Docker: `./mvnw test` (requiere PostgreSQL local y `JWT_SECRET`).

## Documentación

| Doc | Contenido |
|---|---|
| [docs/arquitectura.md](docs/arquitectura.md) | Stack, recursos, traducción Go (cursada) → Java, flujo end-to-end, fases |
| [docs/docker.md](docs/docker.md) | Dockerfile multietapa, OCI labels, amd64, Compose, comandos |
| [docs/azure.md](docs/azure.md) | Recursos reales, costos, limitaciones de la suscripción, operaciones |
| [docs/ci-cd.md](docs/ci-cd.md) | Workflow, los 3 casos, secretos, versionado, errores históricos |
| [docs/seguridad.md](docs/seguridad.md) | JWT, Spring Security, Grype (188→68), CodeQL |
| [docs/monitoreo.md](docs/monitoreo.md) | Actuator, métricas, logs, KQL, 12 factores |
| [docs/guia-parcial.md](docs/guia-parcial.md) | **16 escenarios, 50 preguntas, dificultades, simulacro** |
| [docs/grype/](docs/grype/) | Informes crudos y comparativa de vulnerabilidades |

## CI/CD (resumen)

- Push a `main` → **CI**: `mvn test` (PostgreSQL como service), build amd64, **Grype** (falla si hay críticas), y **publicación en ACR** con tag = SHA (publicar ≠ desplegar).
- Commit con `[deploy]` o dispatch manual con la casilla → **+ CD**: login con Service Principal, update de la Container App con la imagen publicada, verificación de health.

## Credenciales / secretos

- Local: `.env` (gitignored; plantilla en `.env.example`).
- CI: GitHub Secrets (`AZURE_CREDENTIALS`, `AZURE_DB_PASSWORD`, `AZURE_JWT_SECRET`).
- Azure: secretos de la Container App + PostgreSQL.
- Postman: colección en `postman/FinancIA-Backend-JWT.postman_collection.json`.
