from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, send, emit
import os
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk

# Download NLTK data (only required once)
nltk_data_dir = "/tmp/nltk_data"
os.makedirs(nltk_data_dir, exist_ok=True)
nltk.data.path.append(nltk_data_dir)

nltk.download('punkt', download_dir=nltk_data_dir)
nltk.download('stopwords', download_dir=nltk_data_dir)

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for session management
socketio = SocketIO(app,cors_allowed_origins="*")

# Path to the text file where messages will be stored
MESSAGE_FILE = 'chat_messages.txt'

# Ensure the message file exists
if not os.path.exists(MESSAGE_FILE):
    with open(MESSAGE_FILE, 'w') as f:
        f.write('')

# Predefined users (username: password)
USERS = {
    'ali': '1234',
    'zain': '1234',
    'fahad': '1234'
}

@app.route('/', methods=['GET'])
def home():
    # Redirect to login if the user is not logged in
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('chat'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username exists and the password matches
        if username in USERS and USERS[username] == password:
            session['username'] = username  # Store username in session
            return redirect(url_for('chat'))
        else:
            return "Invalid username or password. <a href='/login'>Try again</a>"

    return render_template('login.html')

@app.route('/chat', methods=['GET'])
def chat():
    # Redirect to login if the user is not logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Read all messages from the file
    with open(MESSAGE_FILE, 'r') as f:
        messages = f.readlines()

    return render_template('chat.html', messages=messages)

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    return redirect(url_for('login'))

@app.route('/matchmaking')
def matchmaking():
    # Redirect to login if the user is not logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Perform matchmaking
    matches = check_for_matches()  # Use the correct function name
    return render_template('matchmaking.html', matches=matches)

# WebSocket event for receiving and broadcasting messages
@socketio.on('message')
def handle_message(data):
    username = session.get('username')
    message = data['message']

    # Save the message to the file
    with open(MESSAGE_FILE, 'a') as f:
        f.write(f'{username}: {message}\n')

    # Broadcast the message to all connected clients
    emit('message', {'username': username, 'message': message}, broadcast=True)

    # Check for matches after every new message
    check_for_matches()

def check_for_matches():
    # Read all messages from the file
    with open(MESSAGE_FILE, 'r') as f:
        messages = f.readlines()

    # Initialize lists to store buy and sell requests
    buy_requests = []
    sell_requests = []

    # Process each message
    for message in messages:
        username, text = message.split(':', 1)
        text = text.strip().lower()

        # Tokenize the message and remove stopwords
        tokens = word_tokenize(text)
        tokens = [word for word in tokens if word.isalnum() and word not in stopwords.words('english')]

        # Check if the message contains "buy" or "sell"
        if 'buy' in tokens:
            product = extract_product_name(tokens)
            if product:
                buy_requests.append({'username': username.strip(), 'product': product})
        elif 'sell' in tokens:
            product = extract_product_name(tokens)
            if product:
                sell_requests.append({'username': username.strip(), 'product': product})

    # Find matches between buy and sell requests
    matches = []
    for buy in buy_requests:
        for sell in sell_requests:
            if buy['product'] == sell['product']:
                matches.append({
                    'buyer': buy['username'],
                    'seller': sell['username'],
                    'product': buy['product']
                })
                # Remove matched messages from the file
                remove_matched_messages(buy['username'], sell['username'], buy['product'])

    # Broadcast matches to all clients
    if matches:
        for match in matches:
            emit('match_found', {
                'buyer': match['buyer'],
                'seller': match['seller'],
                'product': match['product']
            }, broadcast=True)

def extract_product_name(tokens):
    # Extract the product name (assume it's the word after "buy" or "sell")
    for i, word in enumerate(tokens):
        if word in ['buy', 'sell'] and i + 1 < len(tokens):
            return tokens[i + 1]
    return None

def remove_matched_messages(buyer, seller, product):
    # Read all messages from the file
    with open(MESSAGE_FILE, 'r') as f:
        messages = f.readlines()

    # Filter out matched messages
    new_messages = []
    for message in messages:
        username, text = message.split(':', 1)
        text = text.strip().lower()
        if not (username.strip() == buyer and f'buy {product}' in text) and \
           not (username.strip() == seller and f'sell {product}' in text):
            new_messages.append(message)

    # Write the updated messages back to the file
    with open(MESSAGE_FILE, 'w') as f:
        f.writelines(new_messages)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')