from flask import Flask, session, render_template, request, redirect, flash, url_for , make_response, send_file, jsonify
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
from collections import defaultdict
from fpdf import FPDF
from collections import defaultdict
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import base64
from io import BytesIO
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from flask import send_file

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
cred = credentials.Certificate(r'C:\Users\S531FL-BQ559T\OneDrive\Documents\MP\Project\MP\src\finsaver3-firebase-adminsdk-udjjx-b479ad6c2d.json')
firebase_admin.initialize_app(cred, {'projectId': 'finsaver3'})
db = firestore.client()

app.secret_key = 'secret'

app.config['MAIL_SERVER'] = 'smtp.office365.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'finsaver@outlook.com'  # Replace with your Outlook email address
app.config['MAIL_PASSWORD'] = 'fintech2024'  # Replace with your Outlook email password
app.config['MAIL_DEFAULT_SENDER'] = 'finsaver@outlook.com'  # Replace with your Outlook email address
# Initialize Flask-Mail
mail = Mail(app)

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

@app.route('/about', methods=['GET', 'POST'])
def about():
    if request.method == 'POST':

        name = request.form['name']
        client_email = request.form['email']
        message_content = request.form['message']

        print(f"Name: {name}, Client Email: {client_email}, Message: {message_content}")

        # Send email
        send_email(name, client_email, message_content)

        return render_template('about.html', show_dialog=True)

    return render_template('about.html', show_dialog=False)

def send_email(name, client_email, message_content):
    # Create a message object
    msg = Message('New Contact Form Submission from Finsaver', sender='finsaver@outlook.com', recipients=['finsaver@outlook.com'])

    # Set the email body
    msg.body = f"Name: {name}\nClient Email: {client_email}\nMessage: {message_content}"

    # Send the email
    mail.send(msg)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
        
@app.route('/', methods=['POST', 'GET'])
def index():
    if 'user' in session:
        user_email = session['user']
        user_ref = db.collection('users').where('email', '==', user_email).limit(1).get()


        if not user_ref:
            flash("User not found.", "danger")
            return redirect('/')
        
        user_doc = user_ref[0]
        user_data = user_doc.to_dict()

        return redirect('/analysis')
    
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

            return redirect('/analysis')
        except Exception as e:
            
            flash(f"Error logging in: {str(e)}", "warning")
    return render_template('login.html')

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
    current_date = datetime.now().strftime("%Y-%m-%d")
    update_login_rewards(email, user_data, user_doc)
    coins=user_data.get('coins', 0)
    savings_goal = float(user_data.get('savingsGoal', 0))

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the total cost for each expense type
    total_food_cost_daily = fetch_total_cost('Food', user_email, current_date)
    total_transport_cost_daily = fetch_total_cost('Transport', user_email, current_date)
    total_budget_cost_daily = fetch_total_cost('Budget', user_email, current_date)
    total_others_cost_daily = fetch_total_cost('Others', user_email, current_date)
    
    session['total_food_cost_daily'] = total_food_cost_daily
    session['total_transport_cost_daily'] = total_transport_cost_daily
    session['total_budget_cost_daily'] = total_budget_cost_daily
    session['total_others_cost_daily'] = total_others_cost_daily

    total_food_cost = fetch_total_cost_analysis('Food', user_email)
    total_transport_cost = fetch_total_cost_analysis('Transport', user_email)
    total_budget_cost = fetch_total_cost_analysis('Budget', user_email)

    total_others_cost = fetch_total_cost_analysis('Others', user_email)
    # Calculate total expense including food, transport, and investment costs
    
    # Store values in session
    session['total_food_cost'] = total_food_cost
    session['total_transport_cost'] = total_transport_cost
    session['total_budget_cost'] = total_budget_cost

    session['total_others_cost'] = total_others_cost

    # Fetch all investment records for the user
    investment_ref = db.collection('Investment').where('user_email', '==', user_email).where('status', '==', 'active').stream()

    # Dictionary to store the latest prices for each ticker
    total_values = defaultdict(float)
    initial_total_closing_prices = defaultdict(float)
    api = '1HEU5NM89I8H1AKX'

    for investment_doc in investment_ref:
        investment_data = investment_doc.to_dict()
        ticker = investment_data.get('ticker')
        quantity = int(investment_data.get('quantity'))
        if ticker and quantity:

            # Fetch the latest prices for each ticker
            url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval=1min&apikey={api}'
            response = requests.get(url)
            stockData = response.json()

            if 'Time Series (1min)' in stockData:
                lastRefreshed = stockData["Meta Data"]["3. Last Refreshed"]
                latestPrices = stockData["Time Series (1min)"][lastRefreshed]
                closingUSDPrice = latestPrices["4. close"]
                
                if closingUSDPrice:
                    # Convert to SGD if necessary
                    conversion_url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=SGD&apikey={api}"
                    conversion_response = requests.get(conversion_url)
                    conversion_data = conversion_response.json()
                    exchange_rate = float(conversion_data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
                    closingPrice = float(closingUSDPrice) * exchange_rate

                    total_value = quantity * closingPrice

                    # Update the total value for the investment
                    total_values[ticker] += total_value
        
        current_closing_price = investment_data.get('cost', 0)
        initial_total_closing_prices[ticker] += current_closing_price
    # Calculate the total closingPrice for all tickers
    total_investment_value = round(float(sum(total_values.values())), 2)
    initial_total_closing_price = round(float(sum(initial_total_closing_prices.values())), 2)
    value_difference = round(float((total_investment_value - initial_total_closing_price)), 2)
    value_difference_abs = abs(value_difference)

    sold_investment_ref = db.collection('Investment').where('user_email', '==', user_email).where('status', '==', 'sold').stream()

    total_investment_sold = 0

    for sold_investment_doc in sold_investment_ref:
        sold_investment_data = sold_investment_doc.to_dict()
        
        total_investment_sold += float(sold_investment_data.get('price_difference', 0))
    
    total_expense = total_food_cost + total_transport_cost + total_others_cost
    total_savings = float((total_budget_cost + total_investment_sold) - total_expense)
    session['total_investment_value'] = total_investment_value
    session['value_difference_abs'] =  value_difference_abs
    user_doc.reference.update({
            'totalSavings': total_savings
            })

    progress_percentage = (total_savings / savings_goal) * 100 if savings_goal > 0 else 0

    return render_template('home.html',
                           total_food_cost=total_food_cost,
                           total_transport_cost=total_transport_cost,
                           total_budget_cost=total_budget_cost,
                           total_others_cost=total_others_cost,
                           total_food_cost_daily=total_food_cost_daily,
                           total_transport_cost_daily=total_transport_cost_daily,
                           total_budget_cost_daily=total_budget_cost_daily,
                           total_others_cost_daily=total_others_cost_daily,
                           total_savings=total_savings,
                           coins=coins,
                           savings_goal=savings_goal,
                           progress_percentage=progress_percentage,
                           total_investment_value=total_investment_value,
                           value_difference=value_difference,
                           value_difference_abs=value_difference_abs, 
                           )


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
            new_savings_goal = float(request.form.get('savings_goal'))
        
        user_data = {
            'savingsGoal': new_savings_goal
        }
        # Update user details in Firestore
        user_doc.reference.update(user_data)
        flash("Savings goal set successfully!", "success")
        

    except Exception as e:
        flash(f"Error updating savings goal: {str(e)}", "danger")

    return redirect('/home')

@app.route('/shop', methods=['GET', 'POST'])
def shop():
    if 'user' not in session:
        return redirect('/')
    
    email = session['user']

    user_ref = db.collection('users').where('email', '==', email).limit(1).get()

    if not user_ref:
        flash("User not found.", "danger")
        return redirect('/')
            
    user_doc = user_ref[0]
    user_data = user_doc.to_dict()
    coins = user_data.get('coins', 0)
    login_days = user_data.get('loginDays', 0)

    shares_product_ref = db.collection('Products').where('type', '==', 'shares').stream()
    voucher_product_ref = db.collection('Products').where('type', '==', 'voucher').stream()
    accessory_product_ref = db.collection('Products').where('type', '==', 'accessory').stream()

    shares_product_data = []
    voucher_product_data = []
    accessory_product_data = []

    # Iterate through the food expenses and extract relevant information
    for shares_product_doc in sort_products_by_price(shares_product_ref):
        product_data = shares_product_doc.to_dict()
        shares_product_data.append({
            'description': product_data.get('description', ''),
            'image': product_data.get('image', ''),
            'name': product_data.get('name', ''),
            'price': product_data.get('price', 0),
            'product_id': product_data.get('product_id', 0)
        })

    for voucher_product_doc in sort_products_by_price(voucher_product_ref):
        product_data = voucher_product_doc.to_dict()
        voucher_product_data.append({
            'description': product_data.get('description', ''),
            'image': product_data.get('image', ''),
            'name': product_data.get('name', ''),
            'price': product_data.get('price', 0),
            'product_id': product_data.get('product_id', 0)
        })

    for accessory_product_doc in sort_products_by_price(accessory_product_ref):
        product_data = accessory_product_doc.to_dict()
        accessory_product_data.append({
            'description': product_data.get('description', ''),
            'image': product_data.get('image', ''),
            'name': product_data.get('name', ''),
            'price': product_data.get('price', 0),
            'product_id': product_data.get('product_id', 0)
        })

    return render_template('shop.html',
                            coins=coins,
                            login_days=login_days,
                            shares_product_data=shares_product_data,
                            voucher_product_data=voucher_product_data,
                            accessory_product_data=accessory_product_data
                            )

def sort_products_by_price(products):
    return sorted(products, key=lambda x: int(x.to_dict().get('price', 0)) if isinstance(x.to_dict().get('price', 0), (int, str)) else 0)


@app.route('/claim_reward', methods=['GET'])
def claim_reward():
    try:
        user_email = session['user']
        user_ref = db.collection('users').where('email', '==', user_email).limit(1).get()

        if not user_ref:
            flash("User not found.", "danger")
            return redirect('/')

        user_doc = user_ref[0]
        user_data = user_doc.to_dict()
        coins = user_data.get('coins', 0)
        login_days = user_data.get('loginDays')
        claimed_days = user_data.get('claimedDays')

        # Retrieve the 'day' parameter from the query string
        day = request.args.get('day', type=int)

        if day not in claimed_days:
        
            coins_rewarded = reward_coins(day)
            coins += coins_rewarded
            claimed_days.append(day)

            # Update the user document with the new coins value
            db.collection('users').document(user_doc.id).update({
                'coins': coins,
                'claimedDays': claimed_days
                })

            flash(f"Claimed reward for Day {day}: {coins_rewarded} coins", "success")
            return redirect('/shop')
        
        else:
            flash("Coins have already been claimed for this day.", "warning")
            return redirect('/shop')

    except Exception as e:
        flash(f"Error claiming reward: {str(e)}", "danger")
        return redirect('/shop')


@app.route('/deduct-coins/<int:product_id>', methods=['POST', 'GET'])
def deduct_coins(product_id):
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'})

    email = session['user']
    print(email)
    user_ref = db.collection('users').where('email', '==', email).limit(1).get()

    if not user_ref:
        return jsonify({'success': False, 'message': 'User not found'})

    user_doc = user_ref[0]
    user_data = user_doc.to_dict()

    product_ref = db.collection('Products').where('product_id', '==', product_id).limit(1).get()
    
    product_iter = iter(product_ref)
    product_doc = next(product_iter, None)
    product_data = product_doc.to_dict()
    
    product_name = product_data.get('name')
    product_price = product_data.get('price')
    

    coins = user_data.get('coins')
    if coins is None or not isinstance(coins, int):
        flash("Invalid or missing coins.", "warning")

    if coins < product_price:
        flash("Insufficient coins.", "warning")

    if not product_ref:
        flash("Product not found.", "warning")


    new_coins = coins - product_price
    user_doc.reference.update({'coins': new_coins})
    send_purchase_email(email, product_name, product_price)
    return redirect('/shop')

def send_purchase_email(email, product_name, product_price):
    subject = 'Purchase Confirmation'
    body = f'Thank you for purchasing {product_name} for {product_price} coins. Your order has been confirmed.'

    msg = Message(subject, sender=app.config['MAIL_DEFAULT_SENDER'], recipients=[email])
    msg.body = body

    try:
        mail.send(msg)
        print('Email sent successfully.')
    except Exception as e:
        print(f'Error sending email: {e}')

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']

    # Get filter parameters from the request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category_filter = request.args.get('category_filter')

    # Fetch all expenses based on filters
    all_expenses = fetch_filtered_expenses(user_email, start_date, end_date, category_filter)

    # Organize expenses by date
    all_expenses_by_date = organize_expenses_by_date(all_expenses)

    for date, expenses in all_expenses_by_date.items():
        for expense in expenses:
            expense['cost'] = float(expense['cost'])

    # Calculate total expenses for each date
    total_by_date = calculate_total_by_date(all_expenses_by_date)

    # Sort expenses by date in descending order
    all_expenses_by_date = dict(sorted(all_expenses_by_date.items(), key=lambda x: datetime.strptime(x[0], '%Y-%m-%d'), reverse=True))

    return render_template('history.html',
                           all_expenses_by_date=all_expenses_by_date,
                           total_by_date=total_by_date)

def calculate_total_by_date(expenses_by_date):
    total_by_date = {}

    for date, expenses in expenses_by_date.items():
        total_cost = sum(float(expense['cost']) for expense in expenses)
        total_by_date[date] = float(total_cost)

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
    for expense_type in ['Budget', 'Investment', 'Food', 'Transport', 'Others']:
        expenses = fetch_expenses_by_type(expense_type, user_email)
        all_expenses.extend(expenses)

    return all_expenses

def format_date(value, format='%d %B %Y'):
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d')  # Convert string to datetime object
    return value.strftime(format)

app.jinja_env.filters['format_date'] = format_date

def fetch_filtered_expenses(user_email, start_date=None, end_date=None, category_filter=None):
    all_expenses = fetch_all_expenses(user_email)

    # Apply filters
    filtered_expenses = []

    for expense in all_expenses:
        expense_date = datetime.strptime(expense['date'], '%Y-%m-%d')

        if (start_date is None or expense_date >= datetime.strptime(start_date, '%Y-%m-%d')) and \
           (end_date is None or expense_date <= datetime.strptime(end_date, '%Y-%m-%d')) and \
           (category_filter is None or expense['category'] == category_filter):
            filtered_expenses.append(expense)

    return filtered_expenses

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
                'savingsGoal': 0,
                'nextWeekDate': '',
                'totalSavings': 0
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


@app.route('/changepass', methods=['GET', 'POST'])
def change_password():
    user_email = session.get('user')
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

    # Pass the user's email to the template
    
    return render_template('changepass.html', user_email=user_email)


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

                # Update user details in Firestore, including the new file path for the uploaded photo
                user_data['photo_path'] = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # Update user details in Firestore
        user_doc.reference.update(user_data)
        
        flash("Profile successfully updated!", "success")
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
    return redirect('/user_food_expenses')


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
    return redirect('/user_transport_expenses')


@app.route('/copy_previous_budget', methods=['POST'])
def copy_previous_budget():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")

    latest_date_query = db.collection('Budget').where('user_email', '==', user_email).order_by('date', direction=firestore.Query.DESCENDING).limit(1)
    latest_date_result = latest_date_query.get()

    if not latest_date_result:
        flash("No previous budget data found.", "warning")
        return redirect('/user_budget')
    
    latest_date_doc = latest_date_result[0]
    latest_date = latest_date_doc.get('date')

    # Fetch all the budget expenses for the logged-in user on the latest date
    latest_budget_expenses = db.collection('Budget').where('user_email', '==', user_email).where('date', '==', latest_date).stream()

    try:
        # Copy all the budget data from the previous date to today's date
        for budget_doc in latest_budget_expenses:
            budget_data = budget_doc.to_dict()

            # Generate a new unique index for the copied entry
            new_unique_index = get_new_unique_index()

            # Update the budget data with the new date and unique index
            budget_data['date'] = current_date
            budget_data['unique_index'] = new_unique_index

            # Add the copied budget data to today's date
            db.collection('Budget').add(budget_data)

        flash("All budget data copied successfully from the previous date!", "success")
    except Exception as e:
        flash(f"An error occurred during budget data copying: {str(e)}", "warning")

    return redirect('/user_budget')

def get_new_unique_index():
    # You can implement your logic here to generate a new unique index
    # This can be a random number, a counter, or any other mechanism
    # Ensure that the generated index is unique within the collection
    # For simplicity, let's use a random number between 1 and 1000 in this example
    latest_budget = db.collection('Budget').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
    latest_index = 0

    for budget_doc in latest_budget:
            latest_index = int(budget_doc.to_dict().get('unique_index', 0))
            
    unique_index = latest_index + 1
    return unique_index


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

            flash("Budget expense saved successfully!", "success")
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

        flash("Budget expense updated successfully!", "success")
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
        flash("Budget expense not found.", "warning")
        return redirect('/user_budget_expenses')
    
    try:
        # Delete the food expense from Firestore
        budget_doc.reference.delete()
        flash("Budget expense deleted successfully!", "success")
        
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
        return redirect('/user_budget')
    
    # Pass the updated data to the template
    return redirect('/user_budget')
        
@app.route('/addinvestment', methods=['GET', 'POST'])
def addinvestment():
    
    if request.method == 'POST':
        api = '1HEU5NM89I8H1AKX'
        base_url = 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY'
        user_email = session['user']
        investment_id = request.form.get('investment_id')
        ticker = request.form.get('ticker')
        quantity = int(request.form.get('quantity'))
        url = f'{base_url}&symbol={ticker}&interval=1min&apikey={api}'
        
        payload = {}
        headers = {}

        response = requests.request("GET", url, headers=headers, data=payload)

        stockData = json.loads(response.text)
        response = requests.get(url)
        data = response.json()

        if ('Meta Data' in stockData):
            lastRefreshed = stockData["Meta Data"]["3. Last Refreshed"]
            latestPrices = stockData["Time Series (1min)"][lastRefreshed]
            closingUSDPrice = latestPrices["4. close"]

            conversion_url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=SGD&apikey={api}"
            conversion_response = requests.get(conversion_url)
            conversion_data = json.loads(conversion_response.text)
            exchange_rate = float(conversion_data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
            closingPrice = float(closingUSDPrice) * exchange_rate
            totalClosingPrice = round(float(closingPrice) * quantity, 2)

            try:
                # Check if foodName or cost is empty
                if not ticker or not quantity:
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
                    'ticker': ticker,
                    'quantity': quantity,
                    'date': current_date,  # Add the date field
                    'unique_index': unique_index,
                    'cost': totalClosingPrice,
                    'lastRefreshed': lastRefreshed,
                    'status': 'active',
                    'latest_price': totalClosingPrice,
                    'price_difference': 0
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
        else:
            flash("No such ticker.", "warning")
            return redirect('/user_investment_expenses')

    return render_template('user_investment_expenses.html', lastRefreshed=lastRefreshed)

@app.route('/user_investment_expenses')
def user_investment_expenses():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Fetch the list of food expenses for the logged-in user
    investment_expenses = db.collection('Investment').where('user_email', '==', user_email).where('status', '==', 'active').stream()
    
    
    user_investment_data = []

    # Iterate through the investment expenses and extract relevant information
    for investment_doc in investment_expenses:
        investment_data = investment_doc.to_dict()

        # Make API call to get the latest price for each ticker
        ticker = investment_data.get('ticker', '')
        quantity = investment_data.get('quantity', 0)
        latest_price = get_latest_price(ticker)
        
        total_latest_price = round((latest_price * quantity), 2)
        
        if total_latest_price is not None:
            # Calculate the difference between latest price and closingPrice
            closing_price = investment_data.get('cost', 0)
            price_difference = round(total_latest_price - closing_price, 2)
            price_difference_abs = abs(price_difference)
            

            user_investment_data.append({
                'ticker': ticker,
                'quantity': quantity,
                'unique_index': investment_data.get('unique_index', ''),
                'date': investment_data.get('date', ''),
                'current_date': current_date,
                'cost': closing_price,
                'lastRefreshed': investment_data.get('lastRefreshed', ''),
                'latest_price': investment_data.get('latest_price', 0),
                'price_difference': price_difference,
                'price_difference_abs': price_difference_abs
            })

            investment_data={
            'latest_price': total_latest_price
            }

            investment_doc.reference.update(investment_data)
    
    return render_template('user_investment_expenses.html',  user_investment_data=user_investment_data)

def get_latest_price(ticker):
    api = '1HEU5NM89I8H1AKX'
    base_url = 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY'
    url = f'{base_url}&symbol={ticker}&interval=1min&apikey={api}'

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)
    stock_data = json.loads(response.text)

    if 'Meta Data' in stock_data:
        last_refreshed = stock_data["Meta Data"]["3. Last Refreshed"]
        latest_prices = stock_data["Time Series (1min)"][last_refreshed]
        closing_usd_price = latest_prices["4. close"]

        conversion_url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=SGD&apikey={api}"
        conversion_response = requests.get(conversion_url)
        conversion_data = json.loads(conversion_response.text)
        exchange_rate = float(conversion_data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
        closing_price = float(closing_usd_price) * exchange_rate

        return round(closing_price, 2)
    else:
        return None  # Handle the case where API response does not contain expected data

@app.route('/sell_investment/<unique_index>', methods=['POST', 'GET'])
def sell_investment(unique_index):
    try:
        user_email = session['user']
        investment_expense = db.collection('Investment').where('user_email', '==', user_email).where('status', '==', 'active').where('unique_index', '==', int(unique_index)).limit(1).stream()

        for investment_doc in investment_expense:
            investment_data = investment_doc.to_dict()

            # Fetch the required information from the investment expense
            quantity = investment_data.get('quantity', 0)
            closing_price = investment_data.get('cost', 0)
            latest_price = get_latest_price(investment_data.get('ticker', ''))
            total_latest_price = latest_price * quantity

            if total_latest_price is not None:
                # Calculate the difference between latest price and closingPrice
                price_difference = total_latest_price - closing_price

                # Update totalSavings field in the user model in Firestore
                user_ref = db.collection('users').where('email', '==', user_email).limit(1).get()
                if user_ref:
                    user_doc = user_ref[0]
                    user_data = user_doc.to_dict()
                    current_total_savings = user_data.get('totalSavings', 0)
                    new_total_savings = current_total_savings + price_difference

                    user_doc.reference.update({'totalSavings': new_total_savings})
                
                investment_doc.reference.update({
                    'status': 'sold',
                    'price_difference': price_difference
                    })

                flash(f"Successfully sold!", "success")
            else:
                flash(f"Failed to update total savings. Unable to fetch the latest price for investment with unique index {unique_index}.", "warning")

        return redirect('/user_investment_expenses')
    except Exception as e:
        flash(f"An error occurred during savings update: {str(e)}", "warning")
        return redirect('/user_investment_expenses')

# @app.route('/edit_investment_expenses', methods=['GET', 'POST'])
# def edit_investment_expense():
#     # Redirect to the home page if the user is not logged in
#     if 'user' not in session:
#         return redirect('/')

#     user_email = session['user']
#     investment_unique_index = request.form.get('unique_index')

#     if not investment_unique_index or not investment_unique_index.strip():
#         raise ValueError("Invalid or empty unique_index")
    
#     investment_unique_index = int(investment_unique_index)
#     investment_ref = db.collection('Investment').where('user_email', '==', user_email).where('unique_index', '==', investment_unique_index).get()
#     investment_iter = iter(investment_ref)
#     investment_doc = next(investment_iter, None)

#     if not investment_doc:
#        return redirect('/')
   
#     investment_data = investment_doc.to_dict()
    
#     if request.method == 'POST':
#         print(request.form)
#         new_ticker = request.form.get('ticker')
#         new_quantity = int(request.form.get('quantity'))
#         new_closing_price = round(float(investment_data.get('cost')) * new_quantity)

#         investment_data={
#             'cost': new_closing_price,
#             'quantity': new_quantity,
#             'ticker':new_ticker
#         }
#         user_investment_data=[]
#         investment_doc.reference.update(investment_data)
#         user_investment_data.append(investment_data)

#         flash("investment expense updated successfully!", "success")
#         return redirect('/user_investment_expenses')

    
#     return render_template('user_investment_expenses.html', user_investment_data=user_investment_data, investment_data=investment_data)

@app.route('/delete_investment_expense/<int:unique_index>', methods=['GET'])
def delete_investment_expense(unique_index):
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")
    
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
                'ticker': investment_data.get('ticker', ''),
                'quantity': investment_data.get('quantity', ''),
                'unique_index': investment_data.get('unique_index', ''),
                'date': investment_data.get('date', ''),
                'current_date': current_date,
                'cost': investment_data.get('cost', ''),
                'lastRefreshed': investment_data.get('lastRefreshed', '')
            })

    except Exception as e:
        # Handle any errors that may occur during deletion
        flash(f"An error occurred during food expense deletion: {str(e)}", "danger")
        return redirect('/user_investment_expenses')
    
    # Pass the updated data to the template
    return redirect('/user_investment_expenses')



@app.route('/addothers', methods=['GET', 'POST'])
def addothers():
    if request.method == 'POST':
        user_email = session['user']
        others_id = request.form.get('others_id')
        othersName = request.form.get('othersName')
        cost = request.form.get('cost')

        try:
            # Check if othersName or cost is empty
            if not othersName or not cost:
                flash("Please fill in both others name and cost.", "warning")
                return redirect('/user_others_expenses')

            latest_others = db.collection('Others').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
            latest_index = 0

            for others_doc in latest_others:
                latest_index = int(others_doc.to_dict().get('unique_index', 0))

            unique_index = latest_index + 1

            # Get current date
            current_date = datetime.now().strftime("%Y-%m-%d")

            # Original data
            others_data = {
                'user_email': user_email,
                'othersName': othersName,
                'cost': cost,
                'date': current_date,  # Add the date field
                'unique_index': unique_index
            }

            # Get dynamic fields
            dynamic_fields = request.form.getlist('newField')
            print("Dynamic Fields:", dynamic_fields)

            # Process dynamic fields and add them to others_data
            for index, value in enumerate(dynamic_fields):
                others_data[f'newField_{index + 1}'] = value

            if others_id:
                # Editing an existing others expense
                others_ref = db.collection('others').document(others_id)
                others_ref.update(others_data)
            else:
                # Adding a new others expense
                db.collection('Others').add(others_data)

            flash("others expense saved successfully!", "success")
            return redirect('/user_others_expenses')

        except Exception as e:
            flash(f"An error occurred during others creation: {str(e)}", "warning")

    return render_template('user_others_expenses.html')


@app.route('/user_others_expenses')
def user_others_expenses():
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch the list of others expenses for the logged-in user
    others_expenses = db.collection('Others').where('user_email', '==', user_email).where('date', '==', current_date).stream()

    # Create a list to store the others data
    user_others_data = []

    # Iterate through the others expenses and extract relevant information
    for others_doc in others_expenses:
        others_data = others_doc.to_dict()
        user_others_data.append({
            'othersName': others_data.get('othersName', ''),
            'cost': others_data.get('cost', ''),
            'unique_index': others_data.get('unique_index', ''),
            'date': others_data.get('date', ''),
            'current_date': current_date
        })

    # Render user_others_expense.html
    return render_template('user_others_expenses.html', user_others_data=user_others_data)

@app.route('/edit_others_expenses', methods=['GET', 'POST'])
def edit_others_expense():
    # Redirect to the home page if the user is not logged in
    if 'user' not in session:
        return redirect('/')

    user_email = session['user']
    others_unique_index = request.form.get('unique_index')

    if not others_unique_index or not others_unique_index.strip():
        raise ValueError("Invalid or empty unique_index")
    
    others_unique_index = int(others_unique_index)
    others_ref = db.collection('Others').where('user_email', '==', user_email).where('unique_index', '==', others_unique_index).get()
    others_iter = iter(others_ref)
    others_doc = next(others_iter, None)

    if not others_doc:
       return redirect('/')
   
    others_data = others_doc.to_dict()
    
    if request.method == 'POST':
        print(request.form)
        new_others_name = request.form.get('othersName')
        new_cost = request.form.get('cost')

        others_data={
            'cost': new_cost,
            'othersName':new_others_name
        }
        print(others_data)
        user_others_data=[]
        others_doc.reference.update(others_data)
        user_others_data.append(others_data)

        flash("others expense updated successfully!", "success")
        return redirect('/user_others_expenses')

    
    return render_template('user_others_expenses.html', user_others_data=user_others_data, others_data=others_data)

@app.route('/delete_others_expense/<int:unique_index>', methods=['GET'])
def delete_others_expense(unique_index):
    if 'user' not in session:
        return redirect('/')
    
    user_email = session['user']
    
    # Find the others expense with the given unique index
    others_ref = db.collection('Others').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
    others_iter = iter(others_ref)
    others_doc = next(others_iter, None)
    
    if not others_doc:
        # others expense not found
        flash("Others expense not found.", "warning")
        return redirect('/user_others_expenses')
    
    try:
        # Delete the others expense from Firestore
        others_doc.reference.delete()
        flash("Others expense deleted successfully!", "success")
        
        # Fetch the updated list of others expenses for the logged-in user
        others_expenses = db.collection('Others').where('user_email', '==', user_email).stream()
        
        # Create a list to store the others data
        user_others_data = []

        # Iterate through the others expenses and extract relevant information
        for others_doc in others_expenses:
            others_data = others_doc.to_dict()
            user_others_data.append({
                'othersName': others_data.get('othersName', ''),
                'cost': others_data.get('cost', ''),
                'unique_index': others_data.get('unique_index', '')
            })

    except Exception as e:
        # Handle any errors that may occur during deletion
        flash(f"An error occurred during others expense deletion: {str(e)}", "danger")
        return redirect('/user_others_expenses')
    
    # Pass the updated data to the template
    return redirect('/user_others_expenses')


        
openai.api_key = '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'
@app.route('/analysis')
def total_budget_expense():
    user_email = session['user']

    email = session['user']
    user_ref = db.collection('users').where('email', '==', email).limit(1).get()
    user_doc = user_ref[0]
    user_data = user_doc.to_dict()
    update_login_rewards(email, user_data, user_doc)
    coins=user_data.get('coins', 0)
    savings_goal = float(user_data.get('savingsGoal', 0))

    total_food_cost = fetch_total_cost_analysis('Food', user_email)
    total_transport_cost = fetch_total_cost_analysis('Transport', user_email)
    total_budget_cost = fetch_total_cost_analysis('Budget', user_email)
    total_others_cost = fetch_total_cost_analysis('Others', user_email)

    # Fetch all user investments
    investment_ref = db.collection('Investment').where('user_email', '==', user_email).stream()
    
    user_investment_data = []

    for investment_doc in investment_ref:
        investment_data = investment_doc.to_dict()

        user_investment_data.append({
            'ticker': investment_data.get('ticker', ''),
            'quantity': investment_data.get('quantity', 0),
            'unique_index': investment_data.get('unique_index', ''),
            'date': investment_data.get('date', ''),
            'cost': investment_data.get('cost', 0),
            'lastRefreshed': investment_data.get('lastRefreshed', ''),
            'latest_price': investment_data.get('latest_price', 0),
            'status': investment_data.get('status', '')
        })

    total_investment_cost = fetch_total_cost_analysis('Investment', user_email)

    sold_investment_ref = db.collection('Investment').where('user_email', '==', user_email).where('status', '==', 'sold').stream()

    total_investment_sold = 0

    for sold_investment_doc in sold_investment_ref:
        sold_investment_data = sold_investment_doc.to_dict()
        
        total_investment_sold += float(sold_investment_data.get('price_difference', 0))
    
    total_expense = total_food_cost + total_transport_cost + total_others_cost
    total_savings = float((total_budget_cost + total_investment_sold) - total_expense)

    user_doc.reference.update({
            'totalSavings': total_savings
            })
    
    progress_percentage = (total_savings / savings_goal) * 100 if savings_goal > 0 else 0

    return render_template('analysis.html',
                           total_food_cost=total_food_cost,
                           total_transport_cost=total_transport_cost,
                           total_budget_cost=total_budget_cost,
                           total_investment_cost=total_investment_cost,
                           total_others_cost=total_others_cost,
                           total_expense=total_expense,
                           total_savings=total_savings,
                           coins=coins,
                           savings_goal=savings_goal,
                           progress_percentage=progress_percentage,
                           total_investment_sold=total_investment_sold,
                           user_investment_data=user_investment_data)

def update_login_rewards(user_email, user_data, user_doc):
    singapore_timezone = pytz.timezone('Asia/Singapore')
    current_datetime = datetime.now(singapore_timezone)
    current_date = current_datetime.strftime("%Y-%m-%d") 


    # Update the 'lastLogin' field to today's date
    if user_data['lastLogin'] != current_datetime and current_datetime.hour >= 0:
        if current_datetime > user_data.get('nextRewardTime', datetime.min):
            next_week_start = user_data.get('nextWeekDate')

            if current_datetime > next_week_start:
                user_data['lastLogin'] = current_datetime
                user_data['loginDays'] = 1
                user_data['nextRewardTime'] = (current_datetime + timedelta(days=1)).replace(hour=0, minute=0, second=0)
                user_data['claimedDays'] = []
                next_week_start = (current_datetime + timedelta(days=(7 - current_datetime.weekday()))).replace(hour=0, minute=0, second=0)
            
                user_data['nextWeekDate'] = next_week_start
            else:
                user_data['lastLogin'] = current_datetime
                user_data['loginDays'] += 1
                user_data['nextRewardTime'] = (current_datetime + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        else:
            user_data['lastLogin'] = current_datetime
    
    db.collection('users').document(user_doc.id).update(user_data)
    

def reward_coins(login_days):
    try:
    # Example: Reward 10 coins for the first day, and 5 additional coins for each subsequent day
        coins_to_reward = 10 + (login_days - 1) * 5
        
        return coins_to_reward
            
    except Exception as e:
        flash(f"Error updating coins: {str(e)}", "danger")

@app.route('/analysis', methods=['GET', 'POST'])
def analysis():
    if request.method == 'POST':
        # Get user inputs from the form
        budget = float(request.form['budget'])
        food_expense = float(request.form['food_expense'])
        transport_expense = float(request.form['transport_expense'])
        investment_expense = float(request.form['investment_expense'])

        # Fetch all user investments
        user_email = session['user']
        investment_ref = db.collection('Investment').where('user_email', '==', user_email).stream()
        user_investments = [investment_doc.to_dict().get('ticker', '') for investment_doc in investment_ref]

        prompt = f"Analyze the impact on savings given a budget of {budget}, investment expense of {investment_expense}, food expense of {food_expense}, and transport expense of {transport_expense}. Provide a detailed analysis report on the user's financial statistics "

        analysis_result = openai_analysis(prompt)
        session['analysis_result'] = analysis_result

        # Recommend investments based on similar investments the user has bought
        if user_investments:
            similar_investments = ', '.join(user_investments[:5])  # Consider the first 5 investments as similar
            prompt2 = f"given a budget of {budget}, investment expense of {investment_expense}, food expense of {food_expense}, and transport expense of {transport_expense}. Recommend 5 investments similar to {similar_investments}. Briefly explain why these stocks are reccomended to the user after analyzing their profile."
        else:
            # If the user has no investments, provide a generic recommendation prompt
            prompt2 = f"Given a budget of {budget}, investment expense of {investment_expense}, food expense of {food_expense}, and transport expense of {transport_expense}, provide recommendations for 5 stocks based on their current profile."

        recommendations = openai_analysis(prompt2)
        session['recommendations'] = recommendations

        # Pass 'prompt2' as a keyword argument to url_for
        return redirect(url_for('prompt', prompt=prompt2))
    
    return render_template('analysis.html', prompt="something", prompt2="things")


def openai_analysis(prompt):
    try:
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
        analysis_result = response.choices[0].message.content
        return analysis_result

    except Exception as e:
        return f"Error: {str(e)}"
    
def openai_analysis2(prompt2):
    try:
        response = openai.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt2,
                }
            ],
            model="gpt-3.5-turbo",
        )
        print (response)
        recommendations = response.choices[0].message.content
        return recommendations

    except Exception as e:
        return f"Error: {str(e)}"

def fetch_total_cost_analysis(expense_type, user_email):
    total_cost = 0
    expense_ref = db.collection(expense_type).where('user_email', '==', user_email).stream()

    for expense_doc in expense_ref:
        expense_data = expense_doc.to_dict()
        total_cost += float(expense_data.get('cost', 0))

    return total_cost
    
@app.route('/prompt')
def prompt():
    analysis_result = session.get('analysis_result', '')
    recommendations = session.get('recommendations', '')
    return render_template('prompt.html', analysis_result=analysis_result, recommendations=recommendations)

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    # Retrieve the analysis result from the session
    analysis_result = session.get('analysis_result', '')
    recommendations = session.get('recommendations', '')

    # Create a PDF document
    pdf = FPDF('P', 'mm', 'Letter')
    pdf.add_page()
    pdf.set_font('helvetica', size=12)

    # Add title
    pdf.cell(0, 10, "Analysis Report", ln=True, align='C')
    pdf.ln(5)  # Add a little space after the title

    # Add analysis result with a border
    pdf.set_fill_color(200, 220, 255)  # Light blue background
    pdf.cell(0, 10, "Analysis Result:", ln=True, align='L', fill=True)
    pdf.multi_cell(0, 10, analysis_result.encode('utf-8').decode('latin-1'), align='L')  # Encode and decode using 'utf-8'
    pdf.ln(5)  # Add a little space after the analysis result

    pdf.set_fill_color(255, 200, 200)
    pdf.cell(0, 10, "Expense Breakdown:", ln=True, align='L', fill=True)
    pdf.ln(5)
    add_graph_to_pdf(pdf)
    pdf.ln(100)

    pdf.set_fill_color(255, 240, 200)  # Light yellow background
    pdf.cell(0, 10, "Recommendations:", ln=True, align='L', fill=True)
    pdf.multi_cell(0, 10, recommendations.encode('utf-8').decode('latin-1'), align='L')  # Encode and decode using 'utf-8'
    pdf.ln(20)


    

    downloads_folder = os.path.expanduser("~" + os.sep + "Downloads")
    pdf_path = os.path.join(downloads_folder, 'finsaver_analysis.pdf')

    # Save the PDF to the downloads folder
    pdf.output(pdf_path)

    return send_file(pdf_path, as_attachment=True, download_name='finsaver_analysis.pdf')

def add_graph_to_pdf(pdf):
    # Fetch analysis data from session
    total_food_cost = session.get('total_food_cost', 0)
    total_transport_cost = session.get('total_transport_cost', 0)
    total_budget_cost = session.get('total_budget_cost', 0)
    total_investment_cost = session.get('total_investment_cost', 0)
    total_savings = session.get('total_savings', 0)
    total_others_cost = session.get('total_others_cost', 0)
    # Create a new figure
    fig, ax = plt.subplots()
    bars = ax.bar(['Food', 'Transport', 'Budget', 'Investment', 'Savings', 'Others'],
                  [total_food_cost, total_transport_cost, total_budget_cost, total_investment_cost, total_savings, total_others_cost],
                  color=['blue', 'green', 'orange', 'purple', 'red', 'pink'])

    # Add labels and title
    ax.set_xlabel('Categories')
    ax.set_ylabel('Amount')
    ax.set_title('Expense Analysis')

    # Add values on top of the bars
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, yval, round(yval, 2), ha='center', va='bottom')

    # Save the plot to the PDF
    graph_path = os.path.join(os.path.expanduser("~" + os.sep + "Downloads"), 'expense_analysis_graph.png')
    fig.savefig(graph_path, format='png')
    
    # Add the saved graph to the PDF
    pdf.image(graph_path, x=10, y=pdf.get_y(), w=150)
    
    # Close the plot
    plt.close()

@app.route("/graph")
def graph():
    # Fetch analysis data from session
    total_food_cost = session.get('total_food_cost', 0)
    total_transport_cost = session.get('total_transport_cost', 0)
    total_budget_cost = session.get('total_budget_cost', 0)
    total_investment_cost = session.get('total_investment_cost', 0)
    total_others_cost = session.get('total_others_cost', 0)
    total_savings = session.get('total_savings', 0)

    # Create a bar graph
    categories = ['Food', 'Transport', 'Budget', 'Investment', 'Savings', 'Others']
    values = [total_food_cost, total_transport_cost, total_budget_cost, total_investment_cost, total_savings, total_others_cost]

    fig, ax = plt.subplots()
    bars = ax.bar(categories, values, color=['blue', 'green', 'orange', 'purple', 'red', 'pink'])

    # Add labels and title
    ax.set_xlabel('Categories')
    ax.set_ylabel('Amount')
    ax.set_title('Expense Analysis')

    # Add values on top of the bars
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval, round(yval, 2), ha='center', va='bottom')

    # Save the plot to a temporary buffer
    buf = BytesIO()
    plt.savefig(buf, format="png")
    # Embed the result in the html output
    data = base64.b64encode(buf.getbuffer()).decode("ascii")

    return render_template('home.html', image="data:image/png;base64," + data)

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