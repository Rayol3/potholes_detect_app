DARK_THEME = """
QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}

QLabel {
    color: #e0e0e0;
}

QPushButton {
    background-color: #3e3e42;
    border: 1px solid #555555;
    border-radius: 5px;
    padding: 8px 16px;
    color: white;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #505050;
    border-color: #007acc;
}

QPushButton:pressed {
    background-color: #007acc;
    border-color: #005a9e;
}

QComboBox {
    background-color: #333333;
    border: 1px solid #555555;
    border-radius: 5px;
    padding: 5px;
    color: white;
}

QComboBox::drop-down {
    border: 0px;
}

QGroupBox {
    border: 1px solid #555555;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 5px;
    color: #007acc;
}
"""
