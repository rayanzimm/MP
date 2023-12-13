from flask import Flask, session, render_template, request, redirect
import pyrebase

app = Flask(__name__)

config = {
    'apiKey': "AIzaSyCwckzqjSuDBdPvFGmwxW_t86FMcaiFYOs",
    'authDomain': "finsaver3.firebaseapp.com",
    'projectId': "finsaver3",
    'storageBucket': "finsaver3.appspot.com",
    'messagingSenderId': "546832209179",
    'appId': "1:546832209179:web:8be50246cdaf1bdc53efbe",
    'measurementId': "G-365RF89GXF",
    'databaseURL': ''
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()

app.secret_key = 'secret'

@app.route('/', methods=['POST', 'GET'])
def index():
    if('user' in session):
        return render_template('home.html')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = email
        except:
            return 'Failed to login'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = auth.create_user_with_email_and_password(email, password)
            session['user'] = email
            return render_template('login.html')  # Redirect to login page after successful registration
        except Exception as e:
            # Handle registration errors, you might want to display an error message or log the exception
            return render_template('register.html', error_message=str(e))

    return render_template('register.html')  



if __name__ == '__main__':
    app.run(debug=True)
