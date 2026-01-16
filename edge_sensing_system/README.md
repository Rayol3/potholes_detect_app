# Edge Sensing System: iPhone LiDAR + Mac YOLO
This system establishes a high-performance link between an iPhone (Edge Sensor) and a Mac (Processing Server) using TCP over USB/WiFi.

## Directory Structure
- `server/`: Python code to run on your Mac.
- `client_ios_src/`: Swift reference code to copy into your Xcode project.

## 1. Setup Python Server (Mac)
1.  **Install Dependencies**:
    ```bash
    pip install ultralytics opencv-python numpy
    ```
    (Ensure you are in your virtual environment)

2.  **Run Server**:
    ```bash
    python edge_sensing_system/server/main.py
    ```
    The server will start listening on port 8080.

## 2. Setup iOS App (iPhone) - Paso a Paso

### A. Crear el Proyecto en Xcode
1.  Abre **Xcode** en tu Mac.
2.  En el menú superior, ve a **File > New > Project...**
3.  Selecciona la pestaña **iOS** y luego **App**. Haz clic en **Next**.
4.  Lena los datos:
    - **Product Name**: `EdgeSensor` (o lo que quieras).
    - **Interface**: Selecciona **Storyboard** (¡Importante! Mis códigos usan UIKit).
    - **Language**: **Swift**.
5.  Haz clic en **Next** y guárdalo en una carpeta.

### B. Copiar los Archivos
Ahora tienes un proyecto vacío. Vamos a meter los archivos que generé.

1.  **ViewController.swift**:
    - En Xcode (barra izquierda), haz clic en `ViewController.swift` (ya existe).
    - Borra todo su contenido.
    - Copia el contenido de mi archivo `edge_sensing_system/client_ios_src/ViewController.swift` y pégalo ahí.

2.  **NetworkManager.swift**:
    - En Xcode, haz clic derecho en la carpeta amarilla (grupo) de tu proyecto y elige **New File...**
    - Selecciona **Swift File** y dale a **Next**.
    - Nómbralo `NetworkManager` y créalo.
    - Pega dentro el contenido de `edge_sensing_system/client_ios_src/NetworkManager.swift`.

3.  **ARCameraManager.swift**:
    - Repite el paso anterior: Crea un **Swift File** llamado `ARCameraManager`.
    - Pega dentro el contenido de `edge_sensing_system/client_ios_src/ARCameraManager.swift`.

### C. Permiso de Cámara
1.  En Xcode, haz clic en el archivo azul del proyecto (el raíz en la izquierda).
2.  Ve a la pestaña **Info**.
3.  Busca una linea vacía en "Custom iOS Target Properties", dale al `+`.
4.  Busca la key: `Privacy - Camera Usage Description` (o `NSCameraUsageDescription`).
5.  **IMPORTANTE**: En la columna "Value" (a la derecha), debes escribir algo. **No lo dejes vacío**.
    - Escribe: "Necesitamos la cámara para ver la calle."

### F. Solución de Error: Deployment Target
Si te sale error de "Deployment Target":
1.  Haz clic en el icono azul del proyecto (arriba a la izquierda, raíz).
2.  Selecciona el **Target** (icono de app).
3.  Ve a la pestaña **General**.
4.  En **Minimum Deployments**, baja la versión a **iOS 16.0** (o la que tenga tu iPhone).
5.  Dale a Play de nuevo.

### G. Solución de Error: Signing (Firma)
Para instalar en un iPhone real, Apple necesita que "firmes" la app.
1.  Haz clic en el icono azul del proyecto (navecador izquierdo).
2.  Selecciona el **Target** (icono de App).
3.  Ve a la pestaña **Signing & Capabilities**.
4.  En "Team", abre el menú.
5.  Selecciona tu cuenta personal (ej. `Tu Nombre (Personal Team)`).
    - Si no aparece ninguna, haz clic en **Add an Account...** e inicia sesión con tu Apple ID.
6.  Asegúrate de que "Bundle Identifier" sea algo único (ej. `com.rayols.EdgeSensor`).

### D. Configurar IP
1.  Abre `ViewController.swift` en Xcode.
2.  Busca la línea `private let serverIP = "192.168.1.100"`.
3.  Cámbiala por la IP real de tu Mac (mira la sección "Connecting via USB").

### E. ¡IMPORTANTE! Usar iPhone Físico (No Simulador)
**ARKit y la Cámara NO funcionan en el Simulador de Xcode.**
Debes usar tu iPhone 14 real.

1.  Conecta tu iPhone 14 a la Mac con el cable.
2.  En la parte superior de Xcode, en el centro (al lado del botón Play), verás que dice algo como "iPhone 15 Pro (Simulator)".
3.  Haz clic ahí y selecciona tu **iPhone de Rayols** (o como se llame) que aparecerá arriba en la lista "iOS Devices".
4.  Si es la primera vez, el iPhone te pedirá "¿Confiar en esta computadora?". Di que **Sí**.
5.  Es posible que debas activar el **Modo Desarrollador** en el iPhone:
    - Ve a Ajustes -> Privacidad y Seguridad -> Modo Desarrollador -> Activar (el iPhone se reiniciará).
6.  Ahora dale al botón **Play**.

## 3. Connecting via USB (Recommended)
To avoid WiFi latency and jitter, use the USB cable:

1.  **Connect iPhone** to Mac via USB.
2.  **Important**: Turn off WiFi on the iPhone (Control Center).
3.  **Personal Hotspot**: Go to Settings -> Personal Hotspot -> Allow Others to Join (Enable "Maximize Compatibility" if needed, but usually not).
    - Even without a SIM card, this sometimes triggers the network interface.
    - *Alternative*: If Personal Hotspot is tricky, simply connecting via cable usually creates a virtual network interface on the Mac.
4.  **Find IP**:
    - Open Terminal on Mac.
    - Run `ifconfig`. Look for an interface like `bridge100` or similar that appears when you plug in the phone. It usually has an IP in the `172.20.10.x` range.
    - Use *that* IP address in your Swift code.

## 4. Run
1.  Start Python Server.
2.  Run App on iPhone.
3.  Point iPhone at objects.
4.  See YOLO detections on your Mac screen!

## Troubleshooting
- **Connection Refused**: Check the IP address and ensure firewall is not blocking port 8080.
- **Latency**: Ensure you are using the USB interface (check IPs) and not WiFi if the WiFi signal is weak.
