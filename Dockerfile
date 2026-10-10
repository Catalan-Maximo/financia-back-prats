# syntax=docker/dockerfile:1

# ── Etapa 1: compilación (Maven + Java 21) ────────────────────────────────
# Solo se copia pom + wrapper primero para cachear la resolución de
# dependencias: si el pom no cambia, esta capa se reutiliza.
FROM maven:3.9-eclipse-temurin-21-noble AS builder
WORKDIR /app

COPY pom.xml ./
COPY .mvn .mvn
COPY mvnw ./
RUN ./mvnw dependency:go-offline -B

# El código y el empaquetado. Los tests corren en CI/local antes del build
# de imagen; acá no se repiten (y no hay BD en el build).
COPY src ./src
RUN ./mvnw package -DskipTests -B

# ── Etapa 2: runtime mínimo ───────────────────────────────────────────────
# distroless: sin shell, sin package manager, sin apt — solo la JRE y
# certificados. Imagen nonroot: el proceso NO corre como root.
FROM gcr.io/distroless/java21-debian13:nonroot
WORKDIR /app
USER nonroot

# Etiquetas OCI: trazabilidad (versión, commit, fecha, repo de origen).
# Se pasan como --build-arg en CI y en el script manual.
ARG VERSION=dev
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="financia-back-prats" \
      org.opencontainers.image.description="Backend FinancIA - Spring Boot 4 / Java 21" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.source="https://github.com/Catalan-Maximo/financia-back-prats"

COPY --from=builder --chown=nonroot:nonroot /app/target/financia-api.jar /app/financia-api.jar

EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "/app/financia-api.jar"]
