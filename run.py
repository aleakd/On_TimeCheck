from app import create_app

import app,inspect
print("APP MODULE PATH REAL:", inspect.getfile(app))
import sys
print("PYTHON EXECUTABLE:", sys.executable)


app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)