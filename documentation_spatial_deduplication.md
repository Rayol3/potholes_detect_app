# Documentación: Sistema de Deduplicación Espacial

Este documento detalla el mecanismo de deduplicación espacial implementado para evitar el conteo múltiple de un mismo bache detectado en cuadros consecutivos o en pasadas diferentes.

## Descripción General

El sistema utiliza una base de datos **MongoDB** para almacenar las coordenadas geoespaciales de cada bache detectado. Antes de registrar una nueva detección, se consulta la base de datos para verificar si ya existe un registro previo en las cercanías.

## Lógica de Deduplicación

La lógica principal reside en el método `is_duplicate` de la clase `Database` (archivo: `database.py`).

### 1. Consulta Geoespacial
El sistema recupera los puntos existentes (`lat`, `lon`) de la colección `detections`.

### 2. Cálculo de Distancia (Fórmula de Haversine)
Para cada punto existente, se calcula la distancia exacta con la nueva detección utilizando la fórmula de Haversine, que tiene en cuenta la curvatura de la tierra:

```python
def haversine_dist(lat1, lon1, lat2, lon2):
    R = 6371000 # Radio de la Tierra en metros
    # ... cálculo trigonométrico ...
    return R * c
```

### 3. Umbral de Distancia
Se define un radio de tolerancia (`radius_m`). Si la distancia calculada es menor a este umbral, se considera que la nueva detección corresponde al mismo objeto físico y se descarta (no se guarda en la base de datos).

*   **Umbral por Defecto (Clase Database):** `5.0` metros.
*   **Umbral en Detección en Tiempo Real:** En el hilo de detección (`detection_thread.py`), se ha configurado para utilizar un umbral más estricto de **`1.0` metro** (ver variable `radius_m`).

## Implementación

El flujo en `detection_thread.py` es el siguiente:

1.  Se obtiene la ubicación GPS actual.
2.  Se verifica si el ID del objeto (tracking) ya fue procesado.
3.  Si es un ID nuevo, se consulta `db.is_duplicate(lat, lon, radius_m=1.0)`.
4.  Si retorna `False` (no es duplicado), se inserta el nuevo registro.
5.  Si retorna `True`, se ignora.

> **Nota:** Actualmente, en el código de prueba, esta verificación puede estar deshabilitada (`if True:`) para propósitos de depuración en patio, pero la arquitectura está diseñada para operar con el umbral mencionado.


