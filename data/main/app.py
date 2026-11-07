from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

from data.main.vistas import LOGIN_HTML, INDEX_HTML

app = Flask(__name__)
app.secret_key = "secret_cxp_key_cloud"


# ==========================================
# VISTAS (UI)
# ==========================================
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template_string(INDEX_HTML, username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form.get('username', '').strip()
        return redirect(url_for('index'))
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ==========================================
# ENDPOINTS DE PROCESAMIENTO (PENDIENTES)
# El frontend (vistas.py) ya llama a estas rutas.
# Reemplazar con la nueva lógica de procesamiento.
# ==========================================
NO_IMPLEMENTADO = {'error': 'Procesamiento pendiente de implementar.'}

@app.route('/previsualizar', methods=['POST'])
def previsualizar():
    # Esperado por la UI: {'folios': [...], 'total': int}  |  {'error': str}
    return jsonify(NO_IMPLEMENTADO), 501

@app.route('/procesar', methods=['POST'])
def procesar():
    # Esperado por la UI: {'status': 'success', 'data': [ {...fila...}, ... ]}  |  {'error': str}
    return jsonify(NO_IMPLEMENTADO), 501

@app.route('/descargar')
def descargar():
    return "No hay archivo", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
