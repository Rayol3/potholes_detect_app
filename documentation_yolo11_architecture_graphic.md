# Arquitectura YOLO11 (Guía para Gráficos)

Este documento estructura la arquitectura del modelo **YOLOv11l-seg** específicamente para facilitar la creación de diagramas o gráficos técnicos.

## 1. Input (Entrada)

*   **Bloque:** `Input Layer`
*   **Datos:** `Imagen RGB`
*   **Dimensión:** `640 x 640 x 3`
    *   **H (Alto):** 640
    *   **W (Ancho):** 640
    *   **C (Canales):** 3 (Red, Green, Blue)

---

## 2. Backbone (Columna Vertebral)

Funciona como extractor de características. Reduce la resolución espacial de la imagen mientras aumenta la profundidad (canales) para capturar conceptos abstractos.

**Flujo Secuencial (Bloques Principales):**

| Bloque | Nombre/Tipo | Salida (Canales) | Descripción en Gráfico |
| :--- | :--- | :--- | :--- |
| **B1** | `Conv (Stem)` | 64 | Inicio de la red. Downsampling inicial. |
| **B2** | `C3k2` | 256 | Extracción temprana de texturas/bordes. |
| **B3** | `C3k2` | 512 | Características de nivel medio. **(Salida hacia Neck: P3)** |
| **B4** | `C3k2` | 512 | Características complejas. **(Salida hacia Neck: P4)** |
| **B5** | `C3k2 + SPPF` | 512 | Bloque profundo + Pooling Piramidal. |
| **B6** | `C2PSA` | 512 | Atención Espacial. **(Salida Final Backbone: P5)** |

---

## 3. Neck (Cuello)

Encargado de mezclar las características de diferentes tamaños (P3, P4, P5) para detectar objetos pequeños, medianos y grandes. Utiliza una arquitectura **PANet** (Path Aggregation Network).

**Conexiones Clave para el Gráfico:**

1.  **Ruta de Subida (Upsample):**
    *   El **P5** (del Backbone) sube de resolución y se mezcla con **P4**.
    *   El resultado sube nuevamente y se mezcla con **P3** (Alta resolución).

2.  **Ruta de Bajada (Downsample):**
    *   La mezcla de alta resolución (**P3**) baja para volver a enriquecer a **P4**.
    *   La mezcla media (**P4**) baja para enriquecer a **P5**.

**Salidas del Neck hacia el Head:**
*   **Salida 1:** Mapa de características Alta Resolución (objetos pequeños).
*   **Salida 2:** Mapa de características Resolución Media (objetos medianos).
*   **Salida 3:** Mapa de características Baja Resolución (objetos grandes).

---

## 4. Head (Cabecera)

Es la parte final que realiza las predicciones. En YOLO11 es "Decoupled" (Desacoplada) para tareas de segmentación.

*   **Entradas:** Recibe las 3 salidas del Neck.
*   **Módulo:** `Segment Head`
*   **Salidas Finales (Outputs):**
    1.  **Bounding Boxes:** Coordenadas `(x, y, w, h)` para cada detección.
    2.  **Classes:** Probabilidad de clase (ej. "Bache").
    3.  **Masks (Protomasks):** Coeficientes para generar la forma exacta (polígono) del bache.

---

## 5. Referencia Visual (Ejemplo Mermaid)

```mermaid
graph TD
    %% Estilos
    classDef input fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef backbone fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef neck fill:#fff3e0,stroke:#ef6c00,stroke-width:2px;
    classDef head fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;

    %% Nodos
    I[Input Image<br>640x640x3 RGB]:::input

    subgraph BACKBONE [Extracción de Características]
        direction TB
        B_Stem[Conv Stem]:::backbone
        B_Low[C3k2 Block]:::backbone
        B_Mid[C3k2 Block<br>(Out: P3)]:::backbone
        B_High[C3k2 Block<br>(Out: P4)]:::backbone
        B_Deep[C3k2 + SPPF]:::backbone
        B_Final[C2PSA Attention<br>(Out: P5)]:::backbone
    end

    subgraph NECK [Fusión de Escalas - PANet]
        direction TB
        N_Up[Fusión Ascendente<br>(Upsample + Concat)]:::neck
        N_Down[Fusión Descendente<br>(Conv + Concat)]:::neck
    end

    subgraph HEAD [Predicción]
        H_Seg[Segment Head]:::head
        O_Box[Bounding Boxes]:::head
        O_Mask[Instance Masks]:::head
    end

    %% Conexiones
    I --> B_Stem
    B_Stem --> B_Low
    B_Low --> B_Mid
    B_Mid --> B_High
    B_High --> B_Deep
    B_Deep --> B_Final

    %% Conexiones Backbone -> Neck
    B_Mid --> N_Down
    B_High -.-> N_Up
    B_High -.-> N_Down
    B_Final --> N_Up

    %% Conexiones Internas Neck
    N_Up --> N_Down

    %% Conexiones Neck -> Head
    N_Down --> H_Seg

    %% Salidas
    H_Seg --> O_Box
    H_Seg --> O_Mask
```
