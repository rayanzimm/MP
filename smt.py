
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

            # Original data
            investment_data = {
                'user_email': user_email,
                'investmentName': investmentName,
                'cost': cost,
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

    # Fetch the list of food expenses for the logged-in user
    investment_expenses = db.collection('investment').where('user_email', '==', user_email).stream()

    # Create a list to store the food data
    user_investment_data = []

    # Variable to store the total food cost
    total_investment_cost = 0

    # Iterate through the food expenses and extract relevant information
    for investment_doc in investment_expenses:
        investment_data = investment_doc.to_dict()
        user_investment_data.append({
            'investmentName': investment_data.get('investmentName', ''),
            'cost': investment_data.get('cost', ''),
            'unique_index': investment_data.get('unique_index', '')
        })

        # Add the cost to the total_food_cost
        total_investment_cost += float(investment_data.get('cost', 0))

    # Pass the total_food_cost variable to the template
    session['total_investment_cost'] = total_investment_cost

    # Render user_food_expense.html
    return render_template('user_investment_expenses.html', user_investment_data=user_investment_data)

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
