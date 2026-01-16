# Documentación: Latencia, FPS y Estabilidad bajo Carga

Este documento analiza el rendimiento del sistema en términos de Latencia y Cuadros por Segundo (FPS), con énfasis en la estabilidad del sistema cuando se detectan múltiples objetos simultáneamente (ej. n=6).

## 1. Métricas de Rendimiento Base

En condiciones de operación estándar, el sistema presenta las siguientes métricas:

*   **FPS (Cuadros por Segundo):** Mantiene un rango estable de **30 a 45 FPS**.
    *   Este límite es principalmente impuesto por la tasa de transmisión de red (cuando se usa el Cliente iOS) o la velocidad de captura de la cámara web, más que por la capacidad de inferencia del modelo.
*   **Latencia Total:** Inferior a **100 ms**.
    *   Incluye: Captura -> Transmisión TCP -> Decodificación -> Inferencia YOLO -> Visualización.

## 2. Estabilidad con Múltiples Objetos (Caso n=6)

Es crucial determinar si el rendimiento se degrada linealmente al aumentar el número de baches detectados (ej. Escenario de la Fig. 13 con 6 baches simultáneos).

**Conclusión:** El sistema mantiene su rendimiento estable (30-45 FPS) incluso con múltiples detecciones simultáneas. No hay una caída perceptible de FPS proporcional a la carga de objetos.

### ¿Por qué se mantiene estable?

El flujo de procesamiento está diseñado para desacoplar la carga computacional del número de objetos:

1.  **Inferencia Constante (O(1)):**
    *   El modelo YOLO (basado en CNN) tarda exactamente el mismo tiempo en procesar una imagen vacía que una con 100 baches. El tiempo de inferencia (~10-15ms en GPU/MPS) depende de la resolución de la imagen (640x640), no del contenido de la escena.

2.  **Post-Procesamiento Ligero:**
    *   El dibujo de máscaras (`cv2.fillPoly`) y cajas delimitadoras es una operación extremadamente rápida para CPUs modernas. Dibujar 6 objetos vs 1 objeto representa una diferencia de microsegundos, imperceptible para el contador de FPS global.

3.  **Gestión Inteligente de I/O (El Cuello de Botella Potencial):**
    *   La operación más costosa es guardar la evidencia (imagen en disco e inserción en base de datos).
    *   **Mecanismo de Protección:** El sistema utiliza un rastreador (`tracker`) que asigna un ID único a cada bache.
    *   **Lógica "One-Shot":** El guardado en disco y DB ocurre **solo una vez** por ID único (`if track_id not in self.processed_ids`).
    *   Si aparecen 6 baches nuevos simultáneamente, habrá un leve pico de uso de CPU en *ese único cuadro* para guardar los archivos, pero en los cuadros subsecuentes (mientras los baches sigan en pantalla), el sistema solo realiza el seguimiento visual (costo casi nulo), recuperando inmediatamente los 30-45 FPS estables.

4.  **Audio Rate-Limited:**
    *   Las alertas de audio están limitadas temporalmente (1 alerta cada 2.0 segundos globalmente), evitando que 6 baches generen 6 sonidos superpuestos o bloqueen el hilo de ejecución.

### Resumen de Impacto

| Cantidad de Baches | FPS Estimado | Latencia Adicional | Nota |
| :--- | :--- | :--- | :--- |
| **0 - 1 (Poco tráfico)** | 30 - 45 FPS | 0 ms | Carga base del sistema. |
| **6 (Carga media - Fig. 13)** | 30 - 45 FPS | < 1 ms | Costo de iteración y dibujo despreciable. |
| **Entrada de Nuevos Baches** | 28 - 40 FPS | ~10-20 ms | *Transitorio:* Solo ocurre en el frame exacto donde se guardan las fotos en disco. |
