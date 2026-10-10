package com.FinancIA.api.controller;

import jakarta.validation.Valid;
import com.FinancIA.api.domain.Usuario;
import com.FinancIA.api.dto.AuthRequestDTO;
import com.FinancIA.api.dto.AuthResponseDTO;
import com.FinancIA.api.dto.RegisterRequestDTO;
import com.FinancIA.api.dto.SesionDTO;
import com.FinancIA.api.exception.ResourceNotFoundException;
import com.FinancIA.api.repository.UsuarioRepository;
import com.FinancIA.api.security.JwtService;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Endpoints de autenticación.
 *
 * POST /api/v1/auth/register → crea usuario (password BCrypt) y devuelve JWT.
 * POST /api/v1/auth/login    → valida credenciales con el DaoAuthenticationProvider
 *                              (UsuarioDetailsService + BCrypt) y devuelve JWT.
 * GET  /api/v1/auth/validate → protegido: devuelve 200 solo si el JWT del header
 *                              es válido. Sirve para restaurar la sesión y para
 *                              demostrar validación de tokens en Postman.
 */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final UsuarioRepository usuarioRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthenticationManager authenticationManager;

    public AuthController(UsuarioRepository usuarioRepository,
                          PasswordEncoder passwordEncoder,
                          JwtService jwtService,
                          AuthenticationManager authenticationManager) {
        this.usuarioRepository = usuarioRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
        this.authenticationManager = authenticationManager;
    }

    @PostMapping("/register")
    public AuthResponseDTO registrar(@RequestBody @Valid RegisterRequestDTO request) {
        // Normalizamos el email a minúsculas para evitar duplicados por case
        String email = normalizarEmail(request.getEmail());

        if (usuarioRepository.findByEmailIgnoreCase(email).isPresent()) {
            throw new IllegalArgumentException("El email ya está registrado");
        }

        Usuario usuario = new Usuario();
        usuario.setNombre(request.getNombre());
        usuario.setEmail(email);
        usuario.setPassword(passwordEncoder.encode(request.getPassword()));
        usuarioRepository.save(usuario);

        return new AuthResponseDTO(jwtService.generarToken(usuario.getEmail()),
                usuario.getEmail(), usuario.getPerfilInversor());
    }

    @PostMapping("/login")
    public AuthResponseDTO login(@RequestBody @Valid AuthRequestDTO request) {
        String email = normalizarEmail(request.getEmail());

        // Delega la validación en el AuthenticationManager (DaoAuthenticationProvider):
        // usa UsuarioDetailsService + PasswordEncoder. Si las credenciales son
        // incorrectas lanza BadCredentialsException → GlobalExceptionHandler → 401.
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(email, request.getPassword()));

        Usuario usuario = usuarioRepository.findByEmailIgnoreCase(email).orElseThrow();

        return new AuthResponseDTO(jwtService.generarToken(usuario.getEmail()),
                usuario.getEmail(), usuario.getPerfilInversor());
    }

    /**
     * El filtro JWT ya validó el token (si no, Spring Security responde 401
     * antes de llegar acá). Devolvemos los datos del usuario autenticado.
     */
    @GetMapping("/validate")
    public SesionDTO validar(Authentication authentication) {
        Usuario usuario = usuarioRepository.findByEmailIgnoreCase(authentication.getName())
                .orElseThrow(() -> new ResourceNotFoundException("Usuario autenticado no encontrado"));
        return new SesionDTO(usuario.getEmail(), usuario.getPerfilInversor());
    }

    /** Trim + minúsculas: "Maxi@Mail.com" → "maxi@mail.com". */
    private String normalizarEmail(String email) {
        return email == null ? "" : email.trim().toLowerCase();
    }
}
