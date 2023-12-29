from flask import Flask, session, render_template, request, redirect, flash, url_for
from google.cloud.firestore_v1.base_query import FieldFilter
import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore
import re
from firebase_admin import auth
from werkzeug.utils import secure_filename
import os
import requests
import json

app = Flask(__name__)
UPLOAD_FOLDER = r'D:\Microsoft VS Code\MP\MP\static\assets\img'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
cred = credentials.Certificate(r'C:\Poly module\Year 3\MP\Website Code\MP\src\finsaver3-firebase-adminsdk-udjjx-b479ad6c2d.json')
firebase_admin.initialize_app(cred, {'projectId': 'finsaver3'})
db = firestore.client()

app.secret_key = 'secret'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

        # Check if a file is included in the request
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '' and allowed_file(photo.filename):
                # Save the uploaded photo with an absolute path
                filename = secure_filename(photo.filename)
                full_path = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], filename)
                photo.save(full_path)
                flash("Photo uploaded successfully!", "success")

                try:
                    user = auth.create_user_with_email_and_password(email, password)

                    # Store additional user information in Firestore, including the file path
                    user_data = {
                        'email': email,
                        'firstName': firstName,
                        'lastName': lastName,
                        'dob': dob,
                        'address': address,
                        'mobile': mobile,
                        'photo_path': os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    }
                    db.collection('users').add(user_data)

                    session['user'] = email
                    flash("Registration successful!", "success")
                    return render_template('login.html')  # Redirect to the login page after successful registration

                except Exception as e:
                    flash(f"An error occurred during user creation: {str(e)}", "warning")
            else:
                flash("Invalid file format. Please upload a valid image.", "warning")

        # Validate firstName and lastName are valid strings
        if not all(map(str.isalpha, [firstName, lastName])):
            flash("Please enter a valid name.", "warning")

        # Validate the password length
        elif len(password) < 6:
            flash("Minimum characters for the password are 6.", "warning")

        # Validate mobile contains only numbers
        elif not mobile.isdigit() or len(mobile) != 8:
            flash("Please enter a valid phone number.", "warning")

        elif dob == "":
            flash("Please enter a valid date of birth.", "warning")

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
    user_ref = db.collection('users').where('email', '==', user_email).stream()
    
    # Assuming there is only one user with the given email
    user_doc = next(user_ref, None)
    
    if not user_doc:
        # Handle the case where the user is not found
        return redirect('/')

    user_data = user_doc.to_dict()

    if request.method == 'POST':
        new_address = request.form.get('new_address')
        new_mobile = request.form.get('new_mobile')
        new_firstName = request.form.get('new_firstName')
        new_lastName = request.form.get('new_lastName')
        new_dob = request.form.get('new_dob')

        # Check if a file is included in the request
        if 'new_photo' in request.files:
            new_photo = request.files['new_photo']
            if new_photo.filename != '' and allowed_file(new_photo.filename):
                # Save the uploaded photo to the upload folder
                filename = secure_filename(new_photo.filename)
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                new_photo.save(full_path)
                flash("New photo uploaded successfully!", "success")
            else:
                flash("Invalid file format. Please upload a valid image.", "warning")

        # Update user details in Firestore, including the new file path if a new photo is uploaded
        update_data = {
            'address': new_address,
            'mobile': new_mobile,
            'firstName': new_firstName,
            'lastName': new_lastName,
            'dob': new_dob
        }

        if 'new_photo' in request.files:
            update_data['photo_path'] = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Update user details in Firestore
        user_doc.reference.update(update_data)
        flash("Profile updated successfully!", "success")
        return redirect('/profile')

    return render_template('update_profile.html', user_data=user_data)

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    user_ref = db.collection('users').where('email', '==', user_email).get()

    # Assuming there is only one user with the given email
    for user_doc in user_ref:
        user_data = user_doc.to_dict()
        if user_data:
            return render_template('profile.html', user_data=user_data)
        else:
            flash("User not found.", "warning")
            return redirect('/')

@app.route('/delete_profile', methods=['GET', 'POST'])
def delete_profile():
    if 'user' not in session:
        return redirect('/')
    
    email = session['user']

    if request.method == 'POST':
        password = request.form.get('password')

        # Verify user's password
        try:
            user = auth.sign_in_with_email_and_password(email, password)
        except Exception as e:
            # Incorrect password or other authentication error
            flash("Incorrect password. Please try again.", "warning")
            return render_template('delete_profile.html')

        try:
            # Get the user document reference in Firestore
            user_ref = db.collection('users').where('email', '==', email).get()
            
            # Delete user information from Firestore
            for user_doc in user_ref:
                user_id = user_doc.id
                db.collection('users').document(user_id).delete()

            # Delete user from authentication
            auth.delete_user_account(user['idToken'])
        except auth.AuthError as e:
            # Handle error if user deletion from authentication fails
            flash("Error deleting user from authentication.", "danger")
            return render_template('delete_profile.html')
        
        # Logout the user after deletion
        session.pop('user')

        # You may also want to clear the session data completely
        session.clear()
        flash("Account successfully deleted!", "success")
        return redirect('/')

    return render_template('delete_profile.html')

@app.route('/food')
def food():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']

    # Fetch the list of food expenses for the logged-in user
    food_expenses = db.collection('food').where('user_email', '==', user_email).stream()

    return render_template('food.html', food_expenses=food_expenses)




@app.route('/addfood', methods=['GET', 'POST'])
def addfood():
    if request.method == 'POST':
        user_email = session['user']
        food_id = request.form.get('food_id')
        foodName = request.form.get('foodName')
        cost = request.form.get('cost')

        try:
            # Original data
            food_data = {
                'user_email': user_email,
                'foodName': foodName,
                'cost': cost,
            }

            # Get dynamic fields
            dynamic_fields = request.form.getlist('newField')
            print("Dynamic Fields:", dynamic_fields)

            # Process dynamic fields and add them to food_data
            for index, value in enumerate(dynamic_fields):
                food_data[f'newField_{index + 1}'] = value

            if food_id:
                # Editing an existing food expense
                food_ref = db.collection('food').document(food_id)
                food_ref.update(food_data)
            else:
                # Adding a new food expense
                db.collection('food').add(food_data)

            flash("Food expense saved successfully!", "success")
            return redirect('/food')

        except Exception as e:
            flash(f"An error occurred during food creation: {str(e)}", "warning")

    return render_template('food.html')

@app.route('/fetchfooddata', methods=['GET'])
def fetch_food_data():
    try:
        # Check if the user is authenticated
        if 'user' not in session:
            return jsonify({'error': 'User not authenticated'}), 401

        user_email = session['user']

        # Query the database to fetch food data based on user_email
        food_data = (
            db.collection('food')
            .where('user_email', '==', user_email)
            .stream()  # Use stream to iterate over query results
        )

        # Convert the data to a list of dictionaries
        food_list = [food.to_dict() for food in food_data]

        # Render the HTML template with the fetched data
        return render_template('fetchfooddata.html', food_list=food_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/editfood/<user_email>', methods=['GET', 'POST'])
def editfood(user_email):
    if 'user' not in session or session['user'] != user_email:
        flash("Unauthorized access", "warning")
        return redirect('/')

    try:
        # Fetch the most recent food expense for the user
        food_query = db.collection('food').where('user_email', '==', user_email).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1)
        food_docs = food_query.stream()

        if not food_docs:
            flash("No food expenses found for the user", "warning")
            return redirect('/food')

        # Use the most recent food expense
        food_doc = next(food_docs)

        if request.method == 'POST':
            # Update food expense based on the form submission
            foodName = request.form.get('foodName')
            cost = request.form.get('cost')

            food_data = {
                'foodName': foodName,
                'cost': cost,
            }

            # Get dynamic fields
            dynamic_fields = request.form.getlist('newField')
            print("Dynamic Fields:", dynamic_fields)

            # Process dynamic fields and add them to food_data
            for index, value in enumerate(dynamic_fields):
                food_data[f'newField_{index + 1}'] = value

            # Update the food expense
            food_ref = db.collection('food').document(food_doc.id)
            food_ref.update(food_data)

            flash("Food expense updated successfully!", "success")
            return redirect('/food')

        # Pre-fill the form with existing data for editing
        food_data = food_doc.to_dict()
        return render_template('editfood.html', food_data=food_data)

    except Exception as e:
        flash(f"An error occurred during food editing: {str(e)}", "warning")
        return redirect('/food')


        
@app.route('/news', methods=['GET', 'POST'])
def news():
    api = 'KeEBnRS1TZoCUZYZVdA3MgSENtmqZHU8'
    base_url = 'https://api.polygon.io/v2/reference/news'

    ticker_url = f'https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1000&apiKey={api}'
    ticker_response = requests.get(ticker_url)
    ticker_data = ticker_response.json()
    tickers = [result.get('ticker') for result in ticker_data.get('results', [])]

    # This ticker is from the form in news.html
    ticker = request.args.get('ticker', default='', type=str)
    url = f'{base_url}?order=desc&limit=1000&sort=published_utc&apiKey={api}&ticker={ticker}'

    try:
        payload = {}
        headers = {}

        response = requests.request("GET", url, headers=headers, data=payload)
        data = json.loads(response.text)
        newsData = data['results']
        

        # Function to format news article data
        formatted_data = []
        for i in range(min(1000, len(newsData))):
           formatted_data.append({
                'title': newsData[i]["title"],
                'author': newsData[i]["author"],
                'published_utc': newsData[i]["published_utc"],
                'article_url': newsData[i]["article_url"],
                'image_url': newsData[i]["image_url"]
            })

        return render_template('news.html', news_data=formatted_data, selected_ticker=ticker, tickers=tickers)

        # Extract information for the specified number of news articles
    
    except Exception as e:
        flash(f"An error has occured: {str(e)}", "warning")
        return render_template('news.html', news_data=[], selected_ticker=None, tickers=tickers)
    


if __name__ == '__main__':
    app.run(debug=True)