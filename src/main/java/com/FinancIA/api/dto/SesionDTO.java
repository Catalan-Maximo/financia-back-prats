package com.FinancIA.api.dto;

/** Respuesta de /auth/validate: datos del usuario autenticado en el token actual. */
public record SesionDTO(String email, String perfilInversor) {}
