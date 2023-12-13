from flask import Flask, render_template, request
from firestore_connection import initialize_firestore
db = initialize_firestore()

app = Flask(__name__)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Call your login function
        user_id = login(email, password)

        if user_id:
            return f"User logged in with ID: {user_id}"
        else:
            return "Login failed"

    # Render the HTML page if it's a GET request
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
