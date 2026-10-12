# Seguridad (Fases 2 y 6)

## Autenticación JWT (cómo funciona en esta app)

```
POST /api/v1/auth/register  → guarda usuario con BCrypt, devuelve JWT
POST /api/v1/auth/login     → DaoAuthenticationProvider (UsuarioDetailsService + BCrypt) → JWT
GET  /api/v1/auth/validate  → protegido: 200 solo si el token del header es válido
Todo lo demás               → exige "Authorization: Bearer <token>"
```

- **JWT**: HMAC-SHA512 firmado con `JWT_SECRET` (env, mínimo 32 chars — sin ella la app
  NO arranca, fail-fast). Expiración configurable (`JWT_EXPIRACION_HORAS`, default 24).
- **Filtro** `JwtAuthenticationFilter`: valida firma y expiración **sin tocar la BD**
  (JWT stateless). Un token adulterado o vencido → 401.
- **Detalle técnico**: jjwt trunca `exp` a segundos → un token de 1 s puede nacer vencido;
  el demo de expiración usa ~3 s (`JWT_EXPIRACION_HORAS=0.00084`).
- **Sin roles** en el modelo (solo autenticado/no autenticado) — no se inventaron roles.
- **Sin refresh tokens ni Remember Me** — fuera de alcance, documentado.

## Componentes de Spring Security (para la defensa)

| Concepto | Dónde |
|---|---|
| `UserDetailsService` | `security/UsuarioDetailsService.java` — usado por el login |
| `UserDetails` | `User.builder()` (patrón Builder real) con username + password BCrypt |
| `PasswordEncoder` | bean `BCryptPasswordEncoder` en `SecurityConfig` |
| `AuthenticationManager` | bean en `SecurityConfig` — usado por `AuthController.login` |
| `SecurityFilterChain` | stateless, CSRF off, públicas: `/api/v1/auth/**`, `/api/v1/health`, `/actuator/health` |
| Manejo de errores | login incorrecto → `BadCredentialsException` → **401** (antes 400) |
| CORS | `allowedOriginPatterns("*")` sin cookies — OK para app móvil (JWT en header) |

## Higiene de datos sensibles

- `@JsonIgnoreProperties({"password","pushToken"})` en `Usuario`: el hash BCrypt jamás
  viaja en respuestas JSON (verificado con `/usuarios/{id}` y `/perfil`).
- Credenciales fuera del código: `.env` gitignored, secretos de ACA, GitHub Secrets.
- La password vieja de PostgreSQL quedó en el historial del repo público (F1) → se
  eliminó del código y se creó un usuario dedicado; **rotación del usuario `postgres`
  recomendada** (no bloqueante: la BD es local).

## Grype — análisis de vulnerabilidades de la imagen

Resultados (imagen amd64, informes crudos en `docs/grype/`):

| Severidad | Inicial | Final |
|---|---|---|
| Critical | 9 | **0** |
| High | 64 | **20** |
| Medium | 79 | 24 |
| Low / Unknown | 18 | 6 |
| **Total** | **188** | **68** |

Correcciones aplicadas (sin romper nada — build + tests + smoke en cada paso):
1. Spring Boot 4.0.6 → **4.0.8** (Spring Framework 7.0.9, spring-data 4.0.7, micrometer 1.16.7, driver PG 42.7.13).
2. Overrides del BOM: **Tomcat 11.0.25**, **Jackson 2.21.7** y **tools.jackson 3.1.7**.
3. **jsoup 1.23.2**.
4. Base distroless **debian12 → debian13** (comparadas escaneando solo la base:
   112 hallazgos / 1 crítica vs 68 / 0 críticas).

Las 20 altas restantes: paquetes Debian de la base (libexpat, libuuid, libc, zlib) **sin
versión corregida publicada**. Riesgo bajo justificado: la app no usa esas rutas de código,
corre sin root y sin shell; al publicarse parches se reconstruye y reescanea.

**En CI**: Grype corre en cada push (`severity-cutoff: critical`) — si mañana aparece una
crítica, el pipeline lo frena.

## CodeQL (evaluado, no incorporado)

- Grype = escanea **dependencias e imagen** (SBOM vs CVEs).
- CodeQL = análisis **estático del código fuente** (SQL injection, XSS, etc. en el código).
- Decisión: el profesor lo mencionó como extra → no se incorporó. Habilitable en 2 minutos
  (repo → Settings → Code security → default setup) si se pide en el parcial.
