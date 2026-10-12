# Guía para el parcial — escenarios, preguntas y dificultades

> Valores reales usados en todo este documento:
> - URL backend: `https://financia-back.wonderfulpond-2573e809.southcentralus.azurecontainerapps.io`
> - ACR: `crfinancia.azurecr.io` · Repo: `financia-back` · RG: `rg-financia` · App: `financia-back` · BD: `financia-pg`
> - Usuario demo: `alumno-demo@financia.com` / `claveDePrueba123`
> - SP: `sp-financia-ci` · Workspace: `workspacergfinancia8d74`
> - Versión actual desplegada: la del último commit (`3ceb31d` al escribir esto)

---

# PARTE 1 — Escenarios prácticos (lo que el profesor puede pedir)

## E1. Identificar suscripción y recursos de Azure
1. **Qué pide**: mostrar dónde vive todo en Azure.
2. **Concepto**: jerarquía Subscription → Resource Group → recursos; suscripciones de estudiante.
3. **VS Code**: nada.
4. **Comandos**: `az account show --query name -o tsv` · `az group list -o table` · `az resource list -g rg-financia -o table`.
5. **GitHub**: nada.
6. **Portal**: menú ☰ → Resource groups → `rg-financia` → ver ACR, Container App, PostgreSQL, workspace.
7. **Resultado**: la tabla de recursos de `rg-financia`.
8. **Demo**: abrir el RG y nombrar cada recurso con su función.
9. **Explicación**: "todo el proyecto vive en un solo grupo para controlar costos y poder borrarlo con un comando; hay DOS suscripciones Azure for Students: la de la cursada quedó en solo lectura por créditos agotados y recreamos todo en la renovada".
10. **Errores**: si `az` no está logueado → `az login` (navegador).

## E2. Encontrar imágenes versionadas en ACR
1. **Qué pide**: mostrar dónde y cómo están guardadas las versiones.
2. **Concepto**: registro de contenedores + tags por SHA.
3. **VS Code**: nada.
4. **Comandos**: `az acr repository list --name crfinancia -o table` · `az acr repository show-tags --name crfinancia --repository financia-back -o table`.
5. **GitHub**: los tags provienen de los commits.
6. **Portal**: Container registries → `crfinancia` → Repositories → `financia-back` → tags.
7. **Resultado**: lista de tags (890664f, cffd85c, …, 3ceb31d).
8. **Demo**: correlacionar un tag con su commit (`git log --oneline | grep <sha>`).
9. **Explicación**: "cada imagen se identifica con el SHA del commit que la generó; sin `latest`; manual y CI usan el mismo esquema".
10. **Errores**: ningún tag ≠ ningún push (revisar runs de Actions).

## E3. Construir una imagen Docker
1. **Qué pide**: build manual de la imagen.
2. **Concepto**: Dockerfile multietapa, etiquetas OCI, arquitectura amd64.
3. **VS Code**: editar código si corresponde.
4. **Comandos**: el build con `--build-arg` (ver [docker.md](docker.md)).
5. **GitHub**: nada (el CI lo hace solo en cada push).
6. **Portal**: nada.
7. **Resultado**: imagen local `financia-back:local` / amd64.
8. **Demo**: `docker image inspect` mostrando User=nonroot y Labels OCI.
9. **Explicación**: "multietapa maven→distroless; corre sin root y sin shell; las etiquetas OCI documentan versión, commit, fecha y origen".
10. **Errores**: Mac ARM vs Azure amd64 → usar `--platform linux/amd64`; sin Docker Desktop → arrancarlo.

## E4. Ejecutar Grype
1. **Qué pide**: escaneo de vulnerabilidades en vivo.
2. **Concepto**: SBOM vs base de CVEs; severidades; CVSS.
3. **VS Code**: nada.
4. **Comandos**: `grype financia-back:amd64 -o table` (o la imagen que exista).
5. **GitHub**: el CI lo corre en cada push con corte en critical.
6. **Portal**: nada.
7. **Resultado**: tabla de hallazgos (68, 0 críticas).
8. **Demo**: mostrar `docs/grype/comparativa.md` con el antes/después (188→68).
9. **Explicación**: "Grype arma el inventario (SBOM) de la imagen y lo cruza con la base de CVEs; bajamos de 9 críticas a 0 actualizando Spring Boot/Tomcat/Jackson y cambiando la base distroless a debian13; las 20 altas restantes no tienen parche publicado y su riesgo es bajo (libs de sistema que la app no usa)".
10. **Errores**: primera corrida descarga la BD de vulnerabilidades (tarda); sin Docker no hay imagen que escanear.

## E5. Push que ejecute CI sin deploy (CASO A)
1. **Qué pide**: "modifiquen, generen la imagen, pero NO desplieguen".
2. **Concepto**: CI ≠ CD; condición `[deploy]`.
3. **VS Code**: cambiar algo trivial (p. ej. un comentario o el mensaje de health) y commitear SIN `[deploy]`.
4. **Comandos**: `git add -A && git commit -m "cambio sin deploy" && git push`.
5. **GitHub**: Actions → ver el run: CI verde y CD **skipped**.
6. **Portal**: la app sigue con la MISMA imagen anterior (Overview).
7. **Resultado**: nueva imagen en ACR (tag nuevo), app sin cambios.
8. **Demo**: comparar el tag nuevo en ACR con la imagen activa de la app (distintos).
9. **Explicación**: "el push dispara solo la integración continua: tests, build y escaneo; el despliegue exige una condición explícita para no publicar cambios sin querer".
10. **Errores**: CI rojo → abrir el paso fallido y leer el log (los errores históricos están en [ci-cd.md](ci-cd.md)).

## E6. Publicar imagen en ACR sin desplegar
1. **Qué pide**: imagen en el registro sin tocar la app.
2. **Concepto**: build/push ≠ deploy (el workflow original de Go solo hacía esto).
3. **VS Code**: nada.
4. **Comandos**: `az acr login --name crfinancia` + `docker buildx build --platform linux/amd64 --push -t crfinancia.azurecr.io/financia-back:<tag> .` (manual).
5. **GitHub**: el CASO A deja la imagen en ACR sin desplegar (el job cd no corre) — o ejecutar solo el push manual.
6. **Portal**: ACR → tag nuevo presente; la app sin cambios.
7. **Resultado**: imagen en ACR, app intacta.
8. **Demo**: `az acr repository show-tags` vs `az containerapp show --query ...image`.
9. **Explicación**: "publicar y desplegar son pasos separados; el ACR es el almacén de versiones, desplegar es apuntar la app a una".
10. **Errores**: `az acr login` sin sesión → `az login`; push lento la primera vez.

## E7. Activar CD con [deploy] (CASO B)
1. **Qué pide**: cambio de código + despliegue automático.
2. **Concepto**: despliegue continuo condicionado por convención de commit.
3. **VS Code**: cambio visible (health message es el elegido).
4. **Comandos**: `git add -A && git commit -m "[deploy] ..." && git push`.
5. **GitHub**: Actions → CI verde → CD verde con sus 5 pasos.
6. **Portal**: la app muestra la imagen nueva; Overview → revisión actualizada.
7. **Resultado**: nueva versión viva en Azure.
8. **Demo**: `curl <URL>/api/v1/health` → mensaje nuevo; Postman login → 200.
9. **Explicación**: "el mensaje `[deploy]` es la condición explícita que une CI y CD: sin ella, solo se construye y escanea".
10. **Errores**: app frenada → el paso final de verificación falla: **Start desde el portal antes de pushear** (o inmediatamente después).

## E8. Desplegar manualmente desde GitHub Actions (CASO C)
1. **Qué pide**: disparar el pipeline a mano.
2. **Concepto**: `workflow_dispatch` con inputs.
3. **VS Code**: nada.
4. **Comandos**: nada (opcional `gh workflow run` si estuviera autenticado).
5. **GitHub**: Actions → workflow → **Run workflow** → rama main → marcar **deploy** → Run.
6. **Portal**: verificar la app tras el run.
7. **Resultado**: CI + CD sin tocar código.
8. **Demo**: comparar que la app responde igual (misma imagen reconstruida).
9. **Explicación**: "el dispatch permite re-ejecutar o forzar despliegues sin commits, controlado por el botón y la casilla".
10. **Errores**: si no aparece la casilla es que el workflow no tiene inputs — no es nuestro caso.

## E9. Mostrar qué versión está ejecutándose
1. **Qué pide**: identificar la versión activa.
2. **Concepto**: trazabilidad (tag = SHA = commit).
3. **VS Code**: `git log --oneline -1`.
4. **Comandos**: `az containerapp show -n financia-back -g rg-financia --query "properties.template.containers[0].image" -o tsv`.
5. **GitHub**: el SHA corresponde al último commit de main.
6. **Portal**: Overview de la app → campo Image.
7. **Resultado**: `crfinancia.azurecr.io/financia-back:<sha>`.
8. **Demo**: cruzar SHA ↔ commit ↔ ACR tag.
9. **Explicación**: "el ambiente express mantiene una sola revisión; el historial real vive en el ACR".
10. **Errores**: imagen que no corresponde a un commit → fue un deploy manual (está bien, mismo esquema).

## E10. Probar JWT con Postman
1. **Qué pide**: demostrar que la autenticación es real.
2. **Concepto**: JWT firmado, filtro, endpoints protegidos.
3. **VS Code**: backend corriendo (local o Azure).
4. **Comandos**: ninguno (colección `postman/FinancIA-Backend-JWT.postman_collection.json`).
5. **GitHub**: nada.
6. **Portal**: nada (o ver el log del login en Log stream).
7. **Resultado**: 01 health 200 · 02 register 200/400 (email ya existe → usar login) · 03 login 200 + token · 04 password mal 401 · 05 validate 200 · 06 protegido 200 · 07 sin token 401 · 08 token adulterado 401.
8. **Demo**: pegar el token en jwt.io (header/payload/firma) + ejecutar 07 y 08.
9. **Explicación**: "el login valida con BCrypt y firma el token con JWT_SECRET; cada request lo manda en Authorization; el filtro valida firma y expiración sin tocar la BD".
10. **Errores**: 02 repetido da 400 "ya registrado" (normal) → usar 03.

## E11. Consultar métricas y logs
1. **Qué pide**: demostrar observabilidad.
2. **Concepto**: Actuator, Micrometer, Log Analytics.
3. **VS Code**: nada.
4. **Comandos**: `curl <URL>/actuator/health` · `curl -H "Authorization: Bearer <token>" <URL>/actuator/metrics/hikaricp.connections.active`.
5. **GitHub**: nada.
6. **Portal**: Overview (gráficos) · Monitoring → Log stream · Logs (KQL de [monitoreo.md](monitoreo.md)).
7. **Resultado**: health UP con db UP; métricas; líneas `GET ... -> 200 (X ms)`.
8. **Demo**: hacer requests desde Postman y verlos aparecer en Log stream.
9. **Explicación**: "health público para probes; métricas protegidas con JWT; logs a stdout → Log Analytics; el filtro de peticiones registra método, path, status y duración".
10. **Errores**: CLI `az containerapp logs show` está roto para express → usar el portal (documentado).

## E12. Consultar la conexión con PostgreSQL
1. **Qué pide**: probar que la app ve la BD.
2. **Concepto**: health indicator db + HikariCP + TLS.
3. **VS Code**: nada.
4. **Comandos**: `curl <URL>/actuator/health` (componente db) · `PGPASSWORD=$(cat ~/financia-pg.txt) psql "host=financia-pg.postgres.database.azure.com user=financia dbname=financia sslmode=require" -c "SELECT 1"`.
5. **GitHub**: nada.
6. **Portal**: PostgreSQL → `financia-pg` → Overview (estado, métricas).
7. **Resultado**: `db: UP` + psql responde.
8. **Demo**: frenar la BD (Stop) → health muestra `db: DOWN` → Start → UP de nuevo.
9. **Explicación**: "el health de Actuator valida la conexión con isValid() sobre el pool de Hikari; la URL usa sslmode=require porque Azure exige TLS".
10. **Errores**: sin la regla "allow Azure services" en el firewall la app no conecta (ya configurada); password con espacios/pegado raro → reset (historia en [azure.md](azure.md)).

## E13. Detener e iniciar la aplicación
1. **Qué pide**: control operativo y de costos.
2. **Concepto**: Stop/Start de ACA y PostgreSQL.
3. **VS Code**: nada.
4. **Comandos**: no existen en este CLI para express (documentado) — portal.
5. **GitHub**: nada.
6. **Portal**: app: Overview → **Stop**/**Start** · BD: `financia-pg` → Overview → **Stop**/**Start**.
7. **Resultado**: Running ↔ Stopped; la URL deja de responder frenada; Start tarda ~30 s.
8. **Demo**: frenar la app → `curl` da timeout → Start → health 200.
9. **Explicación**: "parar = cero cómputo; los datos de la BD persisten; la BD frenada se reinicia sola a los 7 días (aviso de Azure)".
10. **Errores**: olvidarse de frenar = gasto de créditos; olvidarse de arrancar antes de la demo = health caído.

## E14. Hacer rollback
1. **Qué pide**: volver a una versión anterior.
2. **Concepto**: versionado por SHA → rollback = apuntar a otro tag.
3. **VS Code**: nada.
4. **Comandos**: `az containerapp update -n financia-back -g rg-financia --image crfinancia.azurecr.io/financia-back:890664f`.
5. **GitHub**: nada (rollback NO usa CI; es una operación de Azure).
6. **Portal**: verificar la imagen en Overview tras el comando.
7. **Resultado**: la app corre la versión vieja (~30 s).
8. **Demo**: (hecho en F12) 890664f → mensaje viejo en /health; volver a la última → mensaje nuevo.
9. **Explicación**: "cada versión queda en el ACR; el rollback es apuntar la app a un tag anterior — sin tocar código; el ambiente express tiene una sola revisión, por eso el historial vive en el ACR".
10. **Errores**: tag inexistente → `az acr repository show-tags` para ver los válidos.

## E15. Explicar Service Principal y GitHub Secrets
1. **Qué pide**: teoría + demo de la identidad del CI.
2. **Concepto**: SP = usuario robot con permisos acotados; secrets cifrados.
3. **VS Code**: nada.
4. **Comandos**: `az ad sp list --display-name sp-financia-ci --query "[].appId" -o tsv` · `az role assignment list --assignee <clientId> --scope /subscriptions/.../rg-financia`.
5. **GitHub**: Settings → Secrets and variables → Actions → los 3 secrets (valores `***`).
6. **Portal**: IAM del RG (el SP como Contributor) — el portal de Entra está bloqueado por la universidad (historia).
7. **Resultado**: SP con Contributor SOLO sobre rg-financia.
8. **Demo**: el job cd del run loguea con el SP (paso "Login en Azure" verde, sin credenciales humanas).
9. **Explicación**: "GitHub nunca ve mi contraseña: usa la del robot, revocable, con alcance mínimo; los secrets de GitHub están cifrados y se entregan solo durante la ejecución".
10. **Errores**: secret mal cargado → el paso azure/login falla con "AADSTS7000215" o similar → revisar el JSON de AZURE_CREDENTIALS.

## E16. Explicar las diferencias entre CI y CD
1. **Qué pide**: teoría fundamental.
2. **Concepto**: integración vs despliegue continuo.
3. **VS Code**: señalar los dos jobs en `.github/workflows/ci-cd.yml`.
4. **Comandos**: ninguno.
5. **GitHub**: Actions → un run con CI verde + CD skipped (CASO A) y otro con ambos (CASO B).
6. **Portal**: la app cambia solo en el CASO B/C.
7. **Resultado**: comprensión verificable.
8. **Demo**: mostrar los runs históricos.
9. **Explicación**: "CI verifica cada cambio (test, build, escaneo) sin tocar producción; CD lleva el cambio verificado a producción; el enlace entre ambos es una condición explícita ([deploy] o botón) para que nada se publique sin intención".
10. **Errores**: confundir "CI verde" con "desplegado" — el CASO A es la prueba de que son cosas distintas.

---

# PARTE 2 — Las 50 preguntas (respuesta técnica + frase oral + dónde + demo)

Formato: **P. pregunta** — Respuesta técnica → *Frase oral* → 📁 dónde → 🔬 demo/comando.

1. **¿Qué es integración continua?** — Verificar cada cambio automáticamente (build + tests + escaneo) al integrarlo al repo. → *"Cada push pasa por una batería de chequeos antes de que nadie lo use."* → 📁 job `ci` → 🔬 push sin [deploy].
2. **¿Qué es despliegue continuo?** — Llevar a producción el cambio verificado, automáticamente y bajo condición explícita. → *"Una vez que el cambio pasó los chequeos, va solo a Azure."* → 📁 job `cd` → 🔬 CASO B.
3. **¿Qué sucede cuando hacemos push a GitHub?** — El workflow arranca: CI (test+build+Grype) y, si el mensaje dice [deploy], CD (push ACR + update ACA + verify). → 📁 `.github/workflows/ci-cd.yml` → 🔬 pestaña Actions.
4. **¿Cómo generamos una imagen sin desplegar?** — Push sin [deploy]: el CI construye y escanea; el CD queda skipped. → 🔬 CASO A: tag nuevo en ACR, app con la imagen anterior.
5. **¿Cómo condicionamos el despliegue?** — `if:` con `contains(github.event.head_commit.message, '[deploy]')` o el input del dispatch. → 📁 ci-cd.yml (bloque if del job cd).
6. **¿Dónde queda la imagen Docker versionada?** — `crfinancia.azurecr.io/financia-back:<sha>`. → 🔬 `az acr repository show-tags`.
7. **¿Qué es Azure Container Registry?** — Registro privado de imágenes Docker en Azure, con versionado por tags. → 🔬 portal → Container registries → crfinancia.
8. **¿De qué grupo depende nuestro ACR?** — `rg-financia`. → 🔬 `az acr show -n crfinancia -g rg-financia`.
9. **¿De qué suscripción depende el grupo?** — Azure for Students `14894dfa-...` (la activa; hay otra vieja en solo lectura). → 🔬 `az account show`.
10. **¿Para qué usamos el Service Principal?** — Para que GitHub Actions opere Azure sin credenciales humanas. → 🔬 job cd, paso azure/login.
11. **¿Dónde están las credenciales del SP?** — GitHub Secret `AZURE_CREDENTIALS` (JSON con clientId/secret/subscription/tenant). → 🔬 Settings → Secrets.
12. **¿Cómo funciona la autenticación de GitHub Actions contra Azure?** — azure/login intercambia el JSON del SP por un token de Azure para el CLI del runner. → 🔬 log del paso "Login en Azure".
13. **¿Cómo publicamos una imagen versionada?** — `az acr login` + `docker buildx build --push -t crfinancia.azurecr.io/financia-back:<sha>` (o el job cd). 
14. **¿Cómo comprobamos que la imagen existe en ACR?** — `az acr repository show-tags --name crfinancia --repository financia-back`.
15. **¿Cómo sabemos qué versión se ejecuta en Azure?** — `az containerapp show ... --query properties.template.containers[0].image` o Overview del portal. → 🔬 E9.
16. **¿Cómo detenemos la aplicación?** — Portal → Stop (el CLI no tiene start/stop en esta versión). → 🔬 E13.
17. **¿Cómo la iniciamos?** — Portal → Start (~30 s hasta servir).
18. **¿Cómo la eliminamos?** — `az containerapp delete -n financia-back -g rg-financia --yes` (post-parcial). → 📁 [azure.md](azure.md) (lista completa de borrado).
19. **¿Cómo consultamos los logs?** — Portal → Log stream (en vivo) o Logs con KQL. El CLI está roto para express. → 📁 [monitoreo.md](monitoreo.md).
20. **¿Cómo sabemos que una aplicación funciona correctamente?** — `/actuator/health` UP (con db UP) + logs con respuestas 200. → 🔬 E11.
21. **¿Cómo probamos el login con Postman?** — Colección `postman/FinancIA-Backend-JWT.postman_collection.json`, requests 03-08. → 🔬 E10.
22. **¿Cuál es la URL real del backend?** — `https://financia-back.wonderfulpond-2573e809.southcentralus.azurecontainerapps.io/api/v1`.
23. **¿Cómo funciona JWT?** — Login válido → token firmado HMAC-SHA512 (header.payload.firma) con expiración; el cliente lo reenvía en Authorization. → 🔬 jwt.io con un token.
24. **¿Cómo se validan los tokens?** — El filtro verifica firma (JWT_SECRET) y expiración en cada request, sin tocar la BD. → 📁 `security/JwtAuthenticationFilter.java`.
25. **¿Cómo protegemos los endpoints?** — SecurityFilterChain: públicas auth/health(+actuator/health); todo lo demás autenticado; 401 sin token. → 📁 `security/SecurityConfig.java`.
26. **¿Para qué sirve UserDetailsService?** — Carga el usuario de la BD para que el DaoAuthenticationProvider valide el login. → 📁 `security/UsuarioDetailsService.java`.
27. **¿Para qué sirve HikariCP?** — Pool de conexiones JDBC: reutiliza conexiones, límites y timeouts (5 s fail-fast). → 📁 `application.yaml` → 🔬 métricas `hikaricp.connections.*`.
28. **¿Dónde almacenamos variables de entorno y secretos?** — Local: `.env` gitignored; Azure: secretos/env de ACA; CI: GitHub Secrets. → 🔬 Settings → Secrets.
29. **¿Dónde configuramos la conexión a la BD?** — Perfiles: `application-dev.yml` (local) y `application-prod.yml` (env vars + TLS). → 🔬 abrir ambos archivos.
30. **¿Cómo verificamos la conectividad con la BD?** — Health db UP + psql con sslmode=require. → 🔬 E12.
31. **¿Qué es un CVE?** — Identificador de una vulnerabilidad conocida en la base pública (Common Vulnerabilities and Exposures).
32. **¿Qué es CVSS?** — Puntuación 0-10 de la gravedad técnica de un CVE (base de severidades Critical/High/Medium/Low).
33. **¿Cómo utilizamos Grype?** — Escanea la imagen (SBOM vs CVEs) en local y en CI con corte en críticas. → 📁 `docs/grype/`.
34. **¿Qué vulnerabilidades encontramos?** — 188 hallazgos iniciales (9 críticas: Tomcat, spring-webmvc…). → 📁 comparativa.md.
35. **¿Cómo las solucionamos?** — Boot 4.0.8 + overrides (Tomcat 11.0.25, Jackson 2.21.7/3.1.7) + jsoup + base debian13. → 📁 `pom.xml`, `Dockerfile`.
36. **¿Qué hacemos si no tienen solución?** — 20 altas sin parche en libs del SO que la app no usa: riesgo aceptado, documentado, y reescaneo al publicarse parches. → 🔬 E4.
37. **¿Diferencias entre Grype y Trivy?** — Mismo objetivo (escaneo de imágenes/SBOM); motores y BD distintas; Grype (Anchore) fue el usado en la cursada; Trivy (Aqua) ofrece también IaC/misconfig. No está instalado en la Mac.
38. **¿Qué es CodeQL?** — Análisis ESTÁTICO del código fuente (patrones de bugs/vulns en el código, no en dependencias). → 🔬 decisión: no incorporado (extra). 📁 [seguridad.md](seguridad.md).
39. **¿Diferencia entre CodeQL y Grype?** — CodeQL analiza el código que escribimos; Grype el inventario de la imagen (dependencias + sistema). Complementarios.
40. **¿Cómo comprobamos que la app recibe peticiones?** — RequestLoggingFilter: líneas `MÉTODO path -> status (ms)` en Log stream. → 🔬 E11.
41. **¿Cómo obtenemos métricas del login?** — `/actuator/metrics/http.server.requests` filtrado por uri `/api/v1/auth/login` (con token). → 🔬 E11.
42. **¿Cómo sabemos cuánto tarda una petición?** — El `(X ms)` del filtro + timers de Micrometer.
43. **¿Relación entre logs y los 12 factores?** — Factor XI: la app escribe a stdout y el ambiente los transporta (Log Analytics); el factor es transporte, la observabilidad completa agrega métricas/health. → 📁 [monitoreo.md](monitoreo.md).
44. **¿Cómo configuramos desarrollo y producción?** — Perfiles Spring (`application-dev.yml` / `application-prod.yml`) + `SPRING_PROFILES_ACTIVE` + `EXPO_PUBLIC_API_URL` en el front.
45. **¿Cómo volvemos a una imagen anterior?** — `az containerapp update --image <tag-viejo>` (rollback, sin CI). → 🔬 E14.
46. **¿Cómo funciona el Dockerfile multietapa?** — Etapa build (maven, cache de dependencias) y etapa runtime (distroless nonroot, solo el jar). → 📁 `Dockerfile`.
47. **¿Diferencia entre Dockerfile y Docker Compose?** — El Dockerfile define UNA imagen; Compose orquesta VARIOS contenedores (api + db) con redes, volúmenes y dependencias para el entorno local.
48. **¿Cómo se conecta React Native con el backend de Azure?** — `EXPO_PUBLIC_API_URL` apunta a la URL HTTPS; el JWT viaja en Authorization; sin la variable usa la IP local (dev). → 📁 front `src/lib/api.ts`.
49. **¿Cómo comprobamos que no hay credenciales hardcodeadas?** — `grep -r "password" src/main/resources` (solo placeholders `${...}`) + export del filesystem de la imagen (0 hallazgos) + la app no arranca sin JWT_SECRET. → 🔬 F4/F9.
50. **¿Qué hacemos si el pipeline falla?** — Abrir el run → paso rojo → leer el log → corregir → push (o Re-run). Los 4 errores históricos y sus fixes están en [ci-cd.md](ci-cd.md).

---

# PARTE 3 — Todas las dificultades que tuvimos (y cómo se resolvieron)

1. **Wrapper Maven roto** (faltaba `.mvn/wrapper/maven-wrapper.properties`): el repo no compilaba clonado → se creó el archivo (Maven 3.9.11).
2. **Password de PostgreSQL hardcodeada en `application.yaml`** de un repo PÚBLICO → se movió a env, usuario dedicado `financia`, y se recomendó rotar la del usuario `postgres`.
3. **Hash BCrypt expuesto** en respuestas JSON (`/usuarios/{id}`, `/perfil`) → `@JsonIgnoreProperties`.
4. **Login incorrecto devolvía 400** → manejador de `BadCredentialsException` → 401.
5. **El filtro JWT consultaba la BD por request** → con la BD caída daba 401 engañosos (logout fantasma) → filtro 100% stateless.
6. **jjwt trunca `exp` a segundos** → tokens de 1 s nacían vencidos → demo de expiración con ~3 s.
7. **`target/` y `node_modules/` commiteados** → `.gitignore` + `git rm --cached`.
8. **Commit de VSCode con solo los cambios staged** → commits "vacíos" (solo borrados) → re-commit correcto por terminal.
9. **Errores falsos de Lombok en el IDE** (language server) → solo cosméticos; Maven siempre dijo la verdad.
10. **Apple Silicon vs Azure amd64** → buildx `--platform linux/amd64`.
11. **Grype: 188 hallazgos (9 críticas)** → Boot 4.0.8 + overrides + debian13 → 68 (0 críticas; 20 altas sin fix).
12. **Suscripción de la cursada en solo lectura** (créditos agotados) → infraestructura recreada en la activa.
13. **Política de regiones** de la suscripción de estudiante → Brazil South bloqueada → South Central US.
14. **Entra ID bloqueado por la universidad** (App registrations → 401) → SP por Azure CLI.
15. **Ambiente express** (creado por el wizard y por el CLI): sin sidecars → la BD no pudo ser sidecar y pasó a Azure PostgreSQL; sin `revisionSuffix`; sin parchear secretos → el CD quedó con solo `--image`; sin historial de revisiones → el historial vive en el ACR; CLI sin `start/stop` y `logs show` roto → portal.
16. **Complejidad de password de Azure PG** (3 de 4 categorías) → password con mayúsculas+símbolos.
17. **Trampas de copy-paste** (marcador `%` de zsh, espacios): 2 resets de password fallidos → se fijó por CLI con `$(cat archivo)`; la password pasó por el chat → **pendiente rotarla** (comando en [azure.md](azure.md)).
18. **Firewall de PostgreSQL**: sin "allow Azure services" la app no conecta (configurado al crear); la IP local habilita el psql de la Mac.
19. **`with:` no expande `${...}`** → Grype buscó una imagen inexistente → output de paso con el SHA.
20. **`--secret` sin repetir el flag** → error de parser del CLI → flag repetido por valor.
21. **El fix intermedio (`a192b14`) nunca desplegó**: la app siguió en `890664f` hasta que el deploy simplificado (`0705a0d`) quedó verde.
22. **Cloud Shell vs Mac**: el SP se creó en la Cloud Shell (home `/home/maximo`) → el JSON se descargó a la Mac para GitHub Secrets.
23. **Cuota de la API de GitHub agotada** por monitorear con polling → se aprende a leer la UI de Actions.
24. **El test `contextLoads` exige BD real** → en CI se levanta postgres como service container (no se desactivaron tests).
25. **Registro de proveedores** en la suscripción nueva (Microsoft.App, ContainerRegistry, DBforPostgreSQL, OperationalInsights) — necesario antes de crear recursos.
26. **Avisos de deprecación de acciones** (Node 20) → checkout@v5, setup-java@v5, azure/login@v3.

---

# PARTE 4 — Simulacro de defensa (los dos pedidos típicos)

## Pedido 1: "Hacé un cambio, subilo, construí una imagen versionada, publicala en ACR, pero NO hagas deploy"

1. VS Code: editar algo trivial (p. ej. un comentario o el mensaje de health).
2. `git add -A && git commit -m "demo: cambio sin deploy" && git push`  ← **SIN [deploy]**
3. GitHub → Actions → esperar CI verde (CD "skipped").
4. Mostrar en ACR el tag nuevo (`az acr repository show-tags`).
5. Mostrar que la app sigue con la imagen ANTERIOR (`az containerapp show --query ...image`).

## Pedido 2: "Ahora desplegá esa misma versión, comprobá que funciona, mostrame los logs y detené la aplicación"

1. Portal → `financia-back` → **Start** (si está frenada).
2. GitHub → Actions → **Run workflow** → marcar **deploy** → Run (CASO C) — o un commit con `[deploy]` (CASO B).
3. Esperar el CD verde (último paso: "la app responda" ✅).
4. `curl https://financia-back.../api/v1/health` → mensaje nuevo.
5. Portal → Monitoring → **Log stream** → mostrar las líneas de arranque + una petición de Postman.
6. Portal → app → **Stop** (+ BD → Stop) — "quedó frenada para no gastar créditos".

---

# PARTE 5 — Check del día del parcial

1. Portal: app `financia-back` **Start** → esperar ~30 s → `curl <URL>/api/v1/health` OK.
2. Portal: BD `financia-pg` **Start** (tarda ~1-2 min en Ready).
3. Postman: colección lista contra `<URL>`.
4. GitHub: pestaña Actions abierta con los runs históricos.
5. VS Code: repo limpio en main, al día (`git pull`).
6. Cosas que NO mostrar: secretos, `.env`, `deploy.yaml`, `~/financia-pg.txt`, `~/azure-credentials.json`.
