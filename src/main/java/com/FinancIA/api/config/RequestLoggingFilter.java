package com.FinancIA.api.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Registra cada petición HTTP: método, path, status y duración.
 * Es lo que permite responder "¿la petición llegó al servidor?" y
 * "¿cuánto tardó?" mirando los logs (Log stream / Log Analytics).
 * Se saltean los health checks para no llenar los logs con el ruido
 * de los probes de Azure.
 */
@Component
@Slf4j
public class RequestLoggingFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String path = request.getRequestURI();
        boolean esHealth = path.equals("/api/v1/health") || path.startsWith("/actuator/health");

        long inicio = System.currentTimeMillis();
        try {
            filterChain.doFilter(request, response);
        } finally {
            if (!esHealth) {
                log.info("{} {} -> {} ({} ms)", request.getMethod(), path,
                        response.getStatus(), System.currentTimeMillis() - inicio);
            }
        }
    }
}
