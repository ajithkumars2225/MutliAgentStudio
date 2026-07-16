import os
import urllib.request

libs = {
    # CSS
    "static/lib/codemirror.min.css": "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.13/codemirror.min.css",
    "static/lib/theme/dracula.min.css": "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.13/theme/dracula.min.css",
    "static/lib/xterm.css": "https://cdn.jsdelivr.net/npm/xterm@5.1.0/css/xterm.css",
    
    # JS
    "static/lib/marked.min.js": "https://cdn.jsdelivr.net/npm/marked/marked.min.js",
    "static/lib/codemirror.min.js": "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.13/codemirror.min.js",
    
    # CodeMirror Modes
    "static/lib/mode/python.min.js": "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.13/mode/python/python.min.js",
    "static/lib/mode/javascript.min.js": "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.13/mode/javascript/javascript.min.js",
    "static/lib/mode/htmlmixed.min.js": "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.13/mode/htmlmixed/htmlmixed.min.js",
    "static/lib/mode/xml.min.js": "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.13/mode/xml/xml.min.js",
    "static/lib/mode/css.min.js": "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.13/mode/css/css.min.js",
    "static/lib/mode/clike.min.js": "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.13/mode/clike/clike.min.js",
    "static/lib/mode/htmlembedded.min.js": "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.13/mode/htmlembedded/htmlembedded.min.js",
    
    # Xterm
    "static/lib/xterm.js": "https://cdn.jsdelivr.net/npm/xterm@5.1.0/lib/xterm.js",
    "static/lib/xterm-addon-fit.js": "https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.7.0/lib/xterm-addon-fit.js"
}

print("Starting download of CDN libraries...")

for path, url in libs.items():
    dir_name = os.path.dirname(path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        print(f"Created directory: {dir_name}")
    
    print(f"Downloading {url} -> {path}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(path, 'wb') as out_file:
            out_file.write(response.read())
        print("Success!")
    except Exception as e:
        print(f"Failed to download: {e}")

print("All downloads complete!")
