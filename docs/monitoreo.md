# Monitoreo y observabilidad (Fase 13)

## Componentes

- **Spring Boot Actuator** (en la imagen desde F1, configurado en F13):
  - `/actuator/health` → **público** (probes de Azure + chequeo real de BD: componente `db`).
  - `/actuator/metrics`, `/actuator/info` → **requieren JWT** (SecurityConfig).
- **Micrometer** (viene con Actuator): registra automáticamente métricas de JVM, HTTP
  (`http.server.requests`) y **HikariCP** (`hikaricp.connections.*`).
- **RequestLoggingFilter** (`config/RequestLoggingFilter.java`): cada petición queda en el
  log como `MÉTODO /path -> status (X ms)`. Saltea los health checks (ruido de probes).
- **Log Analytics** (workspace `workspacergfinancia8d74`): los stdout del contenedor llegan
  acá automáticamente (config del ambiente).
- Application Insights: **no disponible en ambientes express** (sin OpenTelemetry) —
  decisión documentada: Log Analytics + métricas del portal + Actuator cubren el requisito.

## Endpoints (con la app corriendo)

```bash
URL=https://financia-back.wonderfulpond-2573e809.southcentralus.azurecontainerapps.io

curl -s $URL/actuator/health                 # público: {"status":"UP","components":{"db":{"status":"UP"}}}
curl -s $URL/actuator/metrics                # 401 sin token
curl -s -H "Authorization: Bearer <token>" $URL/actuator/metrics/hikaricp.connections.active
```

## Desde el portal

1. **Métricas**: Container apps → `financia-back` → Overview (requests, response time,
   restarts, CPU/memoria). Hacer requests y ver los gráficos moverse.
2. **Log stream**: Monitoring → Log stream → líneas en vivo (login → línea del filtro).
3. **Log Analytics**: Monitoring → Logs → KQL:

```kusto
ContainerAppConsoleLogs
| where ContainerAppName == "financia-back"
| project TimeGenerated, Log
| order by TimeGenerated desc
| take 25

ContainerAppConsoleLogs
| where ContainerAppName == "financia-back" and Log contains "ERROR"
| project TimeGenerated, Log
| order by TimeGenerated desc
| take 25
```

## Las 8 preguntas de monitoreo del parcial

| Pregunta | Respuesta / demo |
|---|---|
| ¿Spring Boot está funcionando? | `/actuator/health` → UP (público) |
| ¿Se conecta a la BD? | componente `db` del health: UP/DOWN con detalle PostgreSQL |
| ¿Una petición llegó? | línea del RequestLoggingFilter en Log stream |
| ¿El login funcionó? | `POST /api/v1/auth/login -> 200 (X ms)` + Postman |
| ¿Cuánto tardó una petición? | `(X ms)` del filtro + métrica `http.server.requests` |
| ¿Cómo vemos un error? | Log stream / KQL `contains "ERROR"` (los 500 los loguea el GlobalExceptionHandler) |
| ¿Se está reiniciando? | gráfico de restarts del Overview + logs de arranque |
| ¿Fallaron variables de entorno? | fail-fast al arrancar (sin JWT_SECRET/DB_* no levanta) y queda en el log |

## Relación con los 12 factores

- **III. Config**: todo lo configurable vive en env vars/secretos.
- **V. Build, release, run**: imagen inmutable (build) ≠ config del ambiente (release) ≠ Container App (run).
- **VII. Port binding**: la app exporta por 8080; Azure enruta — la app no sabe de infra.
- **XI. Logs**: la app escribe a stdout; el ambiente los lleva a Log Analytics.
  (El factor XI es solo los logs; la observabilidad completa agrega métricas y health.)
