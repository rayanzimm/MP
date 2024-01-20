
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

            latest_others = db.collection('others').order_by('unique_index', direction=firestore.Query.DESCENDING).limit(1).stream()
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
                db.collection('others').add(others_data)

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
    others_expenses = db.collection('others').where('user_email', '==', user_email).where('date', '==', current_date).stream()

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
    others_ref = db.collection('others').where('user_email', '==', user_email).where('unique_index', '==', others_unique_index).get()
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
    others_ref = db.collection('others').where('user_email', '==', user_email).where('unique_index', '==', unique_index).get()
    others_iter = iter(others_ref)
    others_doc = next(others_iter, None)
    
    if not others_doc:
        # others expense not found
        flash("others expense not found.", "warning")
        return redirect('/user_others_expenses')
    
    try:
        # Delete the others expense from Firestore
        others_doc.reference.delete()
        flash("others expense deleted successfully!", "success")
        
        # Fetch the updated list of others expenses for the logged-in user
        others_expenses = db.collection('others').where('user_email', '==', user_email).stream()
        
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
    return render_template('user_others_expenses.html', user_others_data=user_others_data)
