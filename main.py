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
from datetime import datetime


app = Flask(__name__)
UPLOAD_FOLDER = r'static\assets\img'
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

# def openai(prompt):

#     client = OpenAI(
#         # This is the default and can be omitted
#         api_key= "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"
#     )
#     chat_completion = client.chat.completions.create(
#         messages=[
#             {
#                 "role": "user",
#                 "content": prompt
#             }
#         ],
#         model="gpt-3.5-turbo",
#     )
#     print(chat_completion)
# openai("why is the sky blue?")

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
    
    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the total cost for each expense type
    total_food_cost = fetch_total_cost('food', user_email, current_date)
    total_transport_cost = fetch_total_cost('transport', user_email, current_date)
    total_income_cost = fetch_total_cost('income', user_email, current_date)
    total_investment_cost = fetch_total_cost('investment', user_email, current_date)
    total_investmentReturns_cost = fetch_total_cost('investmentReturns', user_email, current_date)

    session['total_food_cost'] = total_food_cost
    session['total_transport_cost'] = total_transport_cost
    session['total_income_cost'] = total_income_cost
    session['total_investment_cost'] = total_investment_cost
    session['total_investmentReturns_cost'] = total_investmentReturns_cost

    total_expense = total_food_cost + total_transport_cost + total_investment_cost - total_investmentReturns_cost
    total_savings = total_income_cost - total_expense

    return render_template('home.html',
                           total_food_cost=total_food_cost,
                           total_transport_cost=total_transport_cost,
                           total_income_cost=total_income_cost,
                           total_investment_cost=total_investment_cost,
                           total_investmentReturns_cost=total_investmentReturns_cost,
                           total_savings=total_savings)


def fetch_total_cost(expense_type, user_email, current_date):
    total_cost = 0

    # Fetch the list of expenses for the given expense type and user
    expense_ref = db.collection(expense_type).where('user_email', '==', user_email).where('date', '==', current_date).stream()

    # Iterate through the expenses and calculate the total cost
    for expense_doc in expense_ref:
        expense_data = expense_doc.to_dict()
        total_cost += float(expense_data.get('cost', 0))

    return total_cost

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']

    # Fetch expenses for specific types
    investment_expenses = fetch_expenses_by_type('investment', user_email)
    food_expenses = fetch_expenses_by_type('food', user_email)
    income_expenses = fetch_expenses_by_type('income', user_email)
    transport_expenses = fetch_expenses_by_type('transport', user_email)

    # Organize expenses by date for each type
    investment_expenses_by_date = organize_expenses_by_date(investment_expenses)
    food_expenses_by_date = organize_expenses_by_date(food_expenses)
    income_expenses_by_date = organize_expenses_by_date(income_expenses)
    transport_expenses_by_date = organize_expenses_by_date(transport_expenses)

    # Calculate total expenses for each category for each date
    total_investment_by_date = calculate_total_by_date(investment_expenses_by_date)
    total_food_by_date = calculate_total_by_date(food_expenses_by_date)
    total_income_by_date = calculate_total_by_date(income_expenses_by_date)
    total_transport_by_date = calculate_total_by_date(transport_expenses_by_date)

    return render_template('history.html',
                           investment_expenses_by_date=investment_expenses_by_date,
                           food_expenses_by_date=food_expenses_by_date,
                           income_expenses_by_date=income_expenses_by_date,
                           transport_expenses_by_date=transport_expenses_by_date,
                           total_investment_by_date=total_investment_by_date,
                           total_food_by_date=total_food_by_date,
                           total_income_by_date=total_income_by_date,
                           total_transport_by_date=total_transport_by_date)

def calculate_total_by_date(expenses_by_date):
    total_by_date = {}

    for date, expenses in expenses_by_date.items():
        total_cost = sum(float(expense['cost']) for expense in expenses)
        total_by_date[date] = total_cost

    return total_by_date

def organize_expenses_by_date(expenses):
    expenses_by_date = {}

    for expense in expenses:
        date = expense.get('date')
        if date not in expenses_by_date:
            expenses_by_date[date] = []

        expenses_by_date[date].append(expense)

    return expenses_by_date

def fetch_expenses_by_type(expense_type, user_email):
    expenses = []

    expense_ref = db.collection(expense_type).where('user_email', '==', user_email).stream()

    for expense_doc in expense_ref:
        expense_data = expense_doc.to_dict()
        expenses.append(expense_data)

    return expenses


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
                full_path = "static/assets/img/" + filename
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
                        'photo_path': "static/assets/img/" + filename
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
                full_path = "static/assets/img/" + filename
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
    return render_template('profile.html')

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


    food_ref = db.collection('food').where('user_email', '==', user_email).stream()
    for food_doc in food_ref:
        food_data = food_doc.to_dict()

        if food_data:
            return render_template('user_food_expenses.html', food_data=food_data)
        else:
            flash("No Food Expenses.", "warning")
            return redirect('/')
        
from datetime import datetime

@app.route('/addfood', methods=['GET', 'POST'])
def addfood():
    if request.method == 'POST':
        user_email = session['user']
        food_id = request.form.get('food_id')
        foodName = request.form.get('foodName')
        cost = request.form.get('cost')

        try:
            # Check if foodName or cost is empty
            if not foodName or not cost:
                flash("Please fill in both food name and cost.", "warning")
                return render_template('food.html')

            latest_food = db.collection('food').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
            latest_index = 0

            for food_doc in latest_food:
                latest_index = int(food_doc.to_dict().get('unique_index', 0))

            unique_index = latest_index + 1

            # Get current date
            current_date = datetime.now().strftime("%Y-%m-%d")

            # Original data
            food_data = {
                'user_email': user_email,
                'foodName': foodName,
                'cost': cost,
                'date': current_date,  # Add the date field
                'unique_index': unique_index
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
            return redirect('/user_food_expenses')

        except Exception as e:
            flash(f"An error occurred during food creation: {str(e)}", "warning")

    return render_template('user_food_expenses.html')


@app.route('/user_food_expenses')
def user_food_expenses():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch the list of food expenses for the logged-in user
    food_expenses = db.collection('food').where('user_email', '==', user_email).where('date', '==', current_date).stream()

    # Create a list to store the food data
    user_food_data = []

    # Iterate through the food expenses and extract relevant information
    for food_doc in food_expenses:
        food_data = food_doc.to_dict()
        user_food_data.append({
            'foodName': food_data.get('foodName', ''),
            'cost': food_data.get('cost', ''),
            'unique_index': food_data.get('unique_index', ''),
            'date': food_data.get('date', ''),
            'current_date': current_date
        })

    # Render user_food_expense.html
    return render_template('user_food_expenses.html', user_food_data=user_food_data)

@app.route('/edit_food_expenses', methods=['GET', 'POST'])
def edit_food_expense():
    # Redirect to the home page if the user is not logged in
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    food_unique_index = request.form.get('unique_index')

    if not food_unique_index or not food_unique_index.strip():
        raise ValueError("Invalid or empty unique_index")
    
    food_unique_index = int(food_unique_index)
    food_ref = db.collection('food').where('user_email', '==', user_email).where('unique_index', '==', food_unique_index).get()
    food_iter = iter(food_ref)
    food_doc = next(food_iter, None)

    if not food_doc:
       return redirect('/')
   
    food_data = food_doc.to_dict()
    
    if request.method == 'POST':
        print(request.form)
        new_food_name = request.form.get('foodName')
        new_cost = request.form.get('cost')

        food_data={
            'cost': new_cost,
            'foodName':new_food_name
        }
        print(food_data)
        user_food_data=[]
        food_doc.reference.update(food_data)
        user_food_data.append(food_data)

        flash("Food expense updated successfully!", "success")
        return redirect('/user_food_expenses')

    
    return render_template('user_food_expenses.html', user_food_data=user_food_data, food_data=food_data)

@app.route('/delete_food_expense/<int:unique_index>', methods=['GET'])
def delete_food_expense(unique_index):
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    
    # Find the food expense with the given unique index
    food_ref = db.collection('food').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
    food_iter = iter(food_ref)
    food_doc = next(food_iter, None)
    
    if not food_doc:
        # Food expense not found
        flash("Food expense not found.", "warning")
        return redirect('/user_food_expenses')
    
    try:
        # Delete the food expense from Firestore
        food_doc.reference.delete()
        flash("Food expense deleted successfully!", "success")
        
        # Fetch the updated list of food expenses for the logged-in user
        food_expenses = db.collection('food').where('user_email', '==', user_email).stream()
        
        # Create a list to store the food data
        user_food_data = []

        # Iterate through the food expenses and extract relevant information
        for food_doc in food_expenses:
            food_data = food_doc.to_dict()
            user_food_data.append({
                'foodName': food_data.get('foodName', ''),
                'cost': food_data.get('cost', ''),
                'unique_index': food_data.get('unique_index', '')
            })

    except Exception as e:
        # Handle any errors that may occur during deletion
        flash(f"An error occurred during food expense deletion: {str(e)}", "danger")
        return redirect('/user_food_expenses')
    
    # Pass the updated data to the template
    return render_template('user_food_expenses.html', user_food_data=user_food_data)
        

@app.route('/transport')
def transport():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']


    transport_ref = db.collection('transport').where('user_email', '==', user_email).stream()
    for transport_doc in transport_ref:
        transport_data = transport_doc.to_dict()

        if transport_data:
            return render_template('transport.html', transport_data=transport_data)
        else:
            flash("No Transport Expenses.", "warning")
            return redirect('/')


@app.route('/addtransport', methods=['GET', 'POST'])
def addtransport():
    if request.method == 'POST':
        user_email = session['user']
        transport_id = request.form.get('transport_id')
        transportName = request.form.get('transportName')
        cost = request.form.get('cost')

        try:
            # Check if foodName or cost is empty
            if not transportName or not cost:
                flash("Please fill in both Transport name and cost.", "warning")
                return render_template('transport.html')

            latest_transport = db.collection('transport').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
            latest_index = 0

            for transport_doc in latest_transport:
                latest_index = int(transport_doc.to_dict().get('unique_index', 0))

            unique_index = latest_index + 1
            current_date = datetime.now().strftime("%Y-%m-%d")
            # Original data
            transport_data = {
                'user_email': user_email,
                'transportName': transportName,
                'cost': cost,
                'date': current_date,  # Add the date field
                'unique_index': unique_index
            }

            # Get dynamic fields
            dynamic_fields = request.form.getlist('newField')
            print("Dynamic Fields:", dynamic_fields)

            # Process dynamic fields and add them to food_data
            for index, value in enumerate(dynamic_fields):
                transport_data[f'newField_{index + 1}'] = value

            if transport_id:
                # Editing an existing food expense
                transport_ref = db.collection('transport').document(transport_id)
                transport_ref.update(transport_data)
            else:
                # Adding a new food expense
                db.collection('transport').add(transport_data)

            flash("Transport expense saved successfully!", "success")
            return redirect('/user_transport_expenses')

        except Exception as e:
            flash(f"An error occurred during transport creation: {str(e)}", "warning")

    return render_template('transport.html')

@app.route('/user_transport_expenses')
def user_transport_expenses():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the list of food expenses for the logged-in user
    transport_expenses = db.collection('transport').where('user_email', '==', user_email).where('date', '==', current_date).stream()

    # Create a list to store the food data
    user_transport_data = []


    # Iterate through the food expenses and extract relevant information
    for transport_doc in transport_expenses:
        transport_data = transport_doc.to_dict()
        user_transport_data.append({
            'transportName': transport_data.get('transportName', ''),
            'cost': transport_data.get('cost', ''),
            'unique_index': transport_data.get('unique_index', ''),
            'date': transport_data.get('date', ''),
            'current_date': current_date
        })

    # Render user_food_expense.html
    return render_template('user_transport_expenses.html', user_transport_data=user_transport_data)

@app.route('/edit_transport_expenses', methods=['GET', 'POST'])
def edit_transport_expense():
    # Redirect to the home page if the user is not logged in
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    transport_unique_index = request.form.get('unique_index')

    if not transport_unique_index or not transport_unique_index.strip():
        raise ValueError("Invalid or empty unique_index")
    
    transport_unique_index = int(transport_unique_index)
    transport_ref = db.collection('transport').where('user_email', '==', user_email).where('unique_index', '==', transport_unique_index).get()
    transport_iter = iter(transport_ref)
    transport_doc = next(transport_iter, None)

    if not transport_doc:
       return redirect('/')
   
    transport_data = transport_doc.to_dict()
    
    if request.method == 'POST':
        print(request.form)
        new_transport_name = request.form.get('transportName')
        new_cost = request.form.get('cost')

        transport_data={
            'cost': new_cost,
            'transportName':new_transport_name
        }
        print(transport_data)
        user_transport_data=[]
        transport_doc.reference.update(transport_data)
        user_transport_data.append(transport_data)

        flash("Transport expense updated successfully!", "success")
        return redirect('/user_transport_expenses')

    
    return render_template('user_transport_expenses.html', user_transport_data=user_transport_data, transport_data=transport_data)

@app.route('/delete_transport_expense/<int:unique_index>', methods=['GET'])
def delete_transport_expense(unique_index):
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    
    # Find the food expense with the given unique index
    transport_ref = db.collection('transport').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
    transport_iter = iter(transport_ref)
    transport_doc = next(transport_iter, None)
    
    if not transport_doc:
      
        flash("transport expense not found.", "warning")
        return redirect('/user_transport_expenses')
    
    try:
        
        transport_doc.reference.delete()
        flash("Transport expense deleted successfully!", "success")
      
        transport_expenses = db.collection('transport').where('user_email', '==', user_email).stream()
      
        user_transport_data = []
        for transport_doc in transport_expenses:
            transport_data = transport_doc.to_dict()
            user_transport_data.append({
                'transportName': transport_data.get('transportName', ''),
                'cost': transport_data.get('cost', ''),
                'unique_index': transport_data.get('unique_index', '')
            })

    except Exception as e:
        # Handle any errors that may occur during deletion
        flash(f"An error occurred during food expense deletion: {str(e)}", "danger")
        return redirect('/user_transport_expenses')
    
    # Pass the updated data to the template
    return render_template('user_transport_expenses.html', user_transport_data=user_transport_data)

@app.route('/income')
def income():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']


    income_ref = db.collection('income').where('user_email', '==', user_email).stream()
    for income_doc in income_ref:
        income_data = income_doc.to_dict()

        if income_data:
            return render_template('income.html', income_data=income_data)
        else:
            flash("No Income Expenses.", "warning")
            return redirect('/')

@app.route('/addincome', methods=['GET', 'POST'])
def addincome():
    if request.method == 'POST':
        user_email = session['user']
        income_id = request.form.get('income_id')
        incomeName = request.form.get('incomeName')
        cost = request.form.get('cost')

        try:
            # Check if foodName or cost is empty
            if not incomeName or not cost:
                flash("Please fill in both income name and cost.", "warning")
                return render_template('income.html')

            latest_income = db.collection('income').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
            latest_index = 0

            for income_doc in latest_income:
                latest_index = int(income_doc.to_dict().get('unique_index', 0))

            unique_index = latest_index + 1
            current_date = datetime.now().strftime("%Y-%m-%d")

            # Original data
            income_data = {
                'user_email': user_email,
                'incomeName': incomeName,
                'cost': cost,
                'date': current_date,  # Add the date field
                'unique_index': unique_index
            }

            # Get dynamic fields
            dynamic_fields = request.form.getlist('newField')
            print("Dynamic Fields:", dynamic_fields)

            # Process dynamic fields and add them to food_data
            for index, value in enumerate(dynamic_fields):
                income_data[f'newField_{index + 1}'] = value

            if income_id:
                # Editing an existing food expense
                income_ref = db.collection('income').document(income_id)
                income_ref.update(income_data)
            else:
                # Adding a new food expense
                db.collection('income').add(income_data)

            flash("Income expense saved successfully!", "success")
            return redirect('/user_income_expenses')

        except Exception as e:
            flash(f"An error occurred during food creation: {str(e)}", "warning")

    return render_template('income.html')

@app.route('/user_income_expenses')
def user_income_expenses():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the list of food expenses for the logged-in user
    income_expenses = db.collection('income').where('user_email', '==', user_email).where('date', '==', current_date).stream()

    # Create a list to store the food data
    user_income_data = []

    # Iterate through the food expenses and extract relevant information
    for income_doc in income_expenses:
        income_data = income_doc.to_dict()
        user_income_data.append({
            'incomeName': income_data.get('incomeName', ''),
            'cost': income_data.get('cost', ''),
            'unique_index': income_data.get('unique_index', ''),
            'date': income_data.get('date', ''),
            'current_date': current_date
        })

    # Render user_food_expense.html
    return render_template('user_income_expenses.html', user_income_data=user_income_data)

@app.route('/edit_income_expenses', methods=['GET', 'POST'])
def edit_income_expense():
    # Redirect to the home page if the user is not logged in
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    income_unique_index = request.form.get('unique_index')


    if not income_unique_index or not income_unique_index.strip():
        raise ValueError("Invalid or empty unique_index")
    
    income_unique_index = int(income_unique_index)
    income_ref = db.collection('income').where('user_email', '==', user_email).where('unique_index', '==', income_unique_index).get()
    income_iter = iter(income_ref)
    income_doc = next(income_iter, None)


    if not income_doc:
       return redirect('/')
   
    income_data = income_doc.to_dict()
    
    if request.method == 'POST':
        print(request.form)
        new_income_name = request.form.get('incomeName')
        new_cost = request.form.get('cost')

        income_data={
            'cost': new_cost,
            'incomeName':new_income_name
        }
        print(income_data)
        user_income_data=[]
        income_doc.reference.update(income_data)
        user_income_data.append(income_data)

        flash("income expense updated successfully!", "success")
        return redirect('/user_income_expenses')

    
    return render_template('user_income_expenses.html', user_income_data=user_income_data, income_data=income_data)

@app.route('/delete_income_expense/<int:unique_index>', methods=['GET'])
def delete_income_expense(unique_index):
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    
    # Find the food expense with the given unique index
    income_ref = db.collection('income').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
    income_iter = iter(income_ref)
    income_doc = next(income_iter, None)
    
    if not income_doc:
        # Food expense not found
        flash("income expense not found.", "warning")
        return redirect('/user_income_expenses')
    
    try:
        # Delete the food expense from Firestore
        income_doc.reference.delete()
        flash("income expense deleted successfully!", "success")
        
        # Fetch the updated list of food expenses for the logged-in user
        income_expenses = db.collection('income').where('user_email', '==', user_email).stream()
        
        # Create a list to store the food data
        user_income_data = []

        # Iterate through the food expenses and extract relevant information
        for income_doc in income_expenses:
            income_data = income_doc.to_dict()
            user_income_data.append({
                'incomeName': income_data.get('incomeName', ''),
                'cost': income_data.get('cost', ''),
                'unique_index': income_data.get('unique_index', '')
            })

    except Exception as e:
        # Handle any errors that may occur during deletion
        flash(f"An error occurred during food expense deletion: {str(e)}", "danger")
        return redirect('/user_income_expenses')
    
    # Pass the updated data to the template
    return render_template('user_income_expenses.html', user_income_data=user_income_data)
        

@app.route('/investment')
def investment():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']


    investment_ref = db.collection('investment').where('user_email', '==', user_email).stream()
    for investment_doc in investment_ref:
        investment_data = investment_doc.to_dict()

        if investment_data:
            return render_template('investment.html', investment_data=investment_data)
        else:
            flash("No investment Expenses.", "warning")
            return redirect('/')


@app.route('/addinvestment', methods=['GET', 'POST'])
def addinvestment():
    if request.method == 'POST':
        user_email = session['user']
        investment_id = request.form.get('investment_id')
        investmentName = request.form.get('investmentName')
        cost = request.form.get('cost')

        try:
            # Check if foodName or cost is empty
            if not investmentName or not cost:
                flash("Please fill in both investment name and cost.", "warning")
                return render_template('investment.html')

            latest_investment = db.collection('investment').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
            latest_index = 0

            for investment_doc in latest_investment:
                latest_index = int(investment_doc.to_dict().get('unique_index', 0))

            unique_index = latest_index + 1
            current_date = datetime.now().strftime("%Y-%m-%d")
            # Original data
            investment_data = {
                'user_email': user_email,
                'investmentName': investmentName,
                'cost': cost,
                'date': current_date,  # Add the date field
                'unique_index': unique_index
            }

            # Get dynamic fields
            dynamic_fields = request.form.getlist('newField')
            print("Dynamic Fields:", dynamic_fields)

            # Process dynamic fields and add them to food_data
            for index, value in enumerate(dynamic_fields):
                investment_data[f'newField_{index + 1}'] = value

            if investment_id:
                # Editing an existing food expense
                investment_ref = db.collection('investment').document(investment_id)
                investment_ref.update(investment_data)
            else:
                # Adding a new food expense
                db.collection('investment').add(investment_data)

            flash("investment expense saved successfully!", "success")
            return redirect('/user_investment_expenses')

        except Exception as e:
            flash(f"An error occurred during investment creation: {str(e)}", "warning")

    return render_template('investment.html')

@app.route('/user_investment_expenses')
def user_investment_expenses():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the list of food expenses for the logged-in user
    investment_expenses = db.collection('investment').where('user_email', '==', user_email).where('date', '==', current_date).stream()

    # Create a list to store the food data
    user_investment_data = []

    # Iterate through the food expenses and extract relevant information
    for investment_doc in investment_expenses:
        investment_data = investment_doc.to_dict()
        user_investment_data.append({
            'investmentName': investment_data.get('investmentName', ''),
            'cost': investment_data.get('cost', ''),
            'unique_index': investment_data.get('unique_index', ''),
            'date': investment_data.get('date', ''),
            'current_date': current_date
        })
        
    return render_template('user_investment_expenses.html',  user_investment_data=user_investment_data)

@app.route('/edit_investment_expenses', methods=['GET', 'POST'])
def edit_investment_expense():
    # Redirect to the home page if the user is not logged in
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    investment_unique_index = request.form.get('unique_index')

    if not investment_unique_index or not investment_unique_index.strip():
        raise ValueError("Invalid or empty unique_index")
    
    investment_unique_index = int(investment_unique_index)
    investment_ref = db.collection('investment').where('user_email', '==', user_email).where('unique_index', '==', investment_unique_index).get()
    investment_iter = iter(investment_ref)
    investment_doc = next(investment_iter, None)

    if not investment_doc:
       return redirect('/')
   
    investment_data = investment_doc.to_dict()
    
    if request.method == 'POST':
        print(request.form)
        new_investment_name = request.form.get('investmentName')
        new_cost = request.form.get('cost')

        investment_data={
            'cost': new_cost,
            'investmentName':new_investment_name
        }
        print(investment_data)
        user_investment_data=[]
        investment_doc.reference.update(investment_data)
        user_investment_data.append(investment_data)

        flash("investment expense updated successfully!", "success")
        return redirect('/user_investment_expenses')

    
    return render_template('user_investment_expenses.html', user_investment_data=user_investment_data, investment_data=investment_data)

@app.route('/delete_investment_expense/<int:unique_index>', methods=['GET'])
def delete_investment_expense(unique_index):
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    
    # Find the food expense with the given unique index
    investment_ref = db.collection('investment').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
    investment_iter = iter(investment_ref)
    investment_doc = next(investment_iter, None)
    
    if not investment_doc:
      
        flash("investment expense not found.", "warning")
        return redirect('/user_investment_expenses')
    
    try:
        
        investment_doc.reference.delete()
        flash("investment expense deleted successfully!", "success")
      
        investment_expenses = db.collection('investment').where('user_email', '==', user_email).stream()
      
        user_investment_data = []
        for investment_doc in investment_expenses:
            investment_data = investment_doc.to_dict()
            user_investment_data.append({
                'investmentName': investment_data.get('investmentName', ''),
                'cost': investment_data.get('cost', ''),
                'unique_index': investment_data.get('unique_index', '')
            })

    except Exception as e:
        # Handle any errors that may occur during deletion
        flash(f"An error occurred during food expense deletion: {str(e)}", "danger")
        return redirect('/user_investment_expenses')
    
    # Pass the updated data to the template
    return render_template('user_investment_expenses.html', user_investment_data=user_investment_data)

@app.route('/investmentReturns')
def investmentReturns():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']


    investmentReturns_ref = db.collection('investmentReturns').where('user_email', '==', user_email).stream()
    for investmentReturns_doc in investmentReturns_ref:
        investmentReturns_data = investmentReturns_doc.to_dict()

        if investmentReturns_data:
            return render_template('investmentReturns.html', investmentReturns_data=investmentReturns_data)
        else:
            flash("No investment Returns.", "warning")
            return redirect('/')

@app.route('/addinvestmentReturns', methods=['GET', 'POST'])
def addinvestmentReturns():
    if request.method == 'POST':
        user_email = session['user']
        investmentReturns_id = request.form.get('investmentReturns_id')
        investmentReturnsName = request.form.get('investmentReturnsName')
        cost = request.form.get('cost')

        try:
            # Check if foodName or cost is empty
            if not investmentReturnsName or not cost:
                flash("Please fill in both income name and cost.", "warning")
                return render_template('investmentReturns.html')

            latest_investmentReturns = db.collection('investmentReturns').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
            latest_index = 0

            for investmentReturns_doc in latest_investmentReturns:
                latest_index = int(investmentReturns_doc.to_dict().get('unique_index', 0))

            unique_index = latest_index + 1
            current_date = datetime.now().strftime("%Y-%m-%d")
            # Original data
            investmentReturns_data = {
                'user_email': user_email,
                'investmentReturnsName': investmentReturnsName,
                'cost': cost,
                'date': current_date,  # Add the date field
                'unique_index': unique_index
            }

            # Get dynamic fields
            dynamic_fields = request.form.getlist('newField')
            print("Dynamic Fields:", dynamic_fields)

            # Process dynamic fields and add them to food_data
            for index, value in enumerate(dynamic_fields):
                investmentReturns_data[f'newField_{index + 1}'] = value

            if investmentReturns_id:
                # Editing an existing food expense
                investmentReturns_ref = db.collection('investmentReturns').document(investmentReturns_id)
                investmentReturns_ref.update(investmentReturns_data)
            else:
                # Adding a new food expense
                db.collection('investmentReturns').add(investmentReturns_data)

            flash("Investment Returns saved successfully!", "success")
            return redirect('/user_investment_returns')

        except Exception as e:
            flash(f"An error occurred during food creation: {str(e)}", "warning")

    return render_template('investmentReturns.html')

@app.route('/user_investment_returns')
def user_investment_returns():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the list of food expenses for the logged-in user
    investment_returns = db.collection('investmentReturns').where('user_email', '==', user_email).where('date', '==', current_date).stream()

    # Create a list to store the food data
    user_investmentReturns_data = []

    # Iterate through the food expenses and extract relevant information
    for investmentReturns_doc in investment_returns:
        investmentReturns_data = investmentReturns_doc.to_dict()
        user_investmentReturns_data.append({
            'investmentReturnsName': investmentReturns_data.get('investmentReturnsName', ''),
            'cost': investmentReturns_data.get('cost', ''),
            'unique_index': investmentReturns_data.get('unique_index', ''),
            'date': investmentReturns_data.get('date', ''),
            'current_date': current_date
        })

    # Render user_food_expense.html
    return render_template('user_investment_returns.html', user_investmentReturns_data=user_investmentReturns_data)

@app.route('/edit_investment_returns', methods=['GET', 'POST'])
def edit_investment_returns():
    # Redirect to the home page if the user is not logged in
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    investmentReturns_unique_index = request.form.get('unique_index')


    if not investmentReturns_unique_index or not investmentReturns_unique_index.strip():
        raise ValueError("Invalid or empty unique_index")
    
    investmentReturns_unique_index = int(investmentReturns_unique_index)
    investmentReturns_ref = db.collection('investmentReturns').where('user_email', '==', user_email).where('unique_index', '==', investmentReturns_unique_index).get()
    investmentReturns_iter = iter(investmentReturns_ref)
    investmentReturns_doc = next(investmentReturns_iter, None)


    if not investmentReturns_doc:
       return redirect('/')
   
    investmentReturns_data = investmentReturns_doc.to_dict()
    
    if request.method == 'POST':
        print(request.form)
        new_investmentReturns_name = request.form.get('investmentReturnsName')
        new_cost = request.form.get('cost')

        investmentReturns_data={
            'cost': new_cost,
            'investmentReturnsName':new_investmentReturns_name
        }
        print(investmentReturns_data)
        user_investmentReturns_data=[]
        investmentReturns_doc.reference.update(investmentReturns_data)
        user_investmentReturns_data.append(investmentReturns_data)

        flash("investment returns updated successfully!", "success")
        return redirect('/user_investment_returns')

    
    return render_template('user_investment_returns.html', user_investmentReturns_data=user_investmentReturns_data, investmentReturns_data=investmentReturns_data)

@app.route('/delete_investment_returns/<int:unique_index>', methods=['GET'])
def delete_investment_returns(unique_index):
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    
    # Find the food expense with the given unique index
    investmentReturns_ref = db.collection('investmentReturns').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
    investmentReturns_iter = iter(investmentReturns_ref)
    investmentReturns_doc = next(investmentReturns_iter, None)
    
    if not investmentReturns_doc:
        # Food expense not found
        flash("investment returns not found.", "warning")
        return redirect('/user_investment_returns')
    
    try:
        # Delete the food expense from Firestore
        investmentReturns_doc.reference.delete()
        flash("investment returns deleted successfully!", "success")
        
        # Fetch the updated list of food expenses for the logged-in user
        investment_returns = db.collection('investmentReturns').where('user_email', '==', user_email).stream()
        
        # Create a list to store the food data
        user_investmentReturns_data = []

        # Iterate through the food expenses and extract relevant information
        for investmentReturns_doc in investment_returns:
            investmentReturns_data = investmentReturns_doc.to_dict()
            user_investmentReturns_data.append({
                'investmentReturnsName': investmentReturns_data.get('investmentReturnsName', ''),
                'cost': investmentReturns_data.get('cost', ''),
                'unique_index': investmentReturns_data.get('unique_index', '')
            })

    except Exception as e:
        # Handle any errors that may occur during deletion
        flash(f"An error occurred during food expense deletion: {str(e)}", "danger")
        return redirect('/user_investments_returns')
    
    # Pass the updated data to the template
    return render_template('user_investment_returns.html', user_investmentReturns_data=user_investmentReturns_data)
        



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
    
# @app.route('/openai', methods=['POST'])

if __name__ == '__main__':
    app.run(debug=True)