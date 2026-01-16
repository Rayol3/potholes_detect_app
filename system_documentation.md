# Documentación del Sistema de Detección de Baches

## 1. Arquitectura General
El sistema opera bajo una arquitectura **Cliente-Servidor Híbrida**, donde el procesamiento pesado (IA) se realiza en un servidor potente (Mac/PC) y la adquisición de datos se delega a sensores remotos (iPhone/Edge Sensor) o cámaras locales.

### Componentes Principales:
1.  **Frontend/GUI (Desktop):** Aplicación de escritorio desarrollada en **PySide6** que gestiona la visualización en tiempo real, mapas y control de sesión.
2.  **Motor de IA (Backend):** Modelo **YOLOv11** ejecutándose en la GPU de la estación base para detección de baches.
3.  **Cliente Edge (iOS):** Aplicación Swift en iPhone que utiliza **ARKit/LiDAR** para capturar video y profundidad, transmitiéndolos al servidor.
4.  **Capa de Persistencia:** Base de datos **MongoDB** para metadatos y almacenamiento en sistema de archivos local para evidencias (imágenes/PDFs).

---

## 2. Conectividad Móvil (Edge Sensing System)
La conexión entre el iPhone y el Mac se establece mediante un protocolo **TCP Socket** de baja latencia, optimizado para transmisión de video en tiempo real.

### Flujo de Conexión:
1.  **Transporte Físico:** Se recomienda **USB (Tethering)** sobre WiFi para minimizar latencia y "jitter". El iPhone crea una interfaz de red virtual (usualmente `172.20.10.x`).
2.  **Protocolo:**
    *   **Servidor (Mac):** Escucha en el puerto `8080`.
    *   **Cliente (iPhone):** Inicia la conexión (Handshake) y comienza el streaming.
3.  **Transmisión de Datos:**
    *   El iPhone captura frames de video y mapas de profundidad (LiDAR).
    *   Los datos se serializan y envían por el socket TCP.
    *   El servidor reconstruye los frames y los pasa al **Detector** (YOLO) para inferencia inmediata.

> **Nota:** La aplicación iOS no procesa IA; actúa como un "ojo inteligente" remoto, delegando la carga computacional al servidor.

---

## 3. Almacenamiento y Gestión de Datos
El sistema utiliza un enfoque dual para el almacenamiento: base de datos NoSQL para metadatos ágiles y almacenamiento en disco para archivos pesados.

### A. Base de Datos (MongoDB)
Todos los incidentes (baches detectados) se almacenan en una base de datos local llamada `potholes`, colección `detections`.

**Esquema del Documento JSON:**
```json
{
  "_id": "ObjectId(...)",
  "timestamp": "2024-05-20T10:30:00.000+00:00",
  "location": {
    "type": "Point",
    "coordinates": [-74.0060, 40.7128]  // [Longitud, Latitud] - Formato GeoJSON
  },
  "lat": 40.7128,
  "lon": -74.0060,
  "confidence": 0.85,                 // Probabilidad de detección (0.0 - 1.0)
  "size_m": 0.45,                     // Tamaño estimado en metros
  "image_path": "captures/pothole_20240520_103000.jpg" // Referencia al archivo
}
```

*   **Geo-Querying:** El uso de GeoJSON permite consultas espaciales eficientes (ej. "buscar baches en un radio de 5 metros" para evitar duplicados).

### B. Sistema de Archivos
*   **Evidencias Visuales:** Las imágenes de los baches (con Bounding Boxes dibujados) se guardan en la carpeta local `/captures`.
*   **Reportes:** Al finalizar una sesión, el sistema genera automáticamente una Orden de Trabajo en formato PDF (`Orden_Trabajo_Sesion.pdf`), que incluye una captura del mapa de ruta y la lista de incidentes.

---

## 4. Flujo de Trabajo (Pipeline)
1.  **Ingesta:** El sistema recibe video desde Webcams USB o el Cliente Edge (TCP).
2.  **Inferencia:** `DetectionThread` procesa cada frame con YOLOv11m.
3.  **Filtrado:**
    *   Si la `confianza > umbral` (ej. 0.5), se considera una detección válida.
    *   Se consulta al **GPS** para obtener coordenadas actuales.
    *   **Deduplicación:** Se verifica en MongoDB si existe un bache reciente en un radio de ~5 metros (`is_duplicate`).
4.  **Persistencia:** Si es único, se guarda la imagen en disco y el registro en MongoDB.
5.  **Visualización:** La interfaz de usuario actualiza el video en vivo, coloca un marcador en el mapa interactivo y alerta al operador.
