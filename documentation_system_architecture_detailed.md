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


arqui del modelo.. 
---
config:
  layout: fixed
  theme: base
---
flowchart LR
 subgraph S_IN["Entrada"]
    direction TB
        Input[("Imagen RGB<br>640 x 640 x 3")]
  end
 subgraph S_BB["Backbone: Extracción de Características"]
    direction TB
        B1["B1: Conv Stem<br>(64 ch)"]
        B2["B2: C3k2<br>(256 ch)"]
        B3["B3: C3k2<br>(512 ch) <br>Feature P3"]
        B4["B4: C3k2<br>(512 ch) <br>Feature P4"]
        B5["B5: C3k2 + SPPF<br>(512 ch)"]
        B6["B6: C2PSA<br>(512 ch) <br>Feature P5"]
  end
 subgraph S_NK["Neck: PANet - Fusión Multiescala"]
    direction TB
        N_UP1["Upsample + Concat (P5->P4)"]
        N_UP2["Upsample + Concat (P4->P3)"]
        N_DOWN1["Downsample + Concat (P3->P4)"]
        N_DOWN2["Downsample + Concat (P4->P5)"]
        Out_Small["Salida Alta Res<br>(Objetos Pequeños)"]
        Out_Med["Salida Media Res<br>(Objetos Medianos)"]
        Out_Large["Salida Baja Res<br>(Objetos Grandes)"]
  end
 subgraph S_HD["Head: Segmentación Desacoplada"]
    direction TB
        SegHead["Módulo Segment Head<br>(Procesamiento Independiente)"]
        O_Box["Bounding Boxes<br>(x, y, w, h)"]
        O_Cls["Clases<br>(Probabilidad)"]
        O_Mask["Máscaras<br>(Polígonos/Protomasks)"]
  end
    Input --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4 & N_UP2
    B4 --> B5 & N_UP1
    B5 --> B6
    B6 --> N_UP1 & N_DOWN2
    N_UP1 --> N_UP2 & N_DOWN1
    N_UP2 --> Out_Small
    Out_Small --> N_DOWN1 & SegHead
    N_DOWN1 --> Out_Med
    Out_Med --> N_DOWN2 & SegHead
    N_DOWN2 --> Out_Large
    Out_Large --> SegHead
    SegHead --> O_Box & O_Cls & O_Mask

     Input:::input
     B1:::backbone
     B2:::backbone
     B3:::backbone
     B4:::backbone
     B5:::backbone
     B6:::backbone
     N_UP1:::neck
     N_UP2:::neck
     N_DOWN1:::neck
     N_DOWN2:::neck
     Out_Small:::neck
     Out_Med:::neck
     Out_Large:::neck
     SegHead:::head
     O_Box:::output
     O_Cls:::output
     O_Mask:::output
    classDef input fill:#e1e1e1,stroke:#333,stroke-width:2px
    classDef backbone fill:#d4e6f1,stroke:#2874a6,stroke-width:2px
    classDef neck fill:#fdebd0,stroke:#d35400,stroke-width:2px
    classDef head fill:#d5f5e3,stroke:#239b56,stroke-width:2px
    classDef output fill:#f9e79f,stroke:#f1c40f,stroke-width:2px,stroke-dasharray: 5 5







esto es de  sistema acpas 


    ---
config:
  layout: dagre
---
flowchart TB
 subgraph Edge[" Nodo Sensor (Edge:iOS)"]
    direction TB
        ARKit[("ARKit Módulo<br>-Captura 60 FPS")]
        LiDAR["Sensor LiDAR<br>-Profundidad"]
        Compress["Compresión JPEG<br>q=0.5"]
        TCPSender["TCP <br>"]
  end
 subgraph InputLayer["Capa de Entrada"]
        TCPRec["TCP Receptor"]
        ImgRecon["Reconstrucción de Imagen"]
  end
 subgraph AICore["Motor de IA & Visión"]
        YOLO["YOLOv11l-seg<br>(CoreML / MPS)"]
        Tracker["Tracking<br>(BoT-SORT)"]
        DepthLogic["Fusión de Profundidad"]
  end
 subgraph LogicLayer["Lógica de Negocio"]
        Dedup["Deduplicación Espacial<br>(Haversine &lt; 5m)"]
        Alerts["Generador de Alertas"]
  end
 subgraph GUI["Capa de Presentación"]
        QtUI["Interfaz PySide6"]
        Map["Mapa Geoespacial"]
  end
 subgraph Server[" Nodo de Procesamiento (Server: M4 Pro)"]
    direction TB
        InputLayer
        AICore
        LogicLayer
        GUI
  end
 subgraph Storage["Persistencia"]
        MongoDB[("MongoDB<br>(GeoJSON Data)")]
        LocalDisk[("/captures<br>Evidencia JPG")]
  end
    TCPSender == TCP / USB (Puerto 8080)<br>Video + Depth Bytes ==> TCPRec
    TCPRec --> ImgRecon
    ImgRecon --> YOLO
    YOLO -- Máscaras + BBox --> Tracker
    Tracker -- ID Objetos --> DepthLogic
    DepthLogic -- Datos Métricos --> Dedup
    Dedup -- Nuevo Bache Detectado --> Alerts
    Dedup -- Es Duplicado --> LogicLayer
    Alerts --> MongoDB & LocalDisk
    YOLO -.-> QtUI
    Dedup -.-> Map

     ARKit:::tech
     ARKit:::edgeNode
     LiDAR:::tech
     LiDAR:::edgeNode
     Compress:::edgeNode
     TCPSender:::edgeNode
     TCPRec:::serverNode
     ImgRecon:::serverNode
     YOLO:::serverNode
     Tracker:::serverNode
     DepthLogic:::serverNode
     Dedup:::serverNode
     Alerts:::serverNode
     QtUI:::serverNode
     Map:::serverNode
     MongoDB:::dbNode
     LocalDisk:::dbNode
    classDef edgeNode fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef serverNode fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef dbNode fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 5 5
    classDef tech fill:#fff,stroke:#666,stroke-width:1px,stroke-dasharray: 2 2