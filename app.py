from flask import Flask, render_template, request, redirect, url_for, session
from flask import jsonify
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
import re
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

@app.route('/get_notifications')
def get_notifications():
    # Simulate fetching a notification (you can replace this with actual logic)
    buyer_username = "buyer_user"
    seller_username = "ali"
    product_name = "ABC"
    return notify_user(buyer_username, seller_username, product_name)

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
    process_latest_message()


def process_latest_message():
    # Read the latest message from chat_messages.txt
    with open("chat_messages.txt", "r") as chat_file:
        lines = chat_file.readlines()
        if not lines:
            return  # No messages to process

        latest_message = lines[-1].strip()  # Get the latest message

    # Extract username and message content
    username, message = latest_message.split(": ", 1)

    # Check if the message is related to buying or selling
    if "buy" in message.lower():
        product_name = extract_product_name(message)
        if product_name:
            with open("buy_product.txt", "a") as buy_file:
                buy_file.write(f"{username}: {product_name}\n")
            match_making(product_name, username)

    elif "sell" in message.lower():
        product_name = extract_product_name(message)
        if product_name:
            with open("sell_product.txt", "a") as sell_file:
                sell_file.write(f"{username}: {product_name}\n")
            match_making(product_name, username)

def extract_product_name(message):
    # Use regex to extract the product name from the message
    match = re.search(r'(buy|sell)\s+(\w+)', message, re.IGNORECASE)
    if match:
        return match.group(2)
    return None

def match_making(product_name, username):
    # Check if product is available for sale
    with open("sell_product.txt", "r") as sell_file:
        for line in sell_file:
            line = line.strip()
            if not line or ": " not in line:
                continue  # Skip empty or malformed lines

            try:
                seller_username, sell_product = line.split(": ", 1)
                if sell_product.lower() == product_name.lower():
                    notify_user(username, seller_username, product_name)
                    return
            except ValueError:
                print(f"Skipping malformed line: {line}") 

    # # Check if someone wants to buy the product
    # with open("buy_product.txt", "r") as buy_file:
    #     for line in buy_file:
    #         line = line.strip()
    #         if not line or ": " not in line:
    #             continue  # Skip empty or malformed lines

    #         try:
    #             buyer_username, buy_product = line.split(": ", 1)
    #             if buy_product.lower() == product_name.lower():
    #                 notify_user(buyer_username, username, product_name)
    #                 return
    #         except ValueError:
    #             print(f"Skipping malformed line: {line}") 

# def notify_user(buyer_username, seller_username, product_name):
#     # Send a notification to the buyer
#     notification_message = f"Notification: {seller_username} is selling {product_name}. You can contact them to buy it."
    
#     # Append the notification to the chat_messages.txt file
#     with open("chat_messages.txt", "a") as chat_file:
#         chat_file.write(f"System: {notification_message}\n")

def notify_user(buyer_username, seller_username, product_name):
    notification_message = f"Notification: {seller_username} is selling {product_name}. You can contact them to buy it."
    
    # Append the notification to chat_messages.txt
    with open("chat_messages.txt", "a") as chat_file:
        chat_file.write(f"System: {notification_message}\n")

    # Emit notification via WebSocket
    emit('notification', {
        "buyer_username": buyer_username,
        "seller_username": seller_username,
        "product_name": product_name,
        "notification_message": notification_message
    }, broadcast=True)
    
    # You can also implement additional notification mechanisms here (e.g., email, push notification)



if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')