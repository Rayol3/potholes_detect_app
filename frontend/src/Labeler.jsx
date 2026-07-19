import { useState, useEffect, useRef } from 'react';
import { Save, Image as ImageIcon, Trash2, MousePointer2 } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

export default function Labeler() {
  const [images, setImages] = useState([]);
  const [currentImage, setCurrentImage] = useState('');
  const [boxes, setBoxes] = useState([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentBox, setCurrentBox] = useState(null);
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 });
  
  const canvasRef = useRef(null);
  const imgRef = useRef(null);

  useEffect(() => {
    fetchImages();
  }, []);

  useEffect(() => {
    if (currentImage) {
      setBoxes([]); // Clear boxes on new image
      redrawCanvas();
    }
  }, [currentImage]);

  useEffect(() => {
    redrawCanvas();
  }, [boxes, currentBox]);

  const fetchImages = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/labeler/images`);
      const data = await res.json();
      setImages(data.images);
      if (data.images.length > 0 && !currentImage) {
        setCurrentImage(data.images[0]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleImageLoad = (e) => {
    setImgSize({ w: e.target.naturalWidth, h: e.target.naturalHeight });
    redrawCanvas();
  };

  const redrawCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas || !imgRef.current) return;
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw committed boxes
    ctx.strokeStyle = '#22c55e'; // success color
    ctx.lineWidth = 2;
    boxes.forEach(b => {
      ctx.strokeRect(b.x, b.y, b.w, b.h);
      ctx.fillStyle = 'rgba(34, 197, 94, 0.2)';
      ctx.fillRect(b.x, b.y, b.w, b.h);
    });

    // Draw current box
    if (currentBox) {
      ctx.strokeStyle = '#3b82f6'; // accent color
      ctx.strokeRect(currentBox.x, currentBox.y, currentBox.w, currentBox.h);
      ctx.fillStyle = 'rgba(59, 130, 246, 0.2)';
      ctx.fillRect(currentBox.x, currentBox.y, currentBox.w, currentBox.h);
    }
  };

  // Mouse Events for drawing
  const getMousePos = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const scaleX = canvasRef.current.width / rect.width;
    const scaleY = canvasRef.current.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  };

  const handleMouseDown = (e) => {
    if (!currentImage) return;
    setIsDrawing(true);
    const pos = getMousePos(e);
    setStartPos(pos);
    setCurrentBox({ x: pos.x, y: pos.y, w: 0, h: 0 });
  };

  const handleMouseMove = (e) => {
    if (!isDrawing) return;
    const pos = getMousePos(e);
    setCurrentBox({
      x: Math.min(startPos.x, pos.x),
      y: Math.min(startPos.y, pos.y),
      w: Math.abs(pos.x - startPos.x),
      h: Math.abs(pos.y - startPos.y)
    });
  };

  const handleMouseUp = () => {
    if (isDrawing && currentBox && currentBox.w > 10 && currentBox.h > 10) {
      setBoxes([...boxes, currentBox]);
    }
    setIsDrawing(false);
    setCurrentBox(null);
  };

  const deleteLastBox = () => {
    setBoxes(boxes.slice(0, -1));
  };

  const saveAnnotation = async () => {
    if (!currentImage || boxes.length === 0) return;

    // Convert to YOLO format
    // YOLO format: class x_center y_center width height (normalized 0-1)
    let yoloText = '';
    const cw = canvasRef.current.width;
    const ch = canvasRef.current.height;

    boxes.forEach(b => {
      const x_c = (b.x + b.w / 2) / cw;
      const y_c = (b.y + b.h / 2) / ch;
      const w_n = b.w / cw;
      const h_n = b.h / ch;
      yoloText += `0 ${x_c.toFixed(6)} ${y_c.toFixed(6)} ${w_n.toFixed(6)} ${h_n.toFixed(6)}\n`;
    });

    try {
      const res = await fetch(`${API_BASE}/api/labeler/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: currentImage,
          content: yoloText
        })
      });
      if (res.ok) {
        alert('Annotation Saved Successfully!');
      }
    } catch (err) {
      console.error(err);
      alert('Error saving annotation');
    }
  };

  return (
    <div className="labeler-container">
      {/* Sidebar Gallery */}
      <div className="glass-panel gallery-sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <ImageIcon size={18} />
          <h3 style={{ fontSize: '16px' }}>Images</h3>
        </div>
        
        {images.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '14px', textAlign: 'center' }}>
            No images in captures/ folder
          </div>
        ) : (
          images.map(img => (
            <div 
              key={img} 
              className={`gallery-item ${currentImage === img ? 'active' : ''}`}
              onClick={() => setCurrentImage(img)}
            >
              {img}
            </div>
          ))
        )}
      </div>

      {/* Main Canvas Area */}
      <div className="canvas-area glass-panel" style={{ padding: 0, display: 'flex', flexDirection: 'column' }}>
        
        {/* Toolbar */}
        <div className="labeler-toolbar">
          <button className="btn" style={{ background: 'rgba(255,255,255,0.1)', padding: '8px 16px' }}>
            <MousePointer2 size={16} /> Draw Box
          </button>
          <div style={{ flex: 1 }}></div>
          <button className="btn" style={{ background: 'var(--danger)', padding: '8px 16px' }} onClick={deleteLastBox} disabled={boxes.length === 0}>
            <Trash2 size={16} /> Undo Last
          </button>
          <button className="btn btn-primary" style={{ padding: '8px 16px' }} onClick={saveAnnotation} disabled={boxes.length === 0}>
            <Save size={16} /> Save YOLO
          </button>
        </div>

        {/* Canvas */}
        <div className="canvas-container" style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', overflow: 'hidden' }}>
          {currentImage ? (
            <div style={{ position: 'relative' }}>
              <img 
                ref={imgRef}
                src={`${API_BASE}/api/labeler/image/${currentImage}`} 
                alt="Current" 
                style={{ maxWidth: '100%', maxHeight: '600px', display: 'block' }}
                onLoad={handleImageLoad}
                crossOrigin="anonymous"
              />
              <canvas
                ref={canvasRef}
                className="annotation-canvas"
                width={imgRef.current?.width || 800}
                height={imgRef.current?.height || 600}
                style={{ 
                  width: imgRef.current?.width, 
                  height: imgRef.current?.height 
                }}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              />
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)' }}>Select an image to start labeling</div>
          )}
        </div>
        
      </div>
    </div>
  );
}
