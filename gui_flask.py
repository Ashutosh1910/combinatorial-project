
import io
import uuid
from flask import Flask, request, redirect, url_for, render_template_string, send_file, abort
import matplotlib

matplotlib.use('Agg')

from allocate import generate_layouts, draw_layout, Room
import matplotlib.pyplot as plt

app = Flask(__name__)
STORAGE = {}

INDEX_HTML = '''
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Floor Plan Generator</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial; margin: 24px; color:#222; }
        .container { max-width: 980px; margin: 0 auto; }
        h1 { margin-bottom: 12px; }
        form { background: #fff; border: 1px solid #e1e4e8; padding: 16px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }
        .row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:8px; }
        label { font-size:14px; color:#444; }
        input[type=number] { width:96px; padding:6px 8px; border:1px solid #cbd5e0; border-radius:6px; }
        textarea { width:100%; min-height:160px; padding:8px; border-radius:6px; border:1px solid #cbd5e0; font-family:monospace; }
        .muted { color:#666; font-size:13px; }
        button { background:#2563eb; color:#fff; border:none; padding:10px 14px; border-radius:6px; cursor:pointer; font-weight:600; }
        button:hover { background:#1e40af; }
        .example { background:#f8fafc; border:1px dashed #e2e8f0; padding:10px; border-radius:6px; font-family:monospace; }
        .footer { margin-top:12px; font-size:13px; color:#555; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Floor Plan Generator</h1>
        <form method=post action="/generate">
            <div class="row">
                <label>Plot width: <input type=number name=plot_w value="20" min=1></label>
                <label>Plot height: <input type=number name=plot_h value="20" min=1></label>
                <label>Max layouts: <input type=number name=max_layouts value="10" min=1></label>
            </div>

                <div class="row">
                        <div style="flex:1">
                                <div class="muted">Enter rooms using the fields below. Each row has separate <code>width</code> and <code>height</code>. IDs are assigned automatically.</div>
                                <div id="rooms-list" style="margin-top:8px">
                                    <div class="room-row">
                                        <label>W: <input type="number" name="room_w" value="10" min=1 style="width:96px"></label>
                                        <label>H: <input type="number" name="room_h" value="12" min=1 style="width:96px"></label>
                                        <button type="button" class="rm-btn" onclick="removeRoom(this)">Remove</button>
                                    </div>
                                    <div class="room-row">
                                        <label>W: <input type="number" name="room_w" value="15" min=1 style="width:96px"></label>
                                        <label>H: <input type="number" name="room_h" value="8" min=1 style="width:96px"></label>
                                        <button type="button" class="rm-btn" onclick="removeRoom(this)">Remove</button>
                                    </div>
                                    <div class="room-row">
                                        <label>W: <input type="number" name="room_w" value="7" min=1 style="width:96px"></label>
                                        <label>H: <input type="number" name="room_h" value="14" min=1 style="width:96px"></label>
                                        <button type="button" class="rm-btn" onclick="removeRoom(this)">Remove</button>
                                    </div>
                                </div>
                                <div style="margin-top:8px">
                                    <button type="button" onclick="addRoomField()" style="background:#10b981; margin-right:8px">Add room</button>
                                    <span class="muted">Use &quot;Add room&quot; to create more rows.</span>
                                </div>
                        </div>
                </div>
                <script>
                    function addRoomField() {
                        const list = document.getElementById('rooms-list');
                        const div = document.createElement('div');
                        div.className = 'room-row';
                        div.style.marginBottom = '6px';
                        div.innerHTML = '<label>W: <input type="number" name="room_w" value="10" min=1 style="width:96px"></label> <label>H: <input type="number" name="room_h" value="8" min=1 style="width:96px"></label> <button type="button" class="rm-btn" onclick="removeRoom(this)">Remove</button>';
                        list.appendChild(div);
                    }
                    function removeRoom(btn) {
                        const row = btn.closest('.room-row');
                        if (!row) return;
                        const list = document.getElementById('rooms-list');
                        // keep at least one field
                        if (list.querySelectorAll('.room-row').length <= 1) {
                            // clear values instead of removing
                            const w = row.querySelector('input[name="room_w"]');
                            const h = row.querySelector('input[name="room_h"]');
                            if (w) w.value = '';
                            if (h) h.value = '';
                            return;
                        }
                        row.remove();
                    }
                </script>

            <div class="row">
                <button type=submit>Generate Layouts</button>
                <div class="muted" style="margin-left:8px">Tip: larger plots and many rooms may take longer to generate.</div>
            </div>
            <div class="footer">After generation you'll be redirected to a gallery of generated layouts where you can click thumbnails to jump to any layout.</div>
        </form>
    </div>
</body>
</html>
'''

VIEW_HTML = '''
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>View Layout</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial; margin:20px; color:#222; }
        .container { max-width:1100px; margin:0 auto; }
        .top { display:flex; gap:18px; align-items:flex-start; }
        .main-image { flex:1; border:1px solid #e2e8f0; padding:12px; border-radius:8px; background:#fff; }
        .meta { width:300px; font-size:14px; color:#333; }
        img.floor { width:100%; height:auto; display:block; border-radius:6px; box-shadow:0 6px 18px rgba(15,23,42,0.06); }
        .thumbs { margin-top:12px; display:flex; gap:8px; flex-wrap:wrap; }
        .thumbs a { display:block; border:2px solid transparent; border-radius:6px; overflow:hidden; }
        .thumbs img { display:block; width:120px; height:90px; object-fit:cover; border-radius:4px; }
        .thumbs a.selected { border-color:#2563eb; box-shadow:0 4px 12px rgba(37,99,235,0.12); }
        .nav { margin-top:10px; }
        a.btn { display:inline-block; padding:8px 12px; background:#2563eb; color:#fff; text-decoration:none; border-radius:6px; font-weight:600; }
        a.btn.secondary { background:#f3f4f6; color:#111; border:1px solid #e5e7eb; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Layout {{ idx+1 }} / {{ total }}</h1>
        <div class="top">
            <div class="main-image">
                <img class="floor" src="{{ url_for('layout_image', lid=lid, index=idx) }}" alt="Layout image">
                <div class="nav">
                    {% if idx>0 %}
                        <a class="btn" href="{{ url_for('view_layout', lid=lid, idx=idx-1) }}">&lt;&lt; Prev</a>
                    {% endif %}
                    {% if idx+1<total %}
                        <a class="btn" href="{{ url_for('view_layout', lid=lid, idx=idx+1) }}">Next &gt;&gt;</a>
                    {% endif %}
                                <a class="btn secondary" href="/">Back to generator</a>
                                <a class="btn secondary" href="{{ url_for('gallery', lid=lid) }}" style="margin-left:8px">Open gallery</a>
                </div>
            </div>
            <div class="meta">
                <p><strong>Plot:</strong> {{ plot_w }} x {{ plot_h }}</p>
                <p><strong>Rooms in layout:</strong> {{ rooms_count }}</p>
                <p><strong>Layout area:</strong> {{ area }}</p>
                <p class="muted">Use Prev/Next to navigate layouts. Thumbnails are for preview only.</p>
            </div>
        </div>

       
    </div>
</body>
</html>
'''


GALLERY_HTML = '''
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Gallery</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial; margin:20px; color:#222; }
        .container { max-width:1100px; margin:0 auto; }
        .grid { display:grid; grid-template-columns: repeat(5, 1fr); gap:12px; }
        .thumb { border:1px solid #e6edf3; border-radius:8px; padding:6px; background:#fff; text-align:center; }
        .thumb img { width:100%; height:140px; object-fit:cover; border-radius:6px; }
        .pager { margin-top:12px; display:flex; gap:8px; align-items:center; }
        a.btn { display:inline-block; padding:8px 12px; background:#2563eb; color:#fff; text-decoration:none; border-radius:6px; font-weight:600; }
        a.info { color:#334155; text-decoration:none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Gallery (page {{ page }} / {{ pages }})</h1>
        <div class="grid">
            {% for item in items %}
                <div class="thumb">
                    <a href="{{ url_for('view_layout', lid=lid, idx=item.index) }}"><img src="{{ url_for('layout_image', lid=lid, index=item.index) }}" alt="Layout {{ item.index+1 }}"></a>
                    <div style="margin-top:6px"><a class="info" href="{{ url_for('view_layout', lid=lid, idx=item.index) }}">Layout {{ item.index+1 }}</a></div>
                </div>
            {% endfor %}
        </div>

        <div class="pager">
            {% if page>1 %}
                <a class="btn" href="{{ url_for('gallery', lid=lid, page=page-1) }}">&lt;&lt; Prev</a>
            {% endif %}
            <div style="flex:1"></div>
            {% if page<pages %}
                <a class="btn" href="{{ url_for('gallery', lid=lid, page=page+1) }}">Next &gt;&gt;</a>
            {% endif %}
            <a class="btn secondary" href="{{ url_for('view_layout', lid=lid, idx=0) }}" style="margin-left:12px">Open first layout</a>
            <a class="btn secondary" href="/" style="margin-left:8px">Back to generator</a>
        </div>
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def index():
    return render_template_string(INDEX_HTML)

@app.route('/generate', methods=['POST'])
def generate():
    plot_w = int(request.form.get('plot_w') or 20)
    plot_h = int(request.form.get('plot_h') or 20)
    max_layouts = int(request.form.get('max_layouts') or 10)

    rooms = []
    widths = request.form.getlist('room_w')
    heights = request.form.getlist('room_h')
    # zip shortest length
    for i, (w_raw, h_raw) in enumerate(zip(widths, heights)):
        if not w_raw and not h_raw:
            continue
        try:
            w = int(w_raw)
            h = int(h_raw)
        except (TypeError, ValueError):
            continue
        rid = i + 1
        rooms.append(Room(rid, w, h))

    if not rooms:
        return "No valid rooms parsed. Please add at least one room with width and height.", 400

    layouts = generate_layouts(rooms, plot_w, plot_h, max_layouts=max_layouts, max_attempts=max_layouts*50)

    lid = str(uuid.uuid4())
    STORAGE[lid] = {"layouts": layouts.reverse(), "plot_w": plot_w, "plot_h": plot_h, "rooms": rooms}

    return redirect(url_for('view_layout', lid=lid, idx=0))

@app.route('/view/<lid>')
def view_layout(lid):
    idx = int(request.args.get('idx', 0))
    data = STORAGE.get(lid)
    if not data:
        abort(404)
    layouts = data['layouts']
    if not layouts:
        return "No layouts generated for this id.", 404
    if idx < 0 or idx >= len(layouts):
        abort(404)
    layout = layouts[idx]
    area = layout.get_room_area()
    return render_template_string(VIEW_HTML, lid=lid, idx=idx, total=len(layouts), plot_w=data['plot_w'], plot_h=data['plot_h'], rooms_count=len(layout.placed_rooms), area=area)


@app.route('/gallery/<lid>')
def gallery(lid):
    data = STORAGE.get(lid)
    if not data:
        abort(404)
    layouts = data['layouts']
    if not layouts:
        return "No layouts generated for this id.", 404

    # Pagination: 10 items per page
    per_page = 10
    page = int(request.args.get('page', 1))
    total = len(layouts)
    pages = (total + per_page - 1) // per_page
    if page < 1:
        page = 1
    if page > pages:
        page = pages

    start = (page - 1) * per_page
    end = min(start + per_page, total)
    items = []
    for i in range(start, end):
        items.append({"index": i})

    return render_template_string(GALLERY_HTML, lid=lid, items=items, page=page, pages=pages)

@app.route('/image/<lid>/<int:index>.png')
def layout_image(lid, index):
    data = STORAGE.get(lid)
    if not data:
        abort(404)
    layouts = data['layouts']
    if index < 0 or index >= len(layouts):
        abort(404)
    layout = layouts[index]

    fig, ax = plt.subplots(figsize=(6,6), dpi=100)
    try:
        draw_layout(ax, layout, data['plot_w'], data['plot_h'], data['rooms'])
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    finally:
        plt.close(fig)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
