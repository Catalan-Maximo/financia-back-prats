package com.FinancIA.api.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Configuración de Spring Security:
 * - Sesión stateless (JWT en cada request).
 * - Públicos: /api/v1/auth/** (login/register) y /api/v1/health.
 *   /api/v1/auth/validate es la excepción: exige token (devuelve 200 si es válido).
 * - Todo lo demás requiere token.
 * - CORS delegado a CorsConfig (WebMvcConfigurer).
 *
 * El AuthenticationManager usa automáticamente el UsuarioDetailsService
 * y el PasswordEncoder (BCrypt) definidos en este contexto.
 */
@Configuration
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtFilter;

    public SecurityConfig(JwtAuthenticationFilter jwtFilter) {
        this.jwtFilter = jwtFilter;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .cors(Customizer.withDefaults())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            // Sin token → 401 (no 403): el cliente sabe que debe autenticarse
            .exceptionHandling(e -> e.authenticationEntryPoint(
                    (request, response, ex) -> response.sendError(401)))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/v1/auth/validate").authenticated()
                .requestMatchers("/api/v1/auth/**", "/api/v1/health").permitAll()
                // Health de Actuator público para probes/monitoreo; el resto
                // de /actuator (metrics, info...) sigue exigiendo JWT.
                .requestMatchers("/actuator/health").permitAll()
                .anyRequest().authenticated())
            .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    /** Manager global: se usa en el login con el DaoAuthenticationProvider auto-configurado. */
    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration configuration)
            throws Exception {
        return configuration.getAuthenticationManager();
    }
}
