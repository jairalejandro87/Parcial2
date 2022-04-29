from flask import Flask, flash, render_template, request, redirect, url_for, session
from itsdangerous import SignatureExpired, URLSafeTimedSerializer
import mysql.connector
import re
from hashlib import sha256
from email.message import EmailMessage
from smtplib import SMTP
from flask_mail import Mail, Message
from datetime import date, datetime

db = mysql.connector.connect(
    host="localhost", user="root", password="", port=3306, database="registroUsuarios"
)
db.autocommit = True

app = Flask(__name__)
app.secret_key = "##91!IyAj#FqkZ2C"
mail=Mail(app)
s=URLSafeTimedSerializer('Thisisasecret')

@app.get("/")
def inicio():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if (
        request.method == "POST"
        and "email" in request.form
        and "password" in request.form
    ):

        email = request.form["email"]
        password = request.form["password"]
        password = sha256(password.encode("utf-8")).hexdigest()

        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM usuarios WHERE email = %s AND contraseña = %s AND confirmacion='1'",
            (
                email,
                password,
            ),
        )

        cuenta = cursor.fetchone()
        cursor.close()

        if cuenta:
            session["login"] = True
            session["id_usuario"] = cuenta["id_usuario"]
            session["email"] = cuenta["email"]
            return redirect(url_for("muro", email=email))
        else:

            flash("¡Nombre de usuario/contraseña incorrectos!")

    return render_template("inicio_sesion.html")



@app.route("/login/muro/<email>", methods=["GET", "POST"])
def muro(email):
    if (
        request.method == "POST"
        and "imagen" in request.files
    ):
        imagen = request.files['imagen']
        if (
            not imagen 
        ):
            flash("¡Por favor llene el formulario!")
        else:
            today = date.today()
            now = datetime.now()
            fecha= str(today)+str(now.hour)+str(now.minute)+str(now.second)+str(now.microsecond)
            nombreImagen = imagen.filename
            imagen.save('./static/imagenes/' + nombreImagen)
            imagen_n=str(fecha)+nombreImagen
            cursor = db.cursor(dictionary=True)
            print(email)
            cursor.execute("UPDATE usuarios SET archivo=%s WHERE email='"+email+"'", (
                imagen_n,
            ))            
            cursor.close()
            flash("Se guardo el archivo correctamente")

    return render_template("muro.html")

@app.route("/registroUsuario", methods=["GET", "POST"])
def registroUsuario():
    if (
        request.method == "POST"
        and "nombre" in request.form
        and "email" in request.form
        and "password" in request.form
    ):

        nombre = request.form["nombre"]
        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        cuenta = cursor.fetchone()
        
        token=s.dumps(email, salt='email-confirm')
        link= url_for('confirmarEmail', token=token, _external=True)

        caracterspecial = ["$", "@", "#", "%"]

        is_valid = True

        if cuenta:
            flash("Ya hay un usuario registrado con este correo!")
            is_valid = False

        if nombre == "":
            flash("El nombre es requerido")
            is_valid = False

        if not (len(password) >= 8 and len(password) <= 20):
            flash("La contraseña debe tener min 8 y max 20 caracteres")
            is_valid = False

        if not any(char.isdigit() for char in password):
            flash("La contraseña debe tener al menos un número")
            is_valid = False

        if not any(char.isupper() for char in password):
            flash("La contraseña debe tener al menos una letra mayúscula")
            is_valid = False

        if not any(char.islower() for char in password):
            flash("La contraseña debe tener al menos una letra minúscula")
            is_valid = False

        if not any(char in caracterspecial for char in password):
            flash("La contraseña debe tener al menos uno de los símbolos $,@,%,#")
            is_valid = False

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("¡Dirección de correo electrónico no válida!")
            is_valid = False

        if (not nombre or not email or not password):
            flash("¡Por favor llene el formulario!")
            is_valid = False
       

        if is_valid == False:
            return render_template(
                "RegistroUsuario.html",
                nombre=nombre,
                email=email,
                password=password,
            )
        else:
            password = sha256(password.encode("utf-8")).hexdigest()
            cursor.execute(
                "INSERT INTO usuarios(nombre, email, contraseña) VALUES (%s, %s, %s)",
                (
                    nombre,
                    email,
                    password,
                ),
            )
            
            
           
            cursor.close()
            msg = EmailMessage()
            msg.set_content("Confirmar tu correo aqui: {} ".format(link))
            msg["Subject"] = "REGISTRO DE USUARIO"
            msg["From"] = "jairpistala2020@itp.edu.co"
            msg["To"] = email
            username = "jairpistala2020@itp.edu.co"
            password = "1124867475"  
            server = SMTP("smtp.gmail.com:587")
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            flash("¡Te has registrado con éxito!")

    elif request.method == "POST":
        flash("¡Por favor llene el formulario!")

    return render_template("RegistroUsuario.html")

@app.route("/login/confirmarEmail/<token>")
def confirmarEmail(token):
    try:
        email=s.loads(token, salt='email-confirm', max_age=120)
        cursor = db.cursor()
        cursor.execute("UPDATE usuarios SET confirmacion='1' WHERE email='"+email+"'")
        cursor.close()
    except SignatureExpired:
        cursor = db.cursor()
        cursor.execute("DELETE FROM usuarios WHERE email='"+email+"' AND confirmacion='0'")
        cursor.close()
        return "<h1>Tiempo limite excedido</h1>"
    return "<h1>Bienvenido tu cuenta se ha confirmado con exito!</h1>"


@app.route("/restablecerPassword", methods=["GET", "POST"])
def restablecerPassword():
    if (
        request.method == "POST"
        and "email" in request.form
    ):
        email = request.form.get("email")
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM usuarios WHERE email = %s AND confirmacion='1'",
            (
                email,
            ),
        )
        cuenta = cursor.fetchone()
        cursor.close()

        if not(cuenta):
            flash('¡Esta cuenta no existe!')
            return render_template('Index.html')

        token_password=s.dumps(email, salt='restablecer-password')
        link_password= url_for('cambiarPassword_a', token_password=token_password, _external=True)  

        msg = EmailMessage()
        msg.set_content("Para restablecer tu contraseña ingresa al siguiente link (Tiempo limite 2 min) : {} ".format(link_password))
        msg["Subject"] = "Recuperar contraseña"
        msg["From"] = "jairpistala2020@itp.edu.co"
        msg["To"] = email
        username = "jairpistala2020@itp.edu.co"
        password = "1124867475" 
        server = SMTP("smtp.gmail.com:587")
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        flash("Revisar el correo")

    return render_template("correoRestablecerContraseña.html")
        

@app.route("/restablecerPassword_a/<token_password>")
def cambiarPassword_a(token_password):
    try:
        email=s.loads(token_password, salt='restablecer-password', max_age=60)
    except SignatureExpired:
        return render_template("correoRestablecerContraseña.html")
    return redirect(url_for('cambiarContra', email=email, _external=True))

@app.route("/restablecerPass/<email>", methods=["GET", "POST"])
def cambiarContra(email):
    if request.method == "GET":
        return render_template("restablecerPassword.html")
    else:   
        password = request.form.get("password")
        password_verificacion= request.form.get("password_verificacion")
        if password==password_verificacion:
                caracterspecial = ["$", "@", "#", "%"]
                is_valid = True
                print(password)
                print(len(password))
                if not (int(len(password)) >= 8 and int(len(password)) <= 20):
                    flash("La contraseña debe tener min 8 y max 20 caracteres")
                    is_valid = False

                if not any(char.isdigit() for char in password):
                    flash("La contraseña debe tener al menos un número")
                    is_valid = False

                if not any(char.isupper() for char in password):
                    flash("La contraseña debe tener al menos una letra mayúscula")
                    is_valid = False

                if not any(char.islower() for char in password):
                        flash("La contraseña debe tener al menos una letra minúscula")
                        is_valid = False

                if not any(char in caracterspecial for char in password):
                        flash("La contraseña debe tener al menos uno de los símbolos $,@,%,#")
                        is_valid = False    

                if is_valid == False:
                    return render_template(
                        "restablecerPassword.html",
                        password=password,
                        password_verificacion=password_verificacion,
                    )   

                passwordencriptada = sha256(password.encode("utf-8")).hexdigest()
                cursor = db.cursor(dictionary=True)
                cursor.execute("UPDATE usuarios SET contraseña=%s WHERE email=%s",
                (
                    passwordencriptada,
                    email,
                ))
                cursor.close()
                flash("Contraseña corregida")
                return render_template("inicio_sesion.html")
        else:
            flash("Comprobar de que las contraseñas sean iguales!")
            return render_template(
                    "restablecerPassword.html",
                    password=password,
                    password_verificacion=password_verificacion,
            )


app.run(debug=True)

