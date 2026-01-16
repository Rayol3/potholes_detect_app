# 🛣️ Intelligent Pothole Detection System (Edge-Fog)

> **Sistema de Detección y Georreferenciación de Baches en Tiempo Real mediante Visión Artificial y LiDAR.**

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![YOLO](https://img.shields.io/badge/YOLO-v11l--seg-green)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20iOS-lightgrey)
![Hardware](https://img.shields.io/badge/Hardware-Apple%20Silicon%20(M4)-orange)

## 📖 Descripción General

Este proyecto implementa una arquitectura híbrida **Edge-Fog** para la detección automatizada de daños en el pavimento. Combina la agilidad de dispositivos móviles (Edge) con la potencia de estaciones base (Fog/Server) para lograr una auditoría vial precisa y eficiente.

El sistema permite capturar, detectar, medir y georreferenciar baches a **60 FPS** utilizando fusión de sensores (Cámara RGB + LiDAR).

## 🚀 Características Clave

*   **Arquitectura Híbrida:** Cliente iOS (Swift/ARKit) para sensado remoto y Servidor Python para procesamiento pesado.
*   **IA de Última Generación:** Modelo **YOLOv11l-seg** (Segmentación de Instancias) optimizado.
*   **Aceleración por Hardware:** Inferencia nativa mediante **Core ML** y **Metal Performance Shaders (MPS)**, aprovechando al 100% la NPU/GPU del chip Apple M4.
*   **Fusión de Sensores:** Estimación de profundidad y severidad del bache mediante **LiDAR** (iPhone Pro).
*   **Deduplicación Espacial:** Algoritmo geoespacial (Haversine + MongoDB) para evitar duplicados en un radio de 5 metros.
*   **Reportes Automatizados:** Generación automática de órdenes de trabajo en PDF con mapas de calor y evidencia fotográfica.

## 🛠️ Stack Tecnológico

*   **Core AI:** Ultralytics YOLOv11 (PyTorch / CoreML)
*   **Backend:** Python 3.11, OpenCV, NumPy, MongoDB (GeoJSON)
*   **Frontend Desktop:** PySide6 (Qt)
*   **Edge Client (iOS):** Swift, ARKit, Network framework (TCP Socket)
*   **Communication:** Custom Length-Prefixed TCP Protocol

---
## 📄 Documentación Adicional

*   [Arquitectura del Sistema (Detallada)](documentation_system_architecture_detailed.md)
*   [Arquitectura Modelo YOLOv11](documentation_model_architecture.md)
*   [Protocolo TCP/IP](documentation_tcp_protocol.md)
*   [Latencia y Estabilidad](documentation_latency_stability.md)
*   [Deduplicación Espacial](documentation_spatial_deduplication.md)
