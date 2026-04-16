# run.py en la raíz
from data.main.app import app

if __name__ == "__main__":
    # debug=True habilita el reinicio automático cada vez que guardas un archivo
    app.run(host='0.0.0.0', port=8080, debug=True)