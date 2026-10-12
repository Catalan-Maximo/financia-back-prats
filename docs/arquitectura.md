# Arquitectura del proyecto FinancIA (DevOps)

## 1. Qué es este proyecto

FinancIA es una app de finanzas personales (mercados, cripto, IA, packs de inversión)
desarrollada en la materia previa con **React Native (Expo) + Spring Boot + PostgreSQL**.
Este documento describe la capa de infraestructura y automatización construida
aplicando los contenidos de Ingeniería de Software Aplicada — originalmente
aprendidos con un proyecto en **Go + Fiber** (`goat-grup-one`) y **adaptados** a
este stack, no copiados.

## 2. Repositorios

| Repo | Rol | Remoto |
|---|---|---|
| `financia-back-prats` | Backend Spring Boot 4 / Java 21 / Maven + toda la infraestructura DevOps | `github.com/Catalan-Maximo/financia-back-prats` |
| `financia-front-prats` | App móvil Expo (React Native 0.86 / SDK 57) | `github.com/Catalan-Maximo/financia-front-prats` |
| `goat-grup-one` (referencia) | Proyecto Go de la cursada — solo lectura, referencia conceptual | `github.com/DannyOkk/goat-grup-one` |

## 3. Traducción de conceptos: de Go (cursada) a Java/Spring Boot (este proyecto)

| Concepto de la cursada | En goat-grup-one (Go) | En FinancIA (Java) | Diferencia clave |
|---|---|---|---|
| App | Go + Fiber, puerto 3000, sin BD | Spring Boot 4.0.8, Java 21, puerto 8080, **con PostgreSQL** | La BD es el cambio estructural: en prod vive en Azure |
| Dockerfile | Multietapa golang → distroless-static | Multietapa maven+temurin → **distroless java21-debian13 nonroot** | Misma idea (distroless), imagen Java |
| Compose | App sola | **api + postgres** con healthcheck y volumen | Compose ahora levanta también la BD |
| CI | Workflow solo build+push | **CI + CD separados**: test, Grype, push y deploy condicionado | El original no desplegaba |
| Despliegue manual | `script_az.py` (1422 líneas) | Comandos `az` + YAML declarativo + CI | Mismo resultado con menos código; **mismo esquema de nombres que el CI** |
| Versionado | Script usaba tags del `.env`; CI usaba SHA → **incompatibles** | **Siempre `financia-back:<sha>`** (manual y CI) | Problema heredado resuelto |
| Secretos | `.env` local con credenciales del SP | **GitHub Secrets** + secretos de ACA | Sin credenciales en archivos versionados |
| Azure | ACR + Container Apps Environment + App | ACR `crfinancia` + ambiente `financia-env` + app `financia-back` + **Azure PostgreSQL** | Recursos recreados en la suscripción activa (ver [azure.md](azure.md)) |
| Seguridad | Ninguna en la app | **JWT + Spring Security + Grype en CI** | Capa nueva completa |
| Monitoreo | `az containerapp logs` | **Actuator + Log Analytics + métricas del portal** | Observabilidad real |

## 4. Recursos reales en Azure (suscripción Azure for Students)

| Recurso | Nombre | Notas |
|---|---|---|
| Resource Group | `rg-financia` | Región metadata Brazil South (irrelevante) |
| Container Registry | `crfinancia` (`crfinancia.azurecr.io`) | SKU Basic, South Central US |
| Container Apps Environment | `financia-env` | **Express** (consumo) — ver limitaciones en [azure.md](azure.md) |
| Container App | `financia-back` | URL: `https://financia-back.wonderfulpond-2573e809.southcentralus.azurecontainerapps.io` |
| PostgreSQL Flexible | `financia-pg.postgres.database.azure.com` | B1ms, PG 17, usuario `financia`, base `financia`, TLS obligatorio |
| Log Analytics | `workspacergfinancia8d74` | Logs de la app |
| Service Principal | `sp-financia-ci` | Contributor solo sobre `rg-financia` |

## 5. Flujo completo end-to-end

```mermaid
flowchart TB
    DEV[Dev en VS Code] -->|git push| GHA[GitHub Actions]
    GHA --> CI[Job CI: mvn test<br/>+ build amd64<br/>+ Grype]
    CI -->|mensaje [deploy] o dispatch| CD[Job CD: azure/login SP<br/>+ push ACR<br/>+ update ACA<br/>+ verify health]
    CD --> ACR[crfinancia.azurecr.io<br/>financia-back:SHA]
    ACR --> ACA[Container App<br/>financia-back]
    ACA --> PG[Azure PostgreSQL<br/>financia-pg]
    ACA -->|stdout| LA[Log Analytics]
    PHONE[App Expo en el celu] -->|HTTPS + JWT| ACA
    POSTMAN[Postman] -->|HTTPS + JWT| ACA
```

## 6. Cómo se enlazan las fases (el hilo conductor)

- **F1** (backend compila + env vars) → sin esto nada de lo demás funciona.
- **F2** (JWT) → define QUÉ protege el backend que vamos a desplegar.
- **F3** (HikariCP) → define CÓMO el backend usa la BD en cualquier entorno.
- **F4** (Dockerfile) → empaqueta todo lo anterior en una imagen inmutable.
- **F5** (Compose) → reproduce producción en local.
- **F6** (Grype) → verifica que la imagen sea segura ANTES de existir en la nube.
- **F7** (Azure) → crea el destino (registro, ambiente, BD).
- **F8** (Service Principal) → crea la LLAVE para que GitHub entre a Azure sin contraseñas humanas.
- **F9** (despliegue manual) → valida cada eslabón de la cadena antes de automatizar.
- **F10/F11** (CI/CD) → automatiza F4+F6+F9 con condiciones explícitas de despliegue.
- **F12** (gestión) → operar la app día a día (estado, logs, stop/start, rollback).
- **F13** (monitoreo) → demostrar con datos que todo lo anterior funciona.
- **F14** (CodeQL) → evaluado y descartado (opcional del profesor; Grype cubre el requisito).
- **F15** (React Native) → el consumidor final de toda la cadena.
- **F16/F17** → auditoría y esta documentación.
