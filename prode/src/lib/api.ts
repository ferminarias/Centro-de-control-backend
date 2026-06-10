// Base URL del backend.
//
// En producción el frontend le pega directo a Railway: el rewrite /api de
// Vercel queda como fallback, pero agrega ~0.5–2 s de latencia por request y
// su pool de conexiones quedó enrutado a réplicas con env desactualizado
// (incidente Google OAuth, jun 2026). En dev las rutas relativas pasan por el
// proxy de Vite (localhost:8000).
export const API = import.meta.env.PROD
  ? 'https://web-production-7d1a.up.railway.app'
  : ''
