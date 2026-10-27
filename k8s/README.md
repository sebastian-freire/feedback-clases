# Kubernetes mínimo

Todos los comandos se ejecutan desde la raíz del proyecto. El kubeconfig
permanece fuera del repositorio. Estos pasos asumen imágenes públicas en Docker Hub.

Los manifiestos están separados por componente: `postgres.yaml` incluye el volumen,
el Deployment y el Service de la base; `backend.yaml` y `frontend.yaml` incluyen
el Deployment y el Service de cada aplicación.

1. En `k8s/frontend.yaml` y `k8s/backend.yaml`, reemplazar `TU_USUARIO` por el usuario de Docker Hub
   y comprobar que los nombres y la etiqueta `1.0` coincidan con las imágenes publicadas.

2. Seleccionar las credenciales y el namespace:

   ```sh
   export KUBECONFIG=/Users/manuela/Downloads/team3.kubeconfig
   kubectl get pods -n alumno-team3
   ```

3. Crear un archivo local ignorado por Git llamado `.env.k8s` con estos valores:

   ```dotenv
   POSTGRES_PASSWORD=REEMPLAZAR
   DATABASE_URL=postgresql+psycopg://feedback:REEMPLAZAR@db:5432/feedback
   JWT_SECRET=REEMPLAZAR_CON_UN_SECRETO_DE_AL_MENOS_32_CARACTERES
   ```

   Usar la misma contraseña alfanumérica en las dos primeras líneas.
   Se puede generar el JWT_SECRET con `openssl rand -hex 32`.
   Este archivo es exclusivo de Kubernetes y no necesita la misma contraseña
   que la base local de Docker Compose. No subirlo ni compartirlo.

4. Crear el Secret y aplicar los manifiestos:

   ```sh
   kubectl create secret generic feedback-secrets --from-env-file=.env.k8s -n alumno-team3
   kubectl apply -f k8s/ -n alumno-team3
   kubectl rollout status deployment/backend -n alumno-team3 --timeout=180s
   kubectl rollout status deployment/frontend -n alumno-team3 --timeout=180s
   ```

   El backend ejecuta las migraciones antes de iniciar la API. Si PostgreSQL
   todavía no está disponible, el contenedor puede reiniciarse hasta conectarse.

5. Abrir la aplicación:

   ```sh
   kubectl port-forward service/frontend 8080:80 -n alumno-team3
   ```

   Mantener esa terminal abierta y visitar http://localhost:8080.

## Diagnóstico

```sh
kubectl get pods,svc,pvc -n alumno-team3
kubectl logs deployment/backend -n alumno-team3
kubectl describe pods -n alumno-team3
```

PostgreSQL usa un volumen persistente de 1 GiB y requiere una StorageClass
predeterminada en el clúster. Si el PVC queda `Pending`, consultar al administrador
qué StorageClass usar y agregar `storageClassName` al `spec` del PVC.

Si aparece `ImagePullBackOff`, comprobar nombre, etiqueta y visibilidad de las imágenes.
Si aparece `exec format error`, la arquitectura de las imágenes no coincide con los nodos;
reconstruirlas para la arquitectura del clúster y publicarlas con una nueva etiqueta.

Para este despliegue mínimo se usa una sola réplica del backend, de modo que las
migraciones se ejecuten desde un solo contenedor. No aumentar las réplicas con
este esquema. Cambiar la contraseña del Secret no cambia la contraseña de una
base que ya fue inicializada.
