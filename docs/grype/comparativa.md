# Grype: comparativa inicial vs final

Escaneo de la imagen `financia-back:amd64` (la que se despliega en Azure) con Grype.

## Resultados por severidad

| Severidad | Inicial | Final |
|---|---|---|
| Critical | 9 | **0** |
| High | 64 | **20** |
| Medium | 79 | **24** |
| Low | 15 | **6** |
| Negligible | 18 | 18 |
| Unknown | 3 | **0** |
| **TOTAL** | **188** | **68** |

Reducción: 64% de los hallazgos. Cero críticas y cero vulnerabilidades en
dependencias Java de la aplicación.

## Correcciones aplicadas

1. **Spring Boot 4.0.6 → 4.0.8** (patch): sube Spring Framework 7.0.7 → 7.0.9
   (arregla las 3 críticas de spring-webmvc), spring-data 4.0.5 → 4.0.7,
   micrometer 1.16.5 → 1.16.7, driver PostgreSQL 42.7.10 → 42.7.13.
2. **Overrides por encima del BOM** (en `pom.xml`):
   - `tomcat.version` → 11.0.25 (GHSA-9xv2-5v5q-p794, GHSA-gcx9-497g-6cp6, GHSA-h3x4-894j-xpx5)
   - `jackson-2-bom.version` → 2.21.7 (GHSA-cxp5-3px4-pw24, GHSA-wv8q-qhhj-9h54, …)
   - `jackson-bom.version` (tools.jackson 3.x) → 3.1.7 (GHSA-q4xh-88c3-wmh7, …)
3. **jsoup 1.18.3 → 1.23.2** (GHSA-65r4-943x-97jj).
4. **Imagen base: distroless java21-debian12 → java21-debian13**: base más
   nueva (0 críticas vs 1, 20 altas vs 35, 68 hallazgos vs 112 en la base).

## Vulnerabilidades pendientes (20 High, todas en la base)

Todas corresponden a paquetes Debian de la imagen base distroless
(libexpat1, libuuid1, libc6, zlib1g, gcc-libs) y **ninguna tiene versión
corregida publicada** en Debian 13 todavía (CVE de 2026 sin parche upstream).

Riesgo para esta aplicación: bajo.
- Son librerías de sistema de uso muy limitado en esta app (no parsea XML,
  no usa UUIDs de libuuid, zlib solo para compresión HTTP).
- Se mitigan operativamente: imagen sin shell y sin root (nonroot),
  superficie mínima, y actualizamos la base apenas Debian publique parches
  (reconstrucción de imagen + reescaneo).
- Los CVE críticos de estas libs (p. ej. CVE-2026-76957 de libexpat1)
  fueron resueltos al pasar de debian12 → debian13.

## Procedimiento de reescaneo

```bash
docker buildx build --platform linux/amd64 --load -t financia-back:amd64 \
  --build-arg VERSION=scan --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) .
grype financia-back:amd64 -o table
```

Informes crudos: `informe-inicial.txt/json` y `informe-final.txt/json`.
