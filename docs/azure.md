# Azure (Fases 7, 8, 9 y 12)

## La situación inicial (y su historia para la defensa)

La cuenta tiene **dos suscripciones "Azure for Students"** (renovación anual):
- `c9f082b2...` — la de la cursada de Go. Contiene el grupo `universidad` con el ACR
  `acringenieria`, el ambiente y la app `goat-grup-one`. Hoy está **en solo lectura**
  (créditos agotados: se pueden listar recursos pero no crear ni modificar nada).
- `14894dfa-...` — la **activa**, con permisos de propietario. Todo FinancIA vive acá.

**Historia**: "reutilizamos los conceptos y la arquitectura de la cursada, pero la
suscripción anterior quedó sin créditos, así que recreamos la infraestructura en la
suscripción renovada — con mejores prácticas (SKU Basic, permisos acotados, secretos)."

## Recursos (todos en rg-financia)

| Recurso | Nombre | Cómo se creó | Costo |
|---|---|---|---|
| Resource Group | `rg-financia` | **Portal** | gratis |
| ACR | `crfinancia` (Basic, South Central US) | **Portal** | ~US$ 5/mes |
| Container Apps env | `financia-env` (express, consumo) | **Portal** (wizard) | $0 inactivo |
| Log Analytics | `workspacergfinancia8d74` | automático con el env | centavos |
| Container App | `financia-back` | **CLI + YAML** | consumo (~US$ 0.5-1/día con min 1 réplica; $0 frenada) |
| PostgreSQL Flexible | `financia-pg` (B1ms, PG 17, base `financia`) | **Portal** | ~US$ 20-25/mes corriendo; frenada solo almacenamiento (~US$ 5-8) |
| Service Principal | `sp-financia-ci` | **CLI** (Entra bloqueado, ver abajo) | gratis |

Región: **South Central US** (la suscripción de estudiante tiene una política de
regiones permitidas; Brazil South fue rechazada al crear el ACR).

## Limitaciones de la suscripción que encontramos (todas reales)

1. **Suscripción vieja en solo lectura** → todo se recreó en la activa.
2. **Política de regiones**: solo regiones "recomendadas" (East US, Central US, etc.) →
   el primer intento de ACR en Brazil South falló con `RequestDisallowedByAzure`.
3. **Entra ID bloqueado por la universidad**: "App registrations" da 401 en el portal →
   el Service Principal se creó por **Azure CLI** (el método de la cursada).
4. **Ambiente "express"**: el wizard del portal (y el CLI en esta versión) crean ambientes
   express, que **no soportan**: contenedores sidecar (por eso no se pudo correr postgres
   al lado del backend), `revisionSuffix` en YAML, parchear secretos con
   `az containerapp update --secret`, historial de revisiones (una sola revisión),
   ni `az containerapp logs show` (bug de CLI con `eventStreamEndpoint`), ni comandos
   `az containerapp start/stop`.
   → **Decisiones tomadas**: la BD pasó a Azure PostgreSQL (más defendible y barato con
   stop/start); el deploy del CD solo cambia `--image` (env vars y secretos persisten
   entre revisiones); start/stop y logs se hacen desde el **portal**.
5. **CLI sin start/stop**: en esta versión no existen `az containerapp start/stop` (el
   script de la cursada tenía un workaround). El portal sí tiene botones Start/Stop.

## Operaciones frecuentes

```bash
# Estado, imagen desplegada, URL
az containerapp show -n financia-back -g rg-financia \
  --query "{estado: properties.runningStatus, imagen: properties.template.containers[0].image, url: properties.configuration.ingress.fqdn}"

# Listar apps
az containerapp list -g rg-financia -o table

# Tags (versiones) en el ACR
az acr repository show-tags --name crfinancia --repository financia-back -o table

# Rollback: apuntar la app a una versión anterior
az containerapp update -n financia-back -g rg-financia \
  --image crfinancia.azurecr.io/financia-back:890664f

# Logs: usar el PORTAL (Log stream). El CLI está roto para express.

# Conectarse a la BD desde la Mac
PGPASSWORD=$(cat ~/financia-pg.txt) psql \
  "host=financia-pg.postgres.database.azure.com user=financia dbname=financia sslmode=require"
```

En el portal: Start/Stop en el Overview de la app y de la BD.
⚠️ La BD frenada **se reinicia sola a los 7 días** (aviso de Azure al frenarla).

## Stop/Start y costos

- App frenada = $0 cómputo. BD frenada = solo almacenamiento.
- Disciplina: **frenar ambas al terminar cada sesión de demo**.
- Los datos de la BD sobreviven al Stop (servicio administrado con disco persistente).

## Borrado al finalizar el parcial (no ejecutar antes)

```bash
az containerapp delete -n financia-back -g rg-financia --yes
az containerapp env delete -n financia-env -g rg-financia --yes
az postgres flexible-server delete -n financia-pg -g rg-financia --yes
az acr delete -n crfinancia -g rg-financia --yes
az group delete -n rg-financia --yes   # borra TODO lo de FinancIA de un golpe
az ad sp delete --id da176e24-6b8a-402b-ae5c-168506d0560c   # borra el robot
```

## Pendientes menores anotados

- Rotar la password de la BD (pasó por el chat en F9): `az postgres flexible-server update
  -n financia-pg -g rg-financia --admin-password "$(openssl rand -hex 12)Aa!"` y actualizar
  el secret `db-pass` de la app + el secret de GitHub.
- Los 4 workspaces de la cursada vieja (suscripción c9f082b2) quedan ahí, intocables.
