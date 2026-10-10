package com.FinancIA.api.security;

import com.FinancIA.api.domain.Usuario;
import com.FinancIA.api.repository.UsuarioRepository;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * Carga el usuario desde la BD para Spring Security.
 *
 * Lo usa el DaoAuthenticationProvider (login): valida la password con
 * BCrypt. El filtro JWT NO lo usa (valida el token sin tocar la BD).
 */
@Service
public class UsuarioDetailsService implements UserDetailsService {

    private final UsuarioRepository usuarioRepository;

    public UsuarioDetailsService(UsuarioRepository usuarioRepository) {
        this.usuarioRepository = usuarioRepository;
    }

    @Override
    public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
        Usuario usuario = usuarioRepository.findByEmailIgnoreCase(email)
                .orElseThrow(() -> new UsernameNotFoundException("Usuario no encontrado: " + email));

        // El modelo no tiene roles: solo distinguimos autenticado / no autenticado,
        // por eso las authorities quedan vacías.
        // Si el password es null (usuarios creados antes del auth), usamos cadena
        // vacía para que el provider falle con BadCredentials en vez de romper.
        return User.builder()
                .username(usuario.getEmail())
                .password(usuario.getPassword() != null ? usuario.getPassword() : "")
                .authorities(List.of())
                .build();
    }
}
