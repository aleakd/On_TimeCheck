from app import create_app
from app.models import db, Empresa

app = create_app()

with app.app_context():

    existe = Empresa.query.first()

    if existe:
        print("Ya existe empresa:", existe.nombre)
        exit()

    empresa = Empresa(
        nombre="Empresa Demo"
    )

    db.session.add(empresa)
    db.session.commit()

    print("✅ Empresa creada:", empresa.nombre)
