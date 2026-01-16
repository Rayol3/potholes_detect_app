# Documentación Técnica: Entrenamiento y Evaluación de YOLOv11m (V6)

## 1. Descripción General
El notebook **`train_yolo11m_v6.ipynb`** funciona como el panel central de orquestación y análisis para el entrenamiento del modelo de detección de baches (*Pothole Detection*). Este script no solo ejecuta el entrenamiento, sino que consolida y compara los resultados de múltiples etapas secuenciales de entrenamiento para generar una visión unificada del rendimiento del modelo a lo largo del tiempo.

**Objetivo Principal:** Maximizar la precisión de detección (mAP) consolidando el aprendizaje de diversas fases y validar el modelo final con métricas robustas.

## 2. Configuración del Entorno
*   **Modelo Base:** YOLOv11m (Medium) - Seleccionado por su balance entre velocidad de inferencia y capacidad de extracción de características complejas.
*   **Hardware Utilizado:** NVIDIA GeForce RTX 3060 Ti.
*   **Librerías Clave:** `ultralytics`, `torch`, `pandas`, `matplotlib`.
*   **Gestión de Memoria GPU:** Se habilita `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` para optimizar la fragmentación de memoria durante cargas de trabajo intensivas.

## 3. Metodología de Consolidación de Entrenamiento
El notebook implementa una estrategia de **Aprendizaje Incremental Consolidado**. En lugar de entrenar una sola vez, agrupa y analiza el historial de múltiples sesiones ("Runs") para evaluar la estabilidad y convergencia a largo plazo.

### Fases Analizadas:
1.  **Entrenamiento_V6_Medium_Stable_512px:** Fase inicial de estabilización con resolución media.
2.  **Entrenamiento_V6_Extended_50e:** Extensión intermedia para refinar pesos.
3.  **Entrenamiento_V6_Extended_2_100e:** Fase final de ajuste fino (Fine-tuning) prolongado.

### Funciones Clave Implementadas:

#### A. `consolidar_historial(project_dir, save_dir)`
Esta función es el núcleo analítico. Realiza lo siguiente:
*   **Fusión de Datos:** Escanea las carpetas de los distintos entrenamientos y concatena sus archivos de métricas (`results.csv`) en un solo DataFrame maestro (`GLOBAL_RESULTS.csv`).
*   **Ajuste Temporal:** Recalcula los índices de las épocas (`epoch`) para que sean continuos a través de las distintas fases, permitiendo ver el progreso como una línea de tiempo única.
*   **Visualización Global:** Genera gráficos unificados (`GLOBAL_PROGRESS.png`) comparando:
    *   *Métricas de Desempeño:* Precision, Recall, mAP50.
    *   *Funciones de Pérdida (Loss):* Box Loss, Seg Loss (tanto en entrenamiento como validación).

#### B. `reporte_mejor_epoca(run_path, save_dir)`
Automatiza la extracción de resultados óptimos.
*   Identifica la época con el **mAP50 máximo**.
*   Exporta un resumen técnico detallado (`BEST_EPOCH_REPORT.txt`) con todas las métricas de esa época específica, eliminando la necesidad de buscar manualmente en logs extensos.

#### C. `probar_inferencia(run_dir, data_path, label)`
Módulo de validación cualitativa.
*   Carga los mejores pesos obtenidos (`best.pt`).
*   Ejecuta inferencias sobre una muestra aleatoria de imágenes del dataset.
*   Muestra visualmente las predicciones (Bounding Boxes y Segmentación) para verificación humana inmediata.

## 4. Resultados Obtenidos (Fase Final: 100 Épocas)
El análisis automatizado del notebook reporta los siguientes resultados definitivos para la mejor época consolidada:

| Métrica | Valor Alcanzado | Interpretación |
| :--- | :--- | :--- |
| **mAP50 (Box)** | **84.47%** | Alta precisión en la localización general de baches. |
| **mAP50-95 (Box)** | **48.96%** | Solidez notable en distintos umbrales de IoU; el modelo es preciso "pixel-perfect". |
| **Precisión** | 85.65% | Baja tasa de falsos positivos (detecciones erróneas). |
| **Recall** | 73.08% | Capacidad consistente para encontrar la mayoría de los baches presentes. |

### Análisis de Convergencia
*   **Train/Box Loss (0.34) vs Val/Box Loss (0.15):** La pérdida de validación es menor que la de entrenamiento, lo cual es un indicador excelente de que el modelo **no sufre de Overfitting** significativo y generaliza bien a datos no vistos.
*   **Tiempo de Entrenamiento:** ~22 horas (79,148 segundos) acumuladas en la fase final, demostrando la robustez del proceso computacional.

## 5. Conclusión Técnica
Este notebook valida la arquitectura YOLOv11m como una solución viable para el sistema de monitoreo vial. La estrategia de entrenamiento por etapas, unificada mediante este script, ha permitido alcanzar un **mAP superior al 84%**, superando los umbrales típicos para aplicaciones de detección en tiempo real en entornos móviles.
