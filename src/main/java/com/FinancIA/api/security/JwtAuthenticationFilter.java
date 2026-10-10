package com.FinancIA.api.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * Lee el header "Authorization: Bearer <token>" y valida el JWT
 * (firma + expiración, pura criptografía) sin consultar la BD.
 *
 * Esa es la ventaja del JWT stateless: la autenticación no depende
 * de la BD en cada request. Si la BD está caída, los endpoints de
 * datos fallan con 500 (el error real), no con un 401 engañoso que
 * haría desloguear al usuario del front.
 *
 * El principal es el email (subject del token); el modelo no tiene
 * roles, por eso las authorities quedan vacías.
 * Trade-off conocido: un usuario borrado de la BD mantiene su token
 * válido hasta la expiración (24 h por defecto).
 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtService jwtService;

    public JwtAuthenticationFilter(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String header = request.getHeader("Authorization");

        if (header != null && header.startsWith("Bearer ")) {
            try {
                String email = jwtService.extraerEmail(header.substring(7));
                UsernamePasswordAuthenticationToken auth =
                        new UsernamePasswordAuthenticationToken(email, null, List.of());
                auth.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                SecurityContextHolder.getContext().setAuthentication(auth);
            } catch (Exception e) {
                // Token inválido o expirado: petición sin autenticar
                SecurityContextHolder.clearContext();
            }
        }

        filterChain.doFilter(request, response);
    }
}
