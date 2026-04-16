import io
import os
import re
import tempfile
import pandas as pd
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for, send_file

from data.logica.logica_facturas import ProcesadorOracle
from data.main.vistas import LOGIN_HTML, INDEX_HTML

app = Flask(__name__)
app.secret_key = "secret_cxp_key_cloud"

@app.route('/')
def index():
    if 'username' not in session: 
        return redirect(url_for('login'))
    return render_template_string(INDEX_HTML, username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form.get('username', '').strip()
        session['password'] = request.form.get('password', '').strip()
        return redirect(url_for('index'))
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/previsualizar', methods=['POST'])
def previsualizar():
    if 'file' not in request.files:
        return jsonify({'error': 'No se recibió ningún archivo'}), 400
    
    file = request.files['file']
    raw_bytes = file.read()
    
    bytes_limpios = raw_bytes.replace(b'\x00', b'')
    texto_crudo = bytes_limpios.decode('iso-8859-1', errors='ignore')

    patron_cfdi = r'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}'
    folios_encontrados = re.findall(patron_cfdi, texto_crudo)

    if not folios_encontrados:
        try:
            df = pd.read_excel(io.BytesIO(raw_bytes))
            for col in df.columns:
                if 'c.f.d.i' in str(col).lower() or 'folio' in str(col).lower():
                    folios_encontrados = df[col].dropna().astype(str).tolist()
                    break
        except:
            pass

    if folios_encontrados:
        folios_finales = list(dict.fromkeys([f.upper().strip() for f in folios_encontrados]))
        return jsonify({
            'folios': folios_finales[:50],
            'total': len(folios_finales)
        })
    
    if '<frameset' in texto_crudo.lower():
        return jsonify({'error': 'Este archivo es un "Cascarón". Por favor, sube el archivo .xlsx que guardaste o el "sheet001.htm".'}), 400
        
    return jsonify({'error': 'No se encontraron folios CFDI en este archivo.'}), 400

@app.route('/procesar', methods=['POST'])
def procesar():
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    file = request.files['file']
    fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
    os.close(fd)
    file.save(temp_path)
    try:
        procesador = ProcesadorOracle(temp_path, session['username'], session['password'])
        datos, ruta = procesador.ejecutar_cruce()
        session['last_result_path'] = ruta
        return jsonify({"status": "success", "data": datos})
    except Exception as e: return jsonify({"error": str(e)}), 500
    finally: os.remove(temp_path)

@app.route('/descargar')
def descargar():
    ruta = session.get('last_result_path')
    if ruta and os.path.exists(ruta):
        return send_file(ruta, as_attachment=True, download_name="Reporte_Final.xlsx")
    return "No hay archivo", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)