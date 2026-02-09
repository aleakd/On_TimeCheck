from app import create_app
from app.models import db, Usuario, Empresa
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():

    empresa = Empresa.query.first()

    if not empresa:
        print("❌ No existe empresa")
        exit()

    usuarios = [
        ("admin@test.com", "admin"),
        ("supervisor@test.com", "supervisor"),
        ("empleado@test.com", "empleado")
    ]

    for email, rol in usuarios:

        existe = Usuario.query.filter_by(email=email).first()
        if existe:
            print("Ya existe:", email)
            continue

        user = Usuario(
            empresa_id=empresa.id,
            email=email,
            password_hash=generate_password_hash("1234"),
            rol=rol
        )

        db.session.add(user)
        print("Creado:", email, "| Rol:", rol)

    db.session.commit()
    print("\n✅ Usuarios listos")
