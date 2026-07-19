# Documentación de Pruebas de Rendimiento (FPS)

Este documento registra las métricas de rendimiento del sistema de detección de baches (Edge Sensing System) utilizando el cliente iOS con LiDAR y el servidor de procesamiento en Python.

## Configuración de la Prueba

*   **Dispositivo Cliente:** iPhone (Especificar modelo, e.g., iPhone 13 Pro, 14 Pro)
*   **iOS Versión:** (Especificar)
*   **Servidor:** (Especificar Hardware, e.g., MacBook Pro M1/M2/M3, RAM)
*   **Red:** (e.g., WiFi 5GHz, Local, Cableado)
*   **Resolución enviada:** (Si aplica)

## Metodología

Para medir los FPS, utilizaremos el script `edge_sensing_system/server/benchmark_fps.py` en tres modos distintos para aislar cuellos de botella:

1.  **Network Only (`--mode network_only`):** Mide cuántos paquetes por segundo llegan al servidor. Evalúa puramente la red y la capacidad de envío del iPhone.
2.  **Decode Only (`--mode decode_only`):** Mide paquetes recibidos + descompresión de imagen JPEG (OpenCV). Evalúa el costo de la decodificación.
3.  **Full System (`--mode full`):** Mide el pipeline completo: Recepción + Decodificación + Inferencia YOLOv11 + Post-procesamiento. Este es el FPS real del sistema.

## Resultados

| Fecha | Modo de Prueba (`--mode`) | FPS Promedio | Ancho de Banda (MB/s) | Notas / Observaciones |
| :--- | :--- | :--- | :--- | :--- |
| YYYY-MM-DD | `network_only` | | | Prueba de throughput puro. |
| YYYY-MM-DD | `decode_only` | | | Prueba de CPU (Descompresión img). |
| YYYY-MM-DD | `full` | | | Rendimiento real con IA activada. |

## Análisis de Resultados

*(Aquí puedes escribir tus conclusiones. Por ejemplo: "El cuello de botella es la inferencia de la IA, ya que la red soporta 60 FPS pero el análisis baja a 15 FPS", o "La red es inestable".)*

## Instrucciones para ejecutar las pruebas

1.  Asegúrate de que el iPhone y el servidor estén en la misma red.
2.  En el servidor (Mac), ejecuta el script de benchmark:

    ```bash
    # Para probar solo RED
    python3 edge_sensing_system/server/benchmark_fps.py --mode network_only
    
    # Para probar RED + DECODIFICACIÓN
    python3 edge_sensing_system/server/benchmark_fps.py --mode decode_only
    
    # Para probar SISTEMA COMPLETO (IA)
    python3 edge_sensing_system/server/benchmark_fps.py --mode full
    ```
3.  En el iPhone, abre la app `EdgeSensor` y apunta la cámara (asegúrate de que esté enviando datos).
4.  Observa la terminal por ~30 segundos y anota el FPS promedio estable.

## Registro de Ejecución Exitosa (2026-01-18)

**Configuración:**
* **Modo:** Full System + Sensor Fusion (LiDAR, Accelerometer, YOLOv11L Segment, MiDaS Depth)
* **IP Servidor:** 192.168.1.76

**Métricas Observadas:**
Durante la ejecución en tiempo real, se observaron los siguientes valores de FPS en el momento de detección de baches:

| Evento | Confianza | Distancia/Tamaño | FPS |
| :--- | :--- | :--- | :--- |
| Detección #1 | 0.84 | 1.41m | **13.8** |
| Detección #24 | 0.37 | 0.39m | **19.5** |
| Detección #30 | 0.32 | 1.85m | **23.2** |
| Detección #38 | 0.36 | 0.3m | **20.3** |
| Detección #255 | 0.47 | 0.62m | **27.1** |
| Detección #302 | 0.49 | 0.78m | **26.3** |
| Detección #339 | 0.40 | 0.47m | **27.2** |

**Resumen:**
* **FPS Mínimo:** ~11.2 FPS
* **FPS Máximo:** ~28.1 FPS
* **FPS Promedio (Estadístico):** ~20-22 FPS

**Conclusión:**
El sistema es estable y opera en tiempo real. La integración del clientes iOS enviando datos crudos permite que el servidor Mac procese modelos pesados (YOLOv11L) manteniendo una tasa de cuadros fluida (promedio >20 FPS), lo cual es suficiente para la detección vehicular a velocidades moderadas. La latencia de red no parece ser un cuello de botella significativo.
