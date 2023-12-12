from API.main import login  

# Example usage
email = 'user@example.com'
password = 'password123'


# Login
logged_in_user_id = login(email, password)
if logged_in_user_id:
    print(f"User logged in with ID: {logged_in_user_id}")
else:
    print("Login failed")
