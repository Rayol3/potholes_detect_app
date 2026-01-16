# Documentación Técnica: Conversión de Modelo a CoreML (.mlpackage)

## 1. Introducción
Este documento detalla el procedimiento técnico utilizado para convertir el modelo entrenado **YOLOv11** (formato nativo PyTorch `.pt`) al formato **CoreML** (`.mlpackage`), permitiendo su ejecución nativa y acelerada en dispositivos Apple (iPhone/iPad) utilizando el **Apple Neural Engine (ANE)**.

El archivo resultante (`.mlpackage`) es un directorio que contiene los metadatos, la arquitectura de la red y los pesos optimizados.

## 2. Herramienta de Conversión
Se utilizó el script propietario `convert_coreml.py`, el cual actúa como wrapper sobre la librería `ultralytics`.

### Código Fuente Utilizado:
```python
from ultralytics import YOLO

# Cargar el modelo entrenado
model = YOLO('best.pt')  # Se asume que best.pt es el mejor checkpoint

# Exportar a formato CoreML
model.export(
    format='coreml', 
    nms=False       # No integra NMS (Detección raw o Segmentación)
)
```

## 3. Parámetros Críticos de Exportación

### A. Sin NMS Integrado (`nms=False`)
*   **Configuración Actual:** El script utiliza `nms=False`.
*   **Implicaciones:**
    *   El modelo exportado retorna los **tensores crudos** (Raw Tensors) de las predicciones en lugar de cajas delimitadoras finales.
    *   **Post-procesamiento:** La aplicación iOS (o el cliente que consuma el modelo) debe encargarse de decodificar estos tensores y aplicar el algoritmo de **Non-Maximum Suppression (NMS)** manualmente para filtrar detecciones duplicadas.
    *   **Motivación:** En modelos de **Segmentación** (como YOLOv11-seg), la salida es más compleja (máscaras + cajas), y los exportadores estándar a veces tienen dificultades para encapsular toda esa lógica eficientemente dentro de una capa CoreML estándar. Desacoplar el NMS ofrece mayor control en el cliente.

### B. Precisión (Default)
*   **Configuración:** No se especificó `half=True` explícitamente en el script.
*   **Impacto:** El modelo se exporta con la precisión por defecto de la librería Ultralytics (generalmente FP32 o FP16 dependiendo del hardware de exportación, pero sin forzarlo).

## 4. Estructura del `.mlpackage`
Al inspeccionar el paquete generado (ej. `best.mlpackage`), se encuentra la siguiente estructura interna (standard Apple CoreML):

1.  **`Manifest.json`**: Metadatos generales (autor, licencia, versión).
2.  **`Data/`**: Contiene los pesos binarios cuantizados (FP16).
3.  **`Model.mlmodel`**: Define el grafo computacional (capas, entradas, salidas).

### Entradas y Salidas del Modelo Final
*   **Input:** Imagen de color (`Color 640x640`). CoreML maneja automáticamente la normalización de píxeles [0, 255] -> [0, 1].
*   **Outputs (`nms=False`):**
    *   Retorna un **MultiArray** (Tensor) multidimensional.
    *   Dimensiones típicas: `[1, 84 + num_masks, 8400]`.
    *   Requiere decodificación customizada en el cliente (Swift).

## 5. Integración en Xcode
Para usar este modelo en la aplicación `EdgeSensor`:
1.  Arrastrar el archivo `.mlpackage` al proyecto de Xcode.
2.  Xcode generará automáticamente una clase Swift (ej. `yolov11m`).
3.  Instanciar el modelo con configuración de hardware (CPU/GPU/ANE):
    ```swift
    let config = MLModelConfiguration()
    config.computeUnits = .all // Usa Neural Engine si está disponible
    let model = try yolov11m(configuration: config)
    ```

## 6. Verificación
El éxito de la conversión se verifica observando la consola de salida durante el script:
*   `CoreML export success`
*   `Optimizing for Neural Engine...`
*   Generación final del archivo `.mlpackage`.
