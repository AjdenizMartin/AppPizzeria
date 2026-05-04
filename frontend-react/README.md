# Frontend React

Este es el frontend oficial de la aplicacion.

## Desarrollo

```bash
cd frontend-react
npm install
npm run dev
```

Por defecto corre en `http://127.0.0.1:5173`.

Si el backend esta en otra URL, crea `frontend-react/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

## Build

```bash
npm run build
```

El build sale en `frontend-react/dist` y FastAPI puede servirlo como SPA unica.
