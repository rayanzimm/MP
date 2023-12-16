from flask import Flask, session, render_template, request, redirect, flash, url_for
import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore
import re

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

# Use firebase_admin to initialize Firestore
cred = credentials.Certificate(r'C:\Users\S531FL-BQ559T\OneDrive\Documents\MP\Project\MP\src\finsaver3-firebase-adminsdk-udjjx-b479ad6c2d.json')
firebase_admin.initialize_app(cred, {'projectId': 'finsaver3'})
db = firestore.client()

app.secret_key = 'secret'

@app.route('/', methods=['POST', 'GET'])
def index():
    if 'user' in session:
        return render_template('home.html')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = email
        except:
            flash("Invalid email or password.", "warning")
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
        firstName = request.form.get('firstName')
        lastName = request.form.get('lastName')
        dob = request.form.get('dob')
        address = request.form.get('address')
        mobile = request.form.get('mobile')
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email) or not email.endswith('.com'):
            flash("Please enter a valid email.", "warning")
        
        # Validate firstName and lastName are valid strings
        elif not all(map(str.isalpha, [firstName, lastName])):
            flash("Please enter a valid name.", "warning")
        
        # Validate the password length
        if len(password) > 10:
            flash("Maximum characters for password is 10.", "warning")
        
        # Validate mobile contains only numbers
        if not mobile.isdigit():
            flash("Please enter a valid phone number.", "warning")
        
        try:
            user = auth.create_user_with_email_and_password(email, password)
            
            # Store additional user information in Firestore
            user_data = {
                'email': email,
                'firstName': firstName,
                'lastName': lastName,
                'dob': dob,
                'address': address,
                'mobile': mobile
            }
            db.collection('users').add(user_data)
            
            session['user'] = email
            flash("Registration successful!", "success")
            return render_template('login.html')  # Redirect to login page after successful registration
            
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "warning")

    return render_template('register.html')

@app.route('/forgetpass', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        try:
            # Assuming the email is sent in the request form
            data = request.form
            email = data.get('email')

            if re.match(r"[^@]+@[^@]+\.[^@]+", email) and email.endswith('.com'):
                auth.send_password_reset_email(email)
                flash("Reset email has been successfuly sent! Please check your inbox.", "success")
                
            else:
                flash("Please enter a valid email", "warning")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "warning")
    return render_template('forgetpass.html')


if __name__ == '__main__':
    app.run(debug=True)
