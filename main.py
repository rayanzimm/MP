from flask import Flask, session, render_template, request, redirect, flash, url_for , make_response, send_file
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
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
from datetime import datetime, timedelta
import random
from openai import OpenAI
import openai
from fpdf import FPDF

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
cred = credentials.Certificate(r'D:\Microsoft VS Code\MP\MP\src\finsaver3-firebase-adminsdk-udjjx-b479ad6c2d.json')
firebase_admin.initialize_app(cred, {'projectId': 'finsaver3'})
db = firestore.client()

app.secret_key = 'secret'



# Function to send daily reminder email

# Flask-Mail configurations
# Outlook SMTP server details
# app.config['MAIL_SERVER'] = 'smtp.office365.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USE_SSL'] = False
# app.config['MAIL_USERNAME'] = 'finsaver@outlook.com'  # Replace with your Outlook email address
# app.config['MAIL_PASSWORD'] = 'fintech2024'  # Replace with your Outlook email password
# app.config['MAIL_DEFAULT_SENDER'] = 'finsaver@outlook.com'  # Replace with your Outlook email address
# # Initialize Flask-Mail
# mail = Mail(app)

# scheduler = BackgroundScheduler()

# def send_daily_reminder(user_email):
#     try:
#         print(user_email)

#         if user_email:
#             with app.app_context():
#                 msg = Message('Daily Expense Reminder', recipients=[user_email])
#                 msg.body = 'Don\'t forget to upload your daily Budget & Expenses'
#                 msg.html = '<p>Don\'t forget to upload your daily Budget & Expenses</p>'

#                 mail.send(msg)

#                 print("Daily reminder email sent successfully")
#         else:
#             print("User email not found. Unable to send reminder.")

#     except Exception as e:
#         print(f"Error sending email: {str(e)}")




# @app.route('/store_user_email', methods=['POST'])
# def store_user_email():
#     try:
#         data = request.get_json()
#         user_email = data.get('email')

#         # Now you can use user_email in your send_daily_reminder function
#         send_daily_reminder(user_email)

#         return "Email received and processed successfully"

#     except Exception as e:
#         return f"Error storing email: {str(e)}"

# Function to retrieve the user's email for the daily reminder
# def get_user_email_for_daily_reminder():
#     try:
#         user_email = session['user']
#         # Fetch any user's email from the database
#         user_ref = db.collection('users').where('email', '==', user_email).limit(1).stream()

#         for user_doc in user_ref:
#             user_data = user_doc.to_dict()
#             return user_data.get('email')

#     except Exception as e:
#         # Handle any exceptions during database query
#         print(f"Error fetching user email: {str(e)}")
#         return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from flask import render_template

@app.route('/progress')
def progress():
    if 'user' not in session:
        return redirect('/')
    
    email = session['user']
    user_ref = db.collection('users').where('email', '==', email).limit(1).get()

    if not user_ref:
        flash("User not found.", "danger")
        return redirect('/')
        
    user_doc = user_ref[0]
    user_data = user_doc.to_dict()
    
    # Retrieve loginDays from user_data
    login_days = user_data.get('loginDays', 1)

    # Define the maximum number of steps (assuming 7 steps for the progress bar)
    max_steps = 7

    # Calculate the progress width based on loginDays
    progress_width = (login_days / max_steps) * 100

    # Create a list of steps for the progress bar
    steps = [{"step_number": i + 1, "active": i < login_days} for i in range(max_steps)]

    return render_template('progress_bar.html', loginDays=login_days, progressWidth=progress_width, steps=steps)
        

@app.route('/', methods=['POST', 'GET'])
def index():
    if 'user' in session:
        user_email = session['user']
        user_ref = db.collection('users').where('email', '==', user_email).limit(1).get()
        current_date = datetime.now().strftime("%Y-%m-%d")

        if not user_ref:
            flash("User not found.", "danger")
            return redirect('/')
        
        user_doc = user_ref[0]
        user_data = user_doc.to_dict()
        update_login_rewards(user_email, user_data, user_doc)
        coins=user_data.get('coins', 0)
        total_food_cost = fetch_total_cost('Food', user_email, current_date)
        total_transport_cost = fetch_total_cost('Transport', user_email, current_date)
        total_budget_cost = fetch_total_cost('Budget', user_email, current_date)
        total_investment_cost = fetch_total_cost('Investment', user_email, current_date)
        total_investmentReturns_cost = fetch_total_cost('Investment Returns', user_email, current_date)



        total_expense = total_food_cost + total_transport_cost + total_investment_cost - total_investmentReturns_cost
        total_savings = total_budget_cost - total_expense

        
        return render_template('home.html', email=user_email, coins=coins, total_food_cost=total_food_cost,
                           total_transport_cost=total_transport_cost,
                           total_budget_cost=total_budget_cost,
                           total_investment_cost=total_investment_cost,
                           total_investmentReturns_cost=total_investmentReturns_cost,
                           total_savings=total_savings)
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = email

            user_ref = db.collection('users').where('email', '==', email).limit(1).get()
            if not user_ref:
                flash("User not found.", "danger")
                return redirect('/')
            
            user_doc = user_ref[0]
            user_data = user_doc.to_dict()
            update_login_rewards(email, user_data, user_doc)
            coins=user_data.get('coins', 0)
            print(coins)

            return render_template('home.html', email=email, coins=coins)
        except:
            flash("Invalid email or password.", "warning")
    return render_template('login.html')

def update_login_rewards(user_email, user_data, user_doc):
    singapore_timezone = pytz.timezone('Asia/Singapore')
    current_datetime = datetime.now(singapore_timezone)
    current_date = current_datetime.strftime("%Y-%m-%d")

    # Update the 'lastLogin' field to today's date
    if user_data['lastLogin'] != current_datetime and current_datetime.hour >= 6:
        if current_datetime > user_data.get('nextRewardTime', datetime.min):
            if current_datetime.weekday() == 0:
                user_data['lastLogin'] = current_datetime
                user_data['loginDays'] = 1
                coins_rewarded = reward_coins(user_email, user_data['loginDays'])
                user_data['coins'] += coins_rewarded
                flash(f"Congratulations! You've been rewarded {coins_rewarded} coins.", "success")
                user_data['nextRewardTime'] = (current_datetime + timedelta(days=1)).replace(hour=6, minute=0, second=0)
            else:
                user_data['lastLogin'] = current_datetime
                user_data['loginDays'] += 1
                coins_rewarded = reward_coins(user_email, user_data['loginDays'])
                user_data['coins'] += coins_rewarded
                flash(f"Congratulations! You've been rewarded {coins_rewarded} coins.", "success")
                user_data['nextRewardTime'] = (current_datetime + timedelta(days=1)).replace(hour=6, minute=0, second=0)
        else:
            user_data['lastLogin'] = current_datetime
    else:
        user_data['lastLogin'] = current_datetime

    # Save the updated user document back to Firestore
    db.collection('users').document(user_doc.id).update(user_data)

def reward_coins(user_email, login_days):
    try:
    # Example: Reward 10 coins for the first day, and 5 additional coins for each subsequent day
        coins_to_reward = 10 + (login_days - 1) * 5
        
        return coins_to_reward
            
    except Exception as e:
        flash(f"Error updating coins: {str(e)}", "danger")

def fetch_total_cost(expense_type, user_email, current_date):
    total_cost = 0

    # Fetch the list of expenses for the given expense type and user
    expense_ref = db.collection(expense_type).where('user_email', '==', user_email).where('date', '==', current_date).stream()

    # Iterate through the expenses and calculate the total cost
    for expense_doc in expense_ref:
        expense_data = expense_doc.to_dict()
        total_cost += float(expense_data.get('cost', 0))

    return total_cost

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect('/')
    
    email = session['user']

    user_ref = db.collection('users').where('email', '==', email).limit(1).get()

    if not user_ref:
            flash("User not found.", "danger")
            return redirect('/')
            
    user_doc = user_ref[0]
    user_data = user_doc.to_dict()
    
    coins=user_data.get('coins', 0)
    savings_goal = float(user_data.get('savingsGoal', 0))

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the total cost for each expense type
    total_food_cost = fetch_total_cost('Food', user_email, current_date)
    total_transport_cost = fetch_total_cost('Transport', user_email, current_date)
    total_budget_cost = fetch_total_cost('Budget', user_email, current_date)
    total_investment_cost = fetch_total_cost('Investment', user_email, current_date)
    total_investmentReturns_cost = fetch_total_cost('Investment Returns', user_email, current_date)
    session['total_food_cost'] = total_food_cost
    session['total_transport_cost'] = total_transport_cost
    session['total_budget_cost'] = total_budget_cost
    session['total_investment_cost'] = total_investment_cost
    session['total_investmentReturns_cost'] = total_investmentReturns_cost


    total_expense = total_food_cost + total_transport_cost + total_investment_cost - total_investmentReturns_cost
    total_savings = float(total_budget_cost - total_expense)

    progress_percentage = (total_savings / savings_goal) * 100 if savings_goal > 0 else 0

    return render_template('home.html',
                           total_food_cost=total_food_cost,
                           total_transport_cost=total_transport_cost,
                           total_budget_cost=total_budget_cost,
                           total_investment_cost=total_investment_cost,
                           total_investmentReturns_cost=total_investmentReturns_cost,
                           total_savings=total_savings,
                           coins=coins,
                           savings_goal=savings_goal,
                           progress_percentage=progress_percentage)


def fetch_total_cost(expense_type, user_email, current_date):
    total_cost = 0

    # Fetch the list of expenses for the given expense type and user
    expense_ref = db.collection(expense_type).where('user_email', '==', user_email).where('date', '==', current_date).stream()

    # Iterate through the expenses and calculate the total cost
    for expense_doc in expense_ref:
        expense_data = expense_doc.to_dict()
        total_cost += float(expense_data.get('cost', 0))

    return total_cost

@app.route('/update_savings_goal', methods=['POST'])
def update_savings_goal():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    

    try:
        # Fetch the user document from Firestore
        user_ref = db.collection('users').where('email', '==', user_email).limit(1).get()

        if not user_ref:
            flash("User not found.", "danger")
            return redirect('/')

        user_doc = user_ref[0]
        user_data = user_doc.to_dict()

        # Update the 'savingsGoal' field
        if request.method == 'POST':
            new_savings_goal = request.form.get('savings_goal')
        
        user_data = {
            'savingsGoal': new_savings_goal
        }
        # Update user details in Firestore
        user_doc.reference.update(user_data)
        flash("Savings goal set successfully!", "success")
        

    except Exception as e:
        flash(f"Error updating savings goal: {str(e)}", "danger")

    return redirect('/home')

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    
    all_expenses = fetch_all_expenses(user_email)

    # Organize expenses by date
    all_expenses_by_date = organize_expenses_by_date(all_expenses)

    # Calculate total expenses for each date
    total_by_date = calculate_total_by_date(all_expenses_by_date)


    return render_template('history.html',
                           all_expenses_by_date=all_expenses_by_date,
                           total_by_date=total_by_date)

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
        expense_data['category'] = expense_type
        expenses.append(expense_data)

    return expenses

def fetch_all_expenses(user_email):
    all_expenses = []

    # Fetch expenses for all categories
    for expense_type in ['Budget', 'Investment', 'Food', 'Transport', 'Investment Returns']:
        expenses = fetch_expenses_by_type(expense_type, user_email)
        all_expenses.extend(expenses)

    return all_expenses

def format_date(value, format='%d %B %Y'):
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d')  # Convert string to datetime object
    return value.strftime(format)

app.jinja_env.filters['format_date'] = format_date


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
        if 'photo' in request.form:
            # Use the default profile picture path if not provided in the form
            photo_path = request.form.get('photo', "static\assets\img\defaultprofile.jpg")
        else:
            # Default profile picture path
            photo_path = "static\assets\img\defaultprofile.jpg"

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
                'photo_path': photo_path,
                'lastLogin': '',
                'loginDays': 0,
                'coins': 0,
                'nextRewardTime': datetime.min,
                'savingsGoal': 0
            }
            db.collection('users').add(user_data)

            session['user'] = email
            flash("Registration successful!", "success")
            return render_template('login.html')  # Redirect to the login page after successful registration

        except Exception as e:
            flash(f"An error occurred during user creation: {str(e)}", "warning")

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
        
        
        user_data={
            'address': new_address,
            'mobile': new_mobile,
            'firstName': new_firstName,
            'lastName': new_lastName,
            'dob': new_dob
        }

        if 'new_photo' in request.files:
            new_photo = request.files['new_photo']
            if new_photo.filename != '' and allowed_file(new_photo.filename):
                # Save the uploaded photo to the upload folder
                filename = secure_filename(new_photo.filename)
                full_path = "static/assets/img/" + filename
                new_photo.save(full_path)
                flash("New photo uploaded successfully!", "success")

                # Update user details in Firestore, including the new file path for the uploaded photo
                user_data['photo_path'] = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # Update user details in Firestore
        user_doc.reference.update(user_data)
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
                return redirect('/user_food_expenses')

            latest_food = db.collection('Food').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
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
                food_ref = db.collection('Food').document(food_id)
                food_ref.update(food_data)
            else:
                # Adding a new food expense
                db.collection('Food').add(food_data)

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
    food_expenses = db.collection('Food').where('user_email', '==', user_email).where('date', '==', current_date).stream()

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
    food_ref = db.collection('Food').where('user_email', '==', user_email).where('unique_index', '==', food_unique_index).get()
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
    food_ref = db.collection('Food').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
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
        food_expenses = db.collection('Food').where('user_email', '==', user_email).stream()
        
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
                return redirect('/user_transport_expenses')

            latest_transport = db.collection('Transport').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
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
                transport_ref = db.collection('Transport').document(transport_id)
                transport_ref.update(transport_data)
            else:
                # Adding a new food expense
                db.collection('Transport').add(transport_data)

            flash("Transport expense saved successfully!", "success")
            return redirect('/user_transport_expenses')

        except Exception as e:
            flash(f"An error occurred during transport creation: {str(e)}", "warning")

    return render_template('user_transport_expenses.html')

@app.route('/user_transport_expenses')
def user_transport_expenses():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the list of food expenses for the logged-in user
    transport_expenses = db.collection('Transport').where('user_email', '==', user_email).where('date', '==', current_date).stream()

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
    transport_ref = db.collection('Transport').where('user_email', '==', user_email).where('unique_index', '==', transport_unique_index).get()
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
    transport_ref = db.collection('Transport').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
    transport_iter = iter(transport_ref)
    transport_doc = next(transport_iter, None)
    
    if not transport_doc:
      
        flash("transport expense not found.", "warning")
        return redirect('/user_transport_expenses')
    
    try:
        
        transport_doc.reference.delete()
        flash("Transport expense deleted successfully!", "success")
      
        transport_expenses = db.collection('Transport').where('user_email', '==', user_email).stream()
      
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


@app.route('/copy_previous_budget', methods=['POST'])
def copy_previous_budget():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch all the budget expenses for the logged-in user on the previous date
    previous_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    previous_budget_expenses = db.collection('Budget').where('user_email', '==', user_email).where('date', '==', previous_date).stream()

    try:
        # Copy all the budget data from the previous date to today's date
        for budget_doc in previous_budget_expenses:
            budget_data = budget_doc.to_dict()

            # Generate a new unique index for the copied entry
            new_unique_index = get_new_unique_index()

            # Update the budget data with the new date and unique index
            budget_data['date'] = current_date
            budget_data['unique_index'] = new_unique_index

            # Add the copied budget data to today's date
            db.collection('Budget').add(budget_data)

        flash("All budget data copied successfully from the previous day!", "success")
    except Exception as e:
        flash(f"An error occurred during budget data copying: {str(e)}", "warning")

    return redirect('/user_budget')

def get_new_unique_index():
    # You can implement your logic here to generate a new unique index
    # This can be a random number, a counter, or any other mechanism
    # Ensure that the generated index is unique within the collection
    # For simplicity, let's use a random number between 1 and 1000 in this example
    return random.randint(1, 1000)


@app.route('/addbudget', methods=['GET', 'POST'])
def addbudget():
    if request.method == 'POST':
        user_email = session['user']
        budget_id = request.form.get('budget_id')
        budgetName = request.form.get('budgetName')
        cost = request.form.get('cost')

        try:
            # Check if foodName or cost is empty
            if not budgetName or not cost:
                flash("Please fill in both budget name and cost.", "warning")
                return redirect('/user_budget')

            latest_budget = db.collection('Budget').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
            latest_index = 0

            for budget_doc in latest_budget:
                latest_index = int(budget_doc.to_dict().get('unique_index', 0))

            unique_index = latest_index + 1
            current_date = datetime.now().strftime("%Y-%m-%d")

            # Original data
            budget_data = {
                'user_email': user_email,
                'budgetName': budgetName,
                'cost': cost,
                'date': current_date,  # Add the date field
                'unique_index': unique_index
            }

            # Get dynamic fields
            dynamic_fields = request.form.getlist('newField')
            print("Dynamic Fields:", dynamic_fields)

            # Process dynamic fields and add them to food_data
            for index, value in enumerate(dynamic_fields):
                budget_data[f'newField_{index + 1}'] = value

            if budget_id:
                # Editing an existing food expense
                budget_ref = db.collection('Budget').document(budget_id)
                budget_ref.update(budget_data)
            else:
                # Adding a new food expense
                db.collection('Budget').add(budget_data)

            flash("budget expense saved successfully!", "success")
            return redirect('/user_budget')

        except Exception as e:
            flash(f"An error occurred during food creation: {str(e)}", "warning")

    return render_template('user_budget.html')

@app.route('/user_budget')
def user_budget_expenses():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the list of food expenses for the logged-in user
    budget_expenses = db.collection('Budget').where('user_email', '==', user_email).where('date', '==', current_date).stream()

    # Create a list to store the food data
    user_budget_data = []

    # Iterate through the food expenses and extract relevant information
    for budget_doc in budget_expenses:
        budget_data = budget_doc.to_dict()
        user_budget_data.append({
            'budgetName': budget_data.get('budgetName', ''),
            'cost': budget_data.get('cost', ''),
            'unique_index': budget_data.get('unique_index', ''),
            'date': budget_data.get('date', ''),
            'current_date': current_date
        })

    # Render user_food_expense.html
    return render_template('user_budget.html', user_budget_data=user_budget_data)

@app.route('/edit_budget', methods=['GET', 'POST'])
def edit_budget_expense():
    # Redirect to the home page if the user is not logged in
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    budget_unique_index = request.form.get('unique_index')


    if not budget_unique_index or not budget_unique_index.strip():
        raise ValueError("Invalid or empty unique_index")
    
    budget_unique_index = int(budget_unique_index)
    budget_ref = db.collection('Budget').where('user_email', '==', user_email).where('unique_index', '==', budget_unique_index).get()
    budget_iter = iter(budget_ref)
    budget_doc = next(budget_iter, None)


    if not budget_doc:
       return redirect('/')
   
    budget_data = budget_doc.to_dict()
    
    if request.method == 'POST':
        print(request.form)
        new_budget_name = request.form.get('budgetName')
        new_cost = request.form.get('cost')

        budget_data={
            'cost': new_cost,
            'budgetName':new_budget_name
        }
        print(budget_data)
        user_budget_data=[]
        budget_doc.reference.update(budget_data)
        user_budget_data.append(budget_data)

        flash("budget expense updated successfully!", "success")
        return redirect('/user_budget')

    
    return render_template('user_budget.html', user_budget_data=user_budget_data, budget_data=budget_data)

@app.route('/delete_budget/<int:unique_index>', methods=['GET'])
def delete_budget_expense(unique_index):
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    
    # Find the food expense with the given unique index
    budget_ref = db.collection('Budget').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
    budget_iter = iter(budget_ref)
    budget_doc = next(budget_iter, None)
    
    if not budget_doc:
        # Food expense not found
        flash("budget expense not found.", "warning")
        return redirect('/user_budget_expenses')
    
    try:
        # Delete the food expense from Firestore
        budget_doc.reference.delete()
        flash("budget expense deleted successfully!", "success")
        
        # Fetch the updated list of food expenses for the logged-in user
        budget_expenses = db.collection('Budget').where('user_email', '==', user_email).stream()
        
        # Create a list to store the food data
        user_budget_data = []

        # Iterate through the food expenses and extract relevant information
        for budget_doc in budget_expenses:
            budget_data = budget_doc.to_dict()
            user_budget_data.append({
                'budgetName': budget_data.get('budgetName', ''),
                'cost': budget_data.get('cost', ''),
                'unique_index': budget_data.get('unique_index', '')
            })

    except Exception as e:
        # Handle any errors that may occur during deletion
        flash(f"An error occurred during food expense deletion: {str(e)}", "danger")
        return redirect('/user_budget_expenses')
    
    # Pass the updated data to the template
    return render_template('user_budget.html', user_budget_data=user_budget_data)
        
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
                return redirect('/user_investment_expenses')

            latest_investment = db.collection('Investment').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
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
                investment_ref = db.collection('Investment').document(investment_id)
                investment_ref.update(investment_data)
            else:
                # Adding a new food expense
                db.collection('Investment').add(investment_data)

            flash("investment expense saved successfully!", "success")
            return redirect('/user_investment_expenses')

        except Exception as e:
            flash(f"An error occurred during investment creation: {str(e)}", "warning")

    return render_template('user_investment_expenses.html')

@app.route('/user_investment_expenses')
def user_investment_expenses():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the list of food expenses for the logged-in user
    investment_expenses = db.collection('Investment').where('user_email', '==', user_email).where('date', '==', current_date).stream()

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
    investment_ref = db.collection('Investment').where('user_email', '==', user_email).where('unique_index', '==', investment_unique_index).get()
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
    investment_ref = db.collection('Investment').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
    investment_iter = iter(investment_ref)
    investment_doc = next(investment_iter, None)
    
    if not investment_doc:
      
        flash("investment expense not found.", "warning")
        return redirect('/user_investment_expenses')
    
    try:
        
        investment_doc.reference.delete()
        flash("investment expense deleted successfully!", "success")
      
        investment_expenses = db.collection('Investment').where('user_email', '==', user_email).stream()
      
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
                flash("Please fill in both budget name and cost.", "warning")
                return redirect('/user_investment_returns')

            latest_investmentReturns = db.collection('Investment Returns').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
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
                investmentReturns_ref = db.collection('Investment Returns').document(investmentReturns_id)
                investmentReturns_ref.update(investmentReturns_data)
            else:
                # Adding a new food expense
                db.collection('Investment Returns').add(investmentReturns_data)

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
    investment_returns = db.collection('Investment Returns').where('user_email', '==', user_email).where('date', '==', current_date).stream()

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
    investmentReturns_ref = db.collection('Investment Returns').where('user_email', '==', user_email).where('unique_index', '==', investmentReturns_unique_index).get()
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
    investmentReturns_ref = db.collection('Investment Returns').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
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
        investment_returns = db.collection('Investment Returns').where('user_email', '==', user_email).stream()
        
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
        
@app.route('/analysis')
def analysis():
    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")

    total_food_cost = fetch_total_cost('Food', user_email, current_date)
    total_transport_cost = fetch_total_cost('Transport', user_email, current_date)
    total_budget_cost = fetch_total_cost('Budget', user_email, current_date)
    total_investment_cost = fetch_total_cost('Investment', user_email, current_date)
    total_investmentReturns_cost = fetch_total_cost('Investment Returns', user_email, current_date)

    # Calculate total expense including food, transport, and investment costs
    total_expense = total_food_cost + total_transport_cost + total_investment_cost
    total_savings = float(total_budget_cost - total_expense)

    # Store values in session
    session['total_food_cost'] = total_food_cost
    session['total_transport_cost'] = total_transport_cost
    session['total_budget_cost'] = total_budget_cost
    session['total_investment_cost'] = total_investment_cost
    session['total_investmentReturns_cost'] = total_investmentReturns_cost

    return render_template('analysis.html',
                           total_food_cost=total_food_cost,
                           total_transport_cost=total_transport_cost,
                           total_budget_cost=total_budget_cost,
                           total_investment_cost=total_investment_cost,
                           total_investmentReturns_cost=total_investmentReturns_cost,
                           total_expense=total_expense,  # Include total_expense in the template
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

# @app.route('/analysis', methods=['GET', 'POST'])
# def analysis():
#     if request.method == 'POST':
#         # Get user inputs from the form
#         budget = float(request.form['budget'])
#         food_expense = float(request.form['food_expense'])
#         transport_expense = float(request.form['transport_expense'])

#         # Generate a prompt for OpenAI based on user inputs
#         prompt = f"Given a budget of {budget}, food expense of {food_expense}, and transport expense of {transport_expense}, analyze the impact on savings."

#         # Use OpenAI API to get analysis
#         analysis_result = openai_analysis(prompt)

#         return render_template('analysis.html', prompt=prompt, analysis_result=analysis_result)

#     return render_template('analysis.html', prompt="something")

def openai_analysis(prompt):
    try:
                # Call OpenAI API to generate analysis
        response = openai.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gpt-3.5-turbo",
        )
        print (response)


        # # Extract the generated text from OpenAI's response
        analysis_result = response.choices[0].message.content

        return analysis_result

    except Exception as e:
        # Handle any errors that may occur during API call
        return f"Error: {str(e)}"
    
@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    # Retrieve the data needed for the PDF
    recommendations = request.form.get('recommendations')

    # Generate PDF
    pdf = FPDF('P', 'mm', 'Letter')
    pdf.add_page()
    pdf.set_font('helvetica', size=12)
    pdf.cell(40, 10, "Monthly Analysis Report")
    pdf.cell(80, 10, recommendations)

    # Construct the path to the user's downloads folder
    downloads_folder = os.path.expanduser("~" + os.sep + "Downloads")
    pdf_path = os.path.join(downloads_folder, 'finsaver_analysis.pdf')

    # Save the PDF to the downloads folder
    pdf.output(pdf_path)

    # Return the PDF file directly
    return send_file(pdf_path, as_attachment=True, download_name='finsaver_analysis.pdf')


@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route("/graph")
def graph():
    # Generate the figure **without using pyplot**.
    fig = Figure()
    ax = fig.subplots()
    ax.plot([1, 2])
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")
    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")

    return render_template('home.html', image = "data:image/png;base64," + data)


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