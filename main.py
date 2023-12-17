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
            return redirect('/home')
        except:
            flash("Invalid email or password.", "warning")
    return render_template('login.html')

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect('/')
    return render_template('home.html')

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
        if len(password) > 6:
            flash("Minumum characters for password is 6.", "warning")
        
        # Validate mobile contains only numbers
        if not mobile.isdigit() or len(mobile)!=8:
            flash("Please enter a valid phone number.", "warning")

        if dob=="":
            flash("Please enter a valid date of birth.", "warning")
        
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


@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    user_ref = db.collection('users').where('email', '==', user_email).get()
    
    if request.method == 'POST':
        new_address = request.form.get('new_address')
        new_mobile = request.form.get('new_mobile')
        new_firstName = request.form.get('new_firstName')
        new_lastName = request.form.get('new_lastName')
        new_dob = request.form.get('new_dob')
        # Update user details in Firestore
        for user_doc in user_ref:
            user_id = user_doc.id
            db.collection('users').document(user_id).update({
                'address': new_address,
                'mobile': new_mobile,
                'firstName': new_firstName,
                'lastName': new_lastName,
                'dob': new_dob,
            })
            
        return redirect('/')
    
    return render_template('update_profile.html')

@app.route('/delete_profile', methods=['GET', 'POST'])
def delete_profile():
    if 'user' not in session:
        return redirect('/')
    
    email = session['user']
    user_ref = db.collection('users').where('email', '==', email).get()

    if request.method == 'POST':
        password = request.form.get('password')
        # Delete user from Firestore
        for user_doc in user_ref:
            user_id = user_doc.id
            db.collection('users').document(user_id).delete()

        # Delete user from Firebase Authentication
        try:
            user = auth.sign_in_with_email_and_password(email, password)  # Sign in to get the user's UID
            uid = auth.get_account_info(user['localId'])
            
            auth.delete_user_account(uid)
        except Exception as e:
            # Handle authentication deletion errors
            print(f"Failed to delete user from authentication: {str(e)}")

        # Logout the user after deletion
        session.pop('user')
        return redirect('/')

    return render_template('delete_profile.html')


if __name__ == '__main__':
    app.run(debug=True)