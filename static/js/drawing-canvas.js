/**
 * Drawing Canvas Component
 * Touch-friendly drawing canvas for Y6 Practice Exam
 * Supports: Freehand drawing, Shapes (flowchart), Lines/Arrows
 */

class DrawingCanvas {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Container not found:', containerId);
            return;
        }

        // Configuration
        this.options = {
            width: options.width || 600,
            height: options.height || 400,
            backgroundColor: options.backgroundColor || '#ffffff',
            strokeColor: options.strokeColor || '#000000',
            strokeWidth: options.strokeWidth || 2,
            type: options.type || 'freehand', // freehand, flowchart, connect
            onSave: options.onSave || null,
            questionId: options.questionId || null,
            ...options
        };

        // State
        this.isDrawing = false;
        this.currentTool = 'pen';
        this.currentShape = null;
        this.history = [];
        this.redoStack = [];
        this.startX = 0;
        this.startY = 0;

        // Colors palette
        this.colors = ['#000000', '#FF0000', '#0000FF', '#008000', '#FFA500', '#800080'];

        this.init();
    }

    init() {
        this.createCanvas();
        this.createToolbar();
        this.attachEventListeners();
        this.saveState();
    }

    createCanvas() {
        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'drawing-wrapper';

        // Create canvas
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.options.width;
        this.canvas.height = this.options.height;
        this.canvas.className = 'drawing-canvas';
        this.ctx = this.canvas.getContext('2d');

        // Set initial background
        this.ctx.fillStyle = this.options.backgroundColor;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        wrapper.appendChild(this.canvas);
        this.container.appendChild(wrapper);
    }

    createToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'drawing-toolbar';

        // Tool buttons
        const tools = [
            { id: 'pen', icon: 'M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z', label: 'Pen' },
            { id: 'eraser', icon: 'M19 4H5a2 2 0 00-2 2v12a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2z', label: 'Eraser' },
            { id: 'line', icon: 'M2 12h20', label: 'Line' },
            { id: 'arrow', icon: 'M2 12h20M14 5l7 7-7 7', label: 'Arrow' },
            { id: 'rectangle', icon: 'M3 3h18v18H3z', label: 'Rectangle' },
            { id: 'diamond', icon: 'M12 2l10 10-10 10L2 12z', label: 'Diamond' },
            { id: 'oval', icon: 'M12 6a6 4 0 100 8 6 4 0 000-8z', label: 'Oval' },
        ];

        // Tools section
        const toolsSection = document.createElement('div');
        toolsSection.className = 'toolbar-section';

        tools.forEach(tool => {
            const btn = document.createElement('button');
            btn.className = `tool-btn ${tool.id === this.currentTool ? 'active' : ''}`;
            btn.dataset.tool = tool.id;
            btn.title = tool.label;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" fill="none" stroke-width="2">
                    <path d="${tool.icon}"/>
                </svg>
            `;
            btn.addEventListener('click', () => this.setTool(tool.id));
            toolsSection.appendChild(btn);
        });

        toolbar.appendChild(toolsSection);

        // Colors section
        const colorsSection = document.createElement('div');
        colorsSection.className = 'toolbar-section colors-section';

        this.colors.forEach(color => {
            const colorBtn = document.createElement('button');
            colorBtn.className = `color-btn ${color === this.options.strokeColor ? 'active' : ''}`;
            colorBtn.style.backgroundColor = color;
            colorBtn.dataset.color = color;
            colorBtn.addEventListener('click', () => this.setColor(color));
            colorsSection.appendChild(colorBtn);
        });

        toolbar.appendChild(colorsSection);

        // Stroke width
        const strokeSection = document.createElement('div');
        strokeSection.className = 'toolbar-section';

        const strokeLabel = document.createElement('span');
        strokeLabel.textContent = 'Size:';
        strokeLabel.className = 'stroke-label';

        const strokeSlider = document.createElement('input');
        strokeSlider.type = 'range';
        strokeSlider.min = '1';
        strokeSlider.max = '10';
        strokeSlider.value = this.options.strokeWidth;
        strokeSlider.className = 'stroke-slider';
        strokeSlider.addEventListener('input', (e) => {
            this.options.strokeWidth = parseInt(e.target.value);
        });

        strokeSection.appendChild(strokeLabel);
        strokeSection.appendChild(strokeSlider);
        toolbar.appendChild(strokeSection);

        // Action buttons
        const actionsSection = document.createElement('div');
        actionsSection.className = 'toolbar-section actions-section';

        const undoBtn = document.createElement('button');
        undoBtn.className = 'action-btn';
        undoBtn.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" fill="none" stroke-width="2"><path d="M3 10h10a5 5 0 015 5v2M3 10l5-5M3 10l5 5"/></svg>';
        undoBtn.title = 'Undo';
        undoBtn.addEventListener('click', () => this.undo());

        const redoBtn = document.createElement('button');
        redoBtn.className = 'action-btn';
        redoBtn.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" fill="none" stroke-width="2"><path d="M21 10H11a5 5 0 00-5 5v2M21 10l-5-5M21 10l-5 5"/></svg>';
        redoBtn.title = 'Redo';
        redoBtn.addEventListener('click', () => this.redo());

        const clearBtn = document.createElement('button');
        clearBtn.className = 'action-btn danger';
        clearBtn.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" fill="none" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>';
        clearBtn.title = 'Clear All';
        clearBtn.addEventListener('click', () => this.clear());

        actionsSection.appendChild(undoBtn);
        actionsSection.appendChild(redoBtn);
        actionsSection.appendChild(clearBtn);
        toolbar.appendChild(actionsSection);

        this.container.insertBefore(toolbar, this.container.firstChild);
    }

    attachEventListeners() {
        // Mouse events
        this.canvas.addEventListener('mousedown', (e) => this.startDrawing(e));
        this.canvas.addEventListener('mousemove', (e) => this.draw(e));
        this.canvas.addEventListener('mouseup', () => this.stopDrawing());
        this.canvas.addEventListener('mouseleave', () => this.stopDrawing());

        // Touch events for mobile
        this.canvas.addEventListener('touchstart', (e) => this.handleTouch(e, 'start'), { passive: false });
        this.canvas.addEventListener('touchmove', (e) => this.handleTouch(e, 'move'), { passive: false });
        this.canvas.addEventListener('touchend', (e) => this.handleTouch(e, 'end'), { passive: false });
        this.canvas.addEventListener('touchcancel', (e) => this.handleTouch(e, 'end'), { passive: false });

        // Prevent clicks on canvas from bubbling up (accidental submit prevention)
        this.canvas.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Prevent container clicks from affecting parent elements
        this.container.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        this.container.addEventListener('touchstart', (e) => {
            // Only stop propagation if touch is on canvas or toolbar
            if (e.target.closest('.drawing-canvas') || e.target.closest('.drawing-toolbar')) {
                e.stopPropagation();
            }
        }, { passive: true });
    }

    handleTouch(e, action) {
        // Prevent default and stop propagation to avoid accidental form submissions
        e.preventDefault();
        e.stopPropagation();

        if (e.touches && e.touches.length > 0) {
            const touch = e.touches[0];
            const rect = this.canvas.getBoundingClientRect();
            const mouseEvent = {
                clientX: touch.clientX,
                clientY: touch.clientY,
                offsetX: touch.clientX - rect.left,
                offsetY: touch.clientY - rect.top
            };

            if (action === 'start') this.startDrawing(mouseEvent);
            else if (action === 'move') this.draw(mouseEvent);
        }

        if (action === 'end') this.stopDrawing();
    }

    getCoords(e) {
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;

        return {
            x: (e.clientX - rect.left) * scaleX,
            y: (e.clientY - rect.top) * scaleY
        };
    }

    startDrawing(e) {
        this.isDrawing = true;
        const coords = this.getCoords(e);
        this.startX = coords.x;
        this.startY = coords.y;

        if (this.currentTool === 'pen' || this.currentTool === 'eraser') {
            this.ctx.beginPath();
            this.ctx.moveTo(coords.x, coords.y);
        }

        // Save state before starting shape
        if (['line', 'arrow', 'rectangle', 'diamond', 'oval'].includes(this.currentTool)) {
            this.tempImage = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        }
    }

    draw(e) {
        if (!this.isDrawing) return;

        const coords = this.getCoords(e);

        if (this.currentTool === 'pen') {
            this.ctx.strokeStyle = this.options.strokeColor;
            this.ctx.lineWidth = this.options.strokeWidth;
            this.ctx.lineCap = 'round';
            this.ctx.lineJoin = 'round';
            this.ctx.lineTo(coords.x, coords.y);
            this.ctx.stroke();
        } else if (this.currentTool === 'eraser') {
            this.ctx.strokeStyle = this.options.backgroundColor;
            this.ctx.lineWidth = this.options.strokeWidth * 3;
            this.ctx.lineCap = 'round';
            this.ctx.lineTo(coords.x, coords.y);
            this.ctx.stroke();
        } else if (this.tempImage) {
            // Restore and redraw shape
            this.ctx.putImageData(this.tempImage, 0, 0);
            this.drawShape(coords.x, coords.y);
        }
    }

    drawShape(endX, endY) {
        this.ctx.strokeStyle = this.options.strokeColor;
        this.ctx.lineWidth = this.options.strokeWidth;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        const width = endX - this.startX;
        const height = endY - this.startY;

        switch (this.currentTool) {
            case 'line':
                this.ctx.beginPath();
                this.ctx.moveTo(this.startX, this.startY);
                this.ctx.lineTo(endX, endY);
                this.ctx.stroke();
                break;

            case 'arrow':
                this.drawArrow(this.startX, this.startY, endX, endY);
                break;

            case 'rectangle':
                this.ctx.beginPath();
                this.ctx.rect(this.startX, this.startY, width, height);
                this.ctx.stroke();
                break;

            case 'diamond':
                this.drawDiamond(this.startX, this.startY, width, height);
                break;

            case 'oval':
                this.drawOval(this.startX, this.startY, width, height);
                break;
        }
    }

    drawArrow(fromX, fromY, toX, toY) {
        const headLength = 15;
        const angle = Math.atan2(toY - fromY, toX - fromX);

        this.ctx.beginPath();
        this.ctx.moveTo(fromX, fromY);
        this.ctx.lineTo(toX, toY);
        this.ctx.stroke();

        // Arrow head
        this.ctx.beginPath();
        this.ctx.moveTo(toX, toY);
        this.ctx.lineTo(
            toX - headLength * Math.cos(angle - Math.PI / 6),
            toY - headLength * Math.sin(angle - Math.PI / 6)
        );
        this.ctx.lineTo(
            toX - headLength * Math.cos(angle + Math.PI / 6),
            toY - headLength * Math.sin(angle + Math.PI / 6)
        );
        this.ctx.closePath();
        this.ctx.fillStyle = this.options.strokeColor;
        this.ctx.fill();
    }

    drawDiamond(x, y, width, height) {
        const centerX = x + width / 2;
        const centerY = y + height / 2;

        this.ctx.beginPath();
        this.ctx.moveTo(centerX, y);
        this.ctx.lineTo(x + width, centerY);
        this.ctx.lineTo(centerX, y + height);
        this.ctx.lineTo(x, centerY);
        this.ctx.closePath();
        this.ctx.stroke();
    }

    drawOval(x, y, width, height) {
        const centerX = x + width / 2;
        const centerY = y + height / 2;
        const radiusX = Math.abs(width / 2);
        const radiusY = Math.abs(height / 2);

        this.ctx.beginPath();
        this.ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
        this.ctx.stroke();
    }

    stopDrawing() {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.tempImage = null;
            this.saveState();
            this.autoSave();
        }
    }

    setTool(tool) {
        this.currentTool = tool;
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tool === tool);
        });
    }

    setColor(color) {
        this.options.strokeColor = color;
        document.querySelectorAll('.color-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.color === color);
        });
    }

    saveState() {
        const imageData = this.canvas.toDataURL('image/png');
        this.history.push(imageData);

        // Limit history to 20 states
        if (this.history.length > 20) {
            this.history.shift();
        }

        this.redoStack = [];
    }

    undo() {
        if (this.history.length > 1) {
            this.redoStack.push(this.history.pop());
            this.loadState(this.history[this.history.length - 1]);
        }
    }

    redo() {
        if (this.redoStack.length > 0) {
            const state = this.redoStack.pop();
            this.history.push(state);
            this.loadState(state);
        }
    }

    loadState(dataUrl) {
        const img = new Image();
        img.onload = () => {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.drawImage(img, 0, 0);
        };
        img.src = dataUrl;
    }

    clear() {
        if (confirm('Are you sure you want to clear the drawing?')) {
            this.ctx.fillStyle = this.options.backgroundColor;
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.saveState();
            this.autoSave();
        }
    }

    autoSave() {
        if (this.options.onSave && this.options.questionId) {
            const imageData = this.canvas.toDataURL('image/png');
            this.options.onSave(this.options.questionId, imageData);
        }
    }

    getImageData() {
        return this.canvas.toDataURL('image/png');
    }

    setBackgroundImage(imageUrl) {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
            this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height);
            this.saveState();
        };
        img.src = imageUrl;
    }
}

// Export for use
window.DrawingCanvas = DrawingCanvas;
