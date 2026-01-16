# Documentación de Rendimiento: Inferencia en Tiempo Real y Resolución

## 1. Resumen de Rendimiento (Benchmark)

| Componente | Especificación / Métrica | Notas |
| :--- | :--- | :--- |
| **FPS Objetivo (Cliente)** | **60 FPS** | Configuración nativa de ARKit en iPhone. |
| **FPS Efectivos (Sistema)** | **30 - 45 FPS** | Limitado por la compresión JPEG y transmisión de red (WiFi/USB). |
| **Tiempo de Inferencia (IA)** | **~5-10 ms** (GPU) | YOLOv11m sobre NVIDIA RTX 3060 Ti / Mac M1 (Neural Engine). |
| **Latencia Total** | **< 100 ms** | Desde captura hasta visualización. |

---

## 2. Adaptación de Resolución (Resolution Adaptation)

El sistema implementa una **adaptación dinámica de resolución** para equilibrar calidad de detección y velocidad de transmisión.

### A. Captura en el Cliente (iPhone)
*   **Resolución Nativa:** ARKit captura video en alta resolución (típicamente **1920x1440** o **1920x1080** dependiendo del dispositivo).
*   **Pre-procesamiento (Downscaling & Compresión):**
    *   No se realiza un redimensionado (resize) explícito de píxeles para mantener la máxima fidelidad del campo de visión (FOV).
    *   **Compresión JPEG:** Se aplica una compresión con factor de calidad **0.5 (50%)**.
    *   **Código Fuente:** `ViewController.swift` -> `uiImage.jpegData(compressionQuality: 0.5)`.
    *   **Impacto:** Reduce el tamaño del paquete de datos (~3MB -> ~300KB) permitiendo transmisión fluida sin perder detalles críticos de los baches.

### B. Ingesta en el Servidor (Mac/PC)
*   **Decodificación:** El servidor recibe el stream de bytes y lo decodifica a una matriz NumPy (`cv2.imdecode`).
*   **Inferencia YOLO:**
    *   El modelo YOLOv11m está entrenado nativamente a **640x640**.
    *   **Auto-Resize Interno:** Al invocar `model(frame)`, la librería Ultralytics redimensiona automáticamente la imagen de entrada (ej. 1920x1080) a 640x640 (manteniendo el aspecto con "letterboxing") para la inferencia.
    *   **Mapeo de Resultados:** Las coordenadas de los baches detectados se re-escalan automáticamente a la resolución original (1920x1080) para que coincidan perfectamente con la visualización en pantalla.

---

## 3. Control de Flujo (Flow Control)

Para evitar la saturación del sistema y garantizar "Tiempo Real" fluido, se implementan mecanismos de control de congestión:

1.  **Frame Dropping (Cliente iOS):**
    *   El iPhone utiliza una **Cola de Procesamiento** (`processingQueue`).
    *   Si la red o el procesamiento anterior está ocupado (`isProcessing == true`), el iPhone **descarta inmediatamente** los nuevos frames de la cámara.
    *   **Beneficio:** Evita que se acumule lag (retardo). El usuario siempre ve lo que está ocurriendo "ahora", no lo que ocurrió hace 2 segundos.

2.  **Inferencia Asíncrona (Servidor):**
    *   El servidor utiliza hilos dedicados (`DetectionThread`) para separar la recepción de red del procesamiento de IA, permitiendo que la interfaz gráfica (GUI) se mantenga responsiva a 60 FPS independientemente de la velocidad del modelo.

## 4. Requisitos de Hardware Recomendados

### Servidor (Procesamiento)
*   **Óptimo:** PC con NVIDIA RTX 3060 o superior (Inferencia < 10ms).
*   **Compatible:** Mac con Apple Silicon (M1/M2/M3). Utiliza aceleración MPS (Metal Performance Shaders).
*   **Mínimo:** CPU Moderna (i7/Ryzen 5). Inferencia ~100ms (10 FPS).

### Cliente (Sensor)
*   **Dispositivo:** iPhone 12 Pro o superior (Modelos "Pro" necesarios para sensor LiDAR).
*   **Conexión:** Cable USB-C / Lightning (Recomendado) o WiFi 5GHz.
