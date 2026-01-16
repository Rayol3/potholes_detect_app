# Documentación de Arquitectura del Sistema: Detección de Baches

Este documento proporciona una visión estructurada y detallada de cómo funciona todo el sistema de detección de baches, desde la captura del sensor hasta el reporte final.

---

## 1. Visión General (High-Level)

El sistema opera bajo un modelo **Híbrido Edge-Fog**, dividiendo las tareas en dos nodos físicos conectados por una red local de alta velocidad (TCP sobre USB/WiFi):

1.  **Nodo Sensor (Edge - iPhone):** Responsable de la "visión" y "sensado". Captura video RGB y datos de profundidad (LiDAR).
2.  **Nodo de Procesamiento (Server - Mac/PC):** Responsable de la "inteligencia". Procesa los datos con IA, gestiona la base de datos y muestra la interfaz al usuario.

---

## 2. Componentes del Sistema

### A. Cliente de Sensado (iOS App)
*   **Función:** Ojo remoto del sistema.
*   **Tecnología:** Swift, ARKit.
*   **Módulos Clave:**
    *   **Captura:** Obtiene frames de video (1920x1440) y mapas de profundidad (LiDAR) a 60 FPS.
    *   **Compresión:** Reduce las imágenes (JPEG q=0.5) para transmisión rápida.
    *   **Transmisión:** Envía paquetes binarios (Header + Imagen + Depth) vía TCP Socket al servidor.

### B. Servidor de Procesamiento (Python App)
*   **Función:** Cerebro del sistema.
*   **Tecnología:** Python 3.11, PySide6 (Qt), PyTorch, OpenCV.
*   **Módulos Clave:**

    *   **1. TCP Receiver (Network):**
        *   Escucha en el puerto `8080`.
        *   Reconstruye el flujo de bytes en imágenes utilizables.
    
    *   **2. Motor de IA (Detection Engine):**
        *   **Modelo:** YOLOv11l-seg (Segmentation).
        *   **Tracking:** BoTSORT/ByteTrack para seguir objetos y asignar IDs únicos.
        *   **Depth Logic:** Fusiona la detección visual (YOLO) con el mapa de profundidad para estimar la severidad del bache.

    *   **3. Gestor de Datos (Database & Logic):**
        *   **Deduplicación Espacial:** Verifica con MongoDB si un bache ya existe en un radio de 5 metros (Fórmula Haversine).
        *   **Persistencia:** Guarda metadatos en MongoDB y fotos en disco local (`/captures`).

    *   **4. Interfaz de Usuario (GUI):**
        *   Muestra video en vivo con superposición de realidad aumentada (máscaras azules).
        *   Mapea detecciones en tiempo real (Map View).

---

## 3. Flujo de Datos (Paso a Paso)

¿Qué pasa desde que aparece un bache hasta que se guarda?

1.  **Captura (0 ms):** El iPhone ve el bache. ARKit captura la luz (RGB) y la distancia (LiDAR).
2.  **Envío (< 10 ms):** El iPhone empaqueta los datos y los envía por el cable USB al Mac.
3.  **Inferencia IA (~15 ms):**
    *   El Mac recibe la imagen.
    *   YOLOv11 la analiza: "¿Hay un bache?".
    *   Si sí -> Genera una máscara (forma del bache) y una caja.
4.  **Tracking:**
    *   El sistema pregunta: "¿He visto este bache (ID #42) en el cuadro anterior?".
    *   Sí -> Solo actualiza su posición visual.
    *   No (Es nuevo) -> Pasa a validación.
5.  **Validación Geoespacial:**
    *   El sistema consulta al GPS y a la Base de Datos: "¿Hay algún bache registrado hace poco a menos de 5 metros de aquí?".
    *   Sí -> Es un duplicado físico. Se ignora.
    *   No -> **¡Es un bache nuevo!**
6.  **Registro:**
    *   Se guarda la foto en el disco duro.
    *   Se inserta el registro en MongoDB (`lat`, `lon`, `size`, `depth`).
    *   Se emite un sonido de alerta ("Ping").

---

## 4. Tecnologías y Librerías

| Capa | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Frontend** | PySide6 (Qt) | Ventanas, botones y visualización de video. |
| **IA Core** | Ultralytics YOLOv11 | Detección y segmentación de objetos. |
| **Visión** | OpenCV (cv2) | Manipulación de imágenes, dibujo de máscaras, lectura de video. |
| **Matemáticas** | NumPy | Cálculos matriciales rápidos. |
| **Backend DB** | MongoDB + PyMongo | Almacenamiento NoSQL geoespacial. |
| **Reportes** | FPDF | Generación de PDFs al final de la sesión. |

---

## 5. Optimización y Aceleración por Hardware

Un componente crítico para lograr el procesamiento en tiempo real de arquitecturas grandes (YOLOv11l) fue la optimización específica para hardware Apple Silicon.

*   **Desafío:** Ejecutar IA pesada sin servidores dedicados.
*   **Solución:** Migración a formato nativo **Core ML**.
*   **Tecnología:** Uso de la API **Metal Performance Shaders (MPS)**.
*   **Resultado:** Aprovechamiento total de la GPU del chip **M4 Pro**, logrando inferencia de baja latencia sin sobrecalentamiento excesivo de la CPU.
