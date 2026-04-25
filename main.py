from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from init import DB_NAME, create_database
import os
from datetime import datetime
import json

app = Flask(__name__, template_folder='html')
app.secret_key = 'your_secret_key_here'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def get_walkin_pricing():
    """
    Get walk-in pricing based on current time
    Off-Peak Hours: 12:00 PM - 3:00 PM ($25.00)
    Peak Hours: 3:00 PM - 12:00 PM ($35.00)
    """
    now = datetime.now()
    hour = now.hour
    
    is_peak = hour < 12 or hour >= 15  # Off-peak only 12 PM to 3 PM (hours 12-14)
    
    return {
        'is_peak': is_peak,
        'price': 3500,  # $35.00 in cents
        'price_offpeak': 2500,  # $25.00 in cents
        'price_display': '$35.00' if is_peak else '$25.00',
        'period': 'Peak Hours' if is_peak else 'Off-Peak Hours',
        'badge_color': 'bg-danger' if is_peak else 'bg-info'
    }

# ITEMS ROUTES
@app.route('/')
def index():
    return redirect(url_for('items'))

@app.route('/items', methods=['GET', 'POST'])
def items():
    if request.method == 'POST':
        try:
            name = request.form['name']
            item_type = request.form['type']
            price = request.form['price']
            
            if not name or not item_type:
                flash('Name and Type are required', 'danger')
                return redirect(url_for('items'))
            
            conn = get_db()
            conn.execute(
                'INSERT INTO items (name, type, price) VALUES (?, ?, ?)',
                (name, item_type, int(float(price) * 100) if price else None)
            )
            conn.commit()
            conn.close()
            
            flash(f'Item "{name}" created successfully!', 'success')
            return redirect(url_for('items'))
        except Exception as e:
            flash(f'Error creating item: {str(e)}', 'danger')
            return redirect(url_for('items'))
    
    conn = get_db()
    items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    
    return render_template('items.html', items=items)

@app.route('/items/<int:item_id>/delete', methods=['POST'])
def delete_item(item_id):
    try:
        conn = get_db()
        conn.execute('DELETE FROM items WHERE iid = ?', (item_id,))
        conn.commit()
        conn.close()
        flash('Item deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting item: {str(e)}', 'danger')
    return redirect(url_for('items'))

# STRINGS (STRINGING) ROUTES
@app.route('/strings', methods=['GET', 'POST'])
def strings():
    if request.method == 'POST':
        try:
            string_type = request.form['string_type']
            string_price = request.form['string_price']
            member_price = request.form['member_price']
            
            if not string_type:
                flash('String Type is required', 'danger')
                return redirect(url_for('strings'))
            
            conn = get_db()
            conn.execute(
                'INSERT INTO stringing (string_type, string_price, member_price) VALUES (?, ?, ?)',
                (string_type, int(float(string_price) * 100) if string_price else None, int(float(member_price) * 100) if member_price else None)
            )
            conn.commit()
            conn.close()
            
            flash(f'String "{string_type}" added successfully!', 'success')
            return redirect(url_for('strings'))
        except Exception as e:
            flash(f'Error adding string: {str(e)}', 'danger')
            return redirect(url_for('strings'))
    
    conn = get_db()
    strings = conn.execute('SELECT * FROM stringing').fetchall()
    conn.close()
    
    return render_template('strings.html', strings=strings)

@app.route('/strings/<int:string_id>/delete', methods=['POST'])
def delete_string(string_id):
    try:
        conn = get_db()
        conn.execute('DELETE FROM stringing WHERE sid = ?', (string_id,))
        conn.commit()
        conn.close()
        flash('String deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting string: {str(e)}', 'danger')
    return redirect(url_for('strings'))

# CUSTOM ORDERS ROUTES (One-time orders)

@app.route('/custom-orders', methods=['GET'])
def custom_orders():
    return render_template('custom_orders.html')

@app.route('/cart/add-custom-order-direct', methods=['POST'])
def add_custom_order_direct():
    try:
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '0')
        
        if not description:
            flash('Order description is required', 'danger')
            return redirect(url_for('custom_orders'))
        
        try:
            price_cents = int(float(price) * 100) if price else 0
        except ValueError:
            flash('Invalid price format', 'danger')
            return redirect(url_for('custom_orders'))
        
        # Save to database for logging
        conn = get_db()
        conn.execute(
            'INSERT INTO custom_orders (description, price) VALUES (?, ?)',
            (description, price_cents)
        )
        conn.commit()
        
        # Get the ID of the newly created order
        order = conn.execute('SELECT coid FROM custom_orders WHERE description = ? AND price = ? ORDER BY coid DESC LIMIT 1', 
                           (description, price_cents)).fetchone()
        conn.close()
        
        # Store custom order in session as PENDING - only added to cart when checkout page loads
        session['pending_custom_order'] = {
            'id': order['coid'] if order else None,
            'description': description,
            'price': price_cents
        }
        session.modified = True
        
        flash(f'Custom order "{description}" added! Go to Checkout to complete your purchase.', 'success')
        return redirect(url_for('custom_orders'))
    except Exception as e:
        flash(f'Error adding to cart: {str(e)}', 'danger')
        return redirect(url_for('custom_orders'))

@app.route('/checkout', methods=['GET'])
def checkout():
    conn = get_db()
    items = conn.execute('SELECT * FROM items ORDER BY type, name').fetchall()
    strings = conn.execute('SELECT * FROM stringing ORDER BY string_type').fetchall()
    conn.close()
    
    walkin_pricing = get_walkin_pricing()
    
    # Get cart from session if it exists
    session_cart = session.get('cart', [])
    
    # Check if there's a pending custom order to add
    if 'pending_custom_order' in session:
        pending = session.pop('pending_custom_order')
        cart_item = {
            'type': 'custom_order',
            'id': pending['id'],
            'description': pending['description'],
            'price': pending['price'],
            'quantity': 1
        }
        session_cart.append(cart_item)
        session.modified = True
    
    return render_template('checkout.html', items=items, strings=strings, walkin=walkin_pricing, session_cart=session_cart)

@app.route('/complete-checkout', methods=['POST'])
def complete_checkout():
    try:
        import json
        
        cart_data = request.form.get('cart_data')
        discount = int(request.form.get('discount', 0))
        total = int(request.form.get('total', 0))
        subtotal = int(request.form.get('subtotal', 0))
        cash_card = int(request.form.get('cash_card', 0))  # 0 = cash, 1 = card
        
        cart = json.loads(cart_data)
        
        if not cart:
            flash('Cart is empty', 'danger')
            return redirect(url_for('checkout'))
        
        conn = get_db()
        
        # Record the transaction - log purchase info
        now = datetime.now()
        checkout_date = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # First, insert a metadata entry with iid=NULL to store purchase summary
        conn.execute(
            'INSERT INTO checkout (checkout_date, total_price, cash_card, iid, discount, user) VALUES (?, ?, ?, ?, ?, ?)',
            (checkout_date, total, cash_card, None, discount, f'PURCHASE_META:{subtotal}')
        )
        
        # Then insert all items with their correct individual prices
        for item in cart:
            item_name = item.get('name') or item.get('description', 'Unknown Item')
            quantity = item.get('quantity', 1)
            item_price = item['price'] * quantity
            conn.execute(
                'INSERT INTO checkout (checkout_date, total_price, cash_card, iid, discount, user) VALUES (?, ?, ?, ?, ?, ?)',
                (checkout_date, item_price, cash_card, item.get('id'), 0, f'{item_name} (x{quantity})')
            )
        
        conn.commit()
        conn.close()
        
        # Clear the session cart after successful purchase
        if 'cart' in session:
            session.pop('cart')
        
        flash(f'Purchase completed! Total: ${total / 100:.2f}', 'success')
        return redirect(url_for('checkout'))
    except Exception as e:
        flash(f'Error processing checkout: {str(e)}', 'danger')
        return redirect(url_for('checkout'))

# COACHING ROUTES
@app.route('/coaching', methods=['GET', 'POST'])
def coaching():
    search_query = request.args.get('search', '').strip()
    search_result = None
    
    if request.method == 'POST':
        try:
            name = request.form['name']
            coach = request.form['coach']
            coaching_time = request.form['coaching_time']
            phone_number = request.form['phone_number']
            coaching_type = request.form['coaching_type']
            member = 1 if request.form.get('member') else 0
            
            if not name or not coach or not coaching_type:
                flash('Name, Coach, and Coaching Type are required', 'danger')
                return redirect(url_for('coaching'))
            
            conn = get_db()
            conn.execute(
                'INSERT INTO coaching (name, coach, coaching_time, phone_number, total_payment, coaching_type, member) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (name, coach, coaching_time, int(phone_number) if phone_number else 0, 0, coaching_type, member)
            )
            conn.commit()
            conn.close()
            
            flash(f'Coaching member "{name}" added successfully!', 'success')
            return redirect(url_for('coaching'))
        except Exception as e:
            flash(f'Error adding coaching member: {str(e)}', 'danger')
            return redirect(url_for('coaching'))
    
    # Search functionality
    if search_query:
        conn = get_db()
        # Search by name in coaching table
        search_result = conn.execute(
            'SELECT * FROM coaching WHERE name LIKE ? ORDER BY name ASC',
            (f'%{search_query}%',)
        ).fetchall()
        
        # Fetch payment information for each result
        results_with_payments = []
        for person in search_result:
            payments = conn.execute(
                'SELECT * FROM coaching_payments WHERE cid = ? ORDER BY payment_date DESC',
                (person['cid'],)
            ).fetchall()
            
            total_paid = sum(p['amount'] for p in payments)
            results_with_payments.append({
                'person': person,
                'payments': payments,
                'total_paid': total_paid,
                'payment_count': len(payments)
            })
        
        conn.close()
        search_result = results_with_payments
    
    return render_template('coaching.html', search_result=search_result, search_query=search_query)

@app.route('/coaching/<int:person_id>/add-payment', methods=['POST'])
def add_coaching_payment(person_id):
    try:
        amount = int(float(request.form.get('amount', 0)) * 100)
        payment_method = int(request.form.get('payment_method', 0))  # 0 = cash, 1 = card
        notes = request.form.get('notes', '').strip()
        
        if amount <= 0:
            flash('Payment amount must be greater than 0', 'danger')
            return redirect(url_for('coaching', search=request.form.get('search', '')))
        
        conn = get_db()
        
        # Get the person's details
        person = conn.execute('SELECT * FROM coaching WHERE cid = ?', (person_id,)).fetchone()
        if not person:
            flash('Person not found', 'danger')
            conn.close()
            return redirect(url_for('coaching'))
        
        # Add payment record
        now = datetime.now()
        payment_date = now.strftime('%Y-%m-%d %H:%M:%S')
        
        conn.execute(
            'INSERT INTO coaching_payments (cid, payment_date, amount, cash_card, notes) VALUES (?, ?, ?, ?, ?)',
            (person_id, payment_date, amount, payment_method, notes)
        )
        
        # Update total payment in coaching table
        total_paid = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) as total FROM coaching_payments WHERE cid = ?',
            (person_id,)
        ).fetchone()['total']
        
        conn.execute(
            'UPDATE coaching SET total_payment = ? WHERE cid = ?',
            (total_paid + amount, person_id)
        )
        
        # Also log in checkout table for general records
        conn.execute(
            'INSERT INTO checkout (checkout_date, total_price, cash_card, iid, discount, user) VALUES (?, ?, ?, ?, ?, ?)',
            (payment_date, amount, payment_method, None, 0, f'COACHING_PAYMENT:{person["name"]}')
        )
        
        conn.commit()
        conn.close()
        
        flash(f'Payment of ${amount / 100:.2f} recorded for {person["name"]}!', 'success')
    except Exception as e:
        flash(f'Error recording payment: {str(e)}', 'danger')
    
    return redirect(url_for('coaching', search=request.form.get('search', '')))

@app.route('/coaching/<int:person_id>/delete', methods=['POST'])
def delete_coaching_member(person_id):
    try:
        conn = get_db()
        
        # Get person name for flash message
        person = conn.execute('SELECT name FROM coaching WHERE cid = ?', (person_id,)).fetchone()
        
        # Delete associated payments
        conn.execute('DELETE FROM coaching_payments WHERE cid = ?', (person_id,))
        
        # Delete coaching member
        conn.execute('DELETE FROM coaching WHERE cid = ?', (person_id,))
        
        conn.commit()
        conn.close()
        
        flash(f'Coaching member "{person["name"]}" deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting coaching member: {str(e)}', 'danger')
    
    return redirect(url_for('coaching'))

# COACHING LOGS ROUTES
@app.route('/coaching-logs', methods=['GET'])
def coaching_logs():
    selected_date = request.args.get('date')
    
    conn = get_db()
    
    # Get all coaching payment transactions
    if selected_date:
        # Filter by selected date
        all_payments = conn.execute(
            'SELECT cp.*, c.name as coaching_name FROM coaching_payments cp JOIN coaching c ON cp.cid = c.cid WHERE cp.payment_date LIKE ? ORDER BY cp.payment_date DESC',
            (f'{selected_date}%',)
        ).fetchall()
    else:
        # Show all coaching payment entries
        all_payments = conn.execute(
            'SELECT cp.*, c.name as coaching_name FROM coaching_payments cp JOIN coaching c ON cp.cid = c.cid ORDER BY cp.payment_date DESC'
        ).fetchall()
    
    # Get unique dates for calendar
    all_dates = conn.execute(
        'SELECT DISTINCT DATE(payment_date) as payment_date FROM coaching_payments ORDER BY payment_date DESC'
    ).fetchall()
    
    conn.close()
    
    # Convert dates to list
    available_dates = [row[0] for row in all_dates]
    
    return render_template('coaching_logs.html', payments=all_payments, available_dates=available_dates, selected_date=selected_date)

# LOGS ROUTES

@app.route('/logs', methods=['GET'])
def logs():
    selected_date = request.args.get('date')
    
    conn = get_db()
    
    # Get all purchase transactions grouped by checkout_date
    if selected_date:
        # Filter by selected date
        all_checkout = conn.execute(
            'SELECT * FROM checkout WHERE checkout_date LIKE ? ORDER BY checkout_date DESC',
            (f'{selected_date}%',)
        ).fetchall()
    else:
        # Show all checkout entries
        all_checkout = conn.execute(
            'SELECT * FROM checkout ORDER BY checkout_date DESC'
        ).fetchall()
    
    # Get unique dates for the calendar
    all_dates = conn.execute(
        'SELECT DISTINCT DATE(checkout_date) as purchase_date FROM checkout ORDER BY purchase_date DESC'
    ).fetchall()
    
    conn.close()
    
    # Group checkout entries by checkout_date to reconstruct purchases
    purchases = {}
    for entry in all_checkout:
        checkout_date = entry['checkout_date']
        
        # Initialize purchase record if needed
        if checkout_date not in purchases:
            purchases[checkout_date] = {
                'checkout_date': checkout_date,
                'items': [],
                'total': 0,
                'discount': 0,
                'subtotal': 0,
                'cash_card': 0  # 0 = cash, 1 = card
            }
        
        # Check if this is a metadata entry (has PURCHASE_META or PURCHASE_LOG marker)
        is_metadata = entry['user'] and ('PURCHASE_META:' in entry['user'] or 'PURCHASE_LOG:' in entry['user'])
        
        if is_metadata:
            # Extract purchase metadata
            subtotal_str = entry['user'].split(':')[1]
            subtotal = int(subtotal_str)
            purchases[checkout_date]['subtotal'] = subtotal
            purchases[checkout_date]['total'] = entry['total_price']
            purchases[checkout_date]['discount'] = entry['discount']
            purchases[checkout_date]['cash_card'] = entry['cash_card']
        else:
            # Regular item entry - add to items list
            purchases[checkout_date]['items'].append({
                'name': entry['user'],
                'price': entry['total_price'],
                'iid': entry['iid']
            })
    
    # Convert to list and sort by date
    purchases_list = sorted(purchases.values(), key=lambda x: x['checkout_date'], reverse=True)
    
    # Convert dates to list
    available_dates = [row[0] for row in all_dates]
    
    return render_template('logs.html', logs=purchases_list, available_dates=available_dates, selected_date=selected_date)
if __name__ == '__main__':
    app.run(debug=True)
