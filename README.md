# Feedback de clases — Docker

El frontend (React/Vite) se construye con Node y se sirve con Nginx.
El backend (FastAPI) corre con Python 3.13 y Uvicorn. Las dependencias
se instalan a partir de `package-lock.json` y `uv.lock`.

## Construir y ejecutar

1. Iniciar Docker Desktop.
2. Copiar `.env.example` a `.env` y completar `POSTGRES_PASSWORD` (alfanumérica)
   y `JWT_SECRET` (mínimo 32 caracteres; se puede generar con `openssl rand -hex 32`).
3. Desde la raíz del proyecto:

   ```sh
   docker compose up --build -d
   ```

Compose inicia PostgreSQL, aplica las migraciones con Alembic y luego inicia
el backend y el frontend. La base de datos se conserva en un volumen.

- Frontend: http://localhost:8080
- Documentación de la API: http://localhost:8000/docs
- Estado de API y base: http://localhost:8000/api/health

El navegador llama a `/api` en el mismo origen; Nginx reenvía esas solicitudes
al servicio `backend:8000`, conservando la ruta completa.
Las rutas del frontend tienen fallback a `index.html` para React Router.

Para cargar los datos de demostración opcionales (este comando reinicia los
datos existentes; usar solamente en una base de desarrollo):

```sh
docker compose exec backend python -m app.seed
```

Para ver logs o detener los servicios:

```sh
docker compose logs -f
docker compose down
```

## Construir las imágenes por separado

```sh
docker build -t feedback-backend:local ./backend
docker build -t feedback-frontend:local ./frontend
```

La imagen del backend requiere `DATABASE_URL` y `JWT_SECRET` al ejecutarse,
y una base con las migraciones aplicadas. La configuración de Nginx espera
que el backend sea accesible con el nombre `backend` en la misma red Docker;
Compose configura esa red automáticamente.

Para compilar el frontend con otra URL pública de API:

```sh
docker build --build-arg VITE_API_URL=https://api.ejemplo.com -t feedback-frontend:local ./frontend
```

`VITE_API_URL` se define durante la construcción y no debe incluir `/api`.
Si se usa otro origen, configurar `CORS_ORIGINS` en el backend con la URL del frontend.
