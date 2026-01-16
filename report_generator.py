from fpdf import FPDF
from datetime import datetime
import os

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Deteccion de Baches - Orden de Trabajo', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_report(potholes, output_filename="Orden_Trabajo.pdf", map_image_path=None):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Summary
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1)
    pdf.cell(0, 10, f"Total Detecciones: {len(potholes)}", 0, 1)
    
    # Map Snapshot
    if map_image_path and os.path.exists(map_image_path):
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Mapa de Calor - Vista General", 0, 1)
        # Assuming A4 width ~210mm, margins ~10mm each side -> 190mm usable
        pdf.image(map_image_path, x=10, w=190) 
        pdf.ln(5)

    pdf.ln(10)
    
    # Header for Table
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(10, 10, "#", 1, 0, 'C')
    pdf.cell(25, 10, "Hora", 1, 0, 'C')
    pdf.cell(35, 10, "Ubicacion", 1, 0, 'C')
    pdf.cell(15, 10, "Conf.", 1, 0, 'C')
    pdf.cell(20, 10, "Tam.(m)", 1, 0, 'C') # New Column
    pdf.cell(40, 10, "Foto", 1, 0, 'C')
    pdf.cell(35, 10, "Tipo", 1, 1, 'C') 
    
    pdf.set_font("Arial", size=9)
    
    for i, p in enumerate(potholes):
        # p is (lat, lon, conf, timestamp, image_path) or similar tuple from DB
        
        timestamp_str = p['timestamp'].strftime('%H:%M:%S')
        loc_str = f"{p['lat']:.5f}, {p['lon']:.5f}"
        conf_str = f"{p['confidence']:.2f}"
        size_str = f"{p.get('size_m', 0.0):.2f} m" if p.get('size_m') else "-"
        img_path = p.get('image_path')
        
        # Row Layout
        # We need height for the image
        row_height = 25 
        
        # Check page break
        if pdf.get_y() > 250:
            pdf.add_page()
            
        x = pdf.get_x()
        y = pdf.get_y()
        
        pdf.cell(10, row_height, str(i+1), 1, 0, 'C')
        pdf.cell(25, row_height, timestamp_str, 1, 0, 'C')
        pdf.cell(35, row_height, loc_str, 1, 0, 'C')
        pdf.cell(15, row_height, conf_str, 1, 0, 'C')
        pdf.cell(20, row_height, size_str, 1, 0, 'C')
        
        # Image Cell
        pdf.cell(40, row_height, "", 1, 0, 'C') # Placeholder for border
        if img_path and os.path.exists(img_path):
             # Draw image inside the cell we just made
             # x position is x + 10+25+35+15+20 = x+105
             pdf.image(img_path, x=x+110, y=y+2, w=30, h=20)
        else:
             pdf.text(x+110, y+15, "Sin Foto")

        # Type (Manual vs AI)
        p_type = p.get('type', 'Deteccion IA')
        if p.get('confidence', 0) == 1.0:
            p_type = "Manual"
            
        pdf.cell(35, row_height, p_type, 1, 1, 'C')

    pdf.output(output_filename)
    print(f"Reporte generado: {output_filename}")
