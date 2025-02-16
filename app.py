from flask import Flask, request, render_template, redirect, url_for, jsonify, session
#import mysql.connector
import upload
import requests
import random
import time
#from mysql.connector import Error
#import pymysql
from flask_session import Session

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session handling
# Track countdown state and time
countdown_active = True
seconds = 6
API_SERVER = "http://localhost:3000"

app.secret_key = 'watamoment123'
app.config['SESSION_PERMANENT'] = False #should this be T or F
app.config['SESSION_USE_SIGNER'] = True #should this be T or F
'''
# Database connection
connection = pymysql.connect(
    host = 'riku.shoshin.uwaterloo.ca',
    user = 'a498wang',
    password ='dbz4SLMtIM0bdgn8Q0%0',
    database= 'db101_a498wang'
)
'''
# Routes for views
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # Render the login page
        return render_template('login.html')

    if request.method == 'POST':
        # Extract username and password from the form
        username = request.form.get('username')
        password = request.form.get('password')

        # Prepare payload for the Node.js login API
        payload = {"username": username, "password": password}

        try:
            print(f"[LOGIN] Attempting login for user: {username}")
            # Send login request to Node.js
            response = requests.post(f"{API_SERVER}/wamUserLogin", json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                print(f"[LOGIN] Response from Node.js: {response.status_code} - {data}")

                # Check for errors in the Node.js response
                if "error" in data:
                    print(f"[LOGIN] Error from Node.js: {data['error']}")
                    return render_template('login.html', error=data["error"])

                # Handle successful login
                elif "redirect" in data:
                    print(f"[LOGIN] Login successful for user: {username}")
                    # Save session in Flask
                    session['username'] = username
                    print("[LOGIN] Flask session updated.")

                    # Sync session with Node.js
                    node_payload = {"username": username}
                    try:
                        sync_response = requests.post(f"{API_SERVER}/sync-session", json=node_payload, timeout=5)
                        if sync_response.status_code == 200:
                            print(f"[LOGIN] Session synced with Node.js: {sync_response.text}")
                        else:
                            print(f"[LOGIN] Failed to sync session with Node.js: {sync_response.status_code} - {sync_response.text}")
                    except Exception as e:
                        print(f"[LOGIN] Error syncing session with Node.js: {e}")

                    # Redirect to dashboard or appropriate page
                    return redirect(data["redirect"])
                else:
                    print("[LOGIN] Unexpected response from Node.js.")
                    return render_template('login.html', error="Unexpected response from server.")
            else:
                # Handle invalid credentials
                print(f"[LOGIN] Invalid credentials: {response.status_code}")
                return render_template('login.html', error="Invalid username or password.")

        except requests.exceptions.RequestException as e:
            # Handle connection issues
            print(f"[LOGIN] Error connecting to Node.js server: {e}")
            return render_template('login.html', error="Unable to connect to the server.")
        except Exception as e:
            # Catch any other errors
            print(f"[LOGIN] Unexpected error: {e}")
            return render_template('login.html', error="An unexpected error occurred.")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        classCode = request.form.get('classCode')
        firstName = request.form.get('fname')
        lastName = request.form.get('lname')

        if classCode != 'SE101':
            return render_template('signup.html', message="Invalid class code!")

        payload = {
            "username": username, 
            "password": password, 
            "classCode": classCode, 
            "firstName": firstName, 
            "lastName": lastName
        }
        try:
            # Check if the user already exists
            response = requests.get(f"{API_SERVER}/getWamUser/{username}")
            if response.status_code == 200 and response.json().get("success"):
                return render_template('signup.html', message="Username is already taken.")
            
            # Create a new user
            response = requests.post(f"{API_SERVER}/createWamUser", json=payload)
            if response.status_code == 200 and response.json().get("success"):
                session['username'] = username  # Log the user in immediately
                return redirect(url_for('dashboard'))
            return render_template('signup.html', message="Unable to create account.")
        except Exception as e:
            print(f"Signup error: {e}")
            return render_template('signup.html', message="Unable to connect to the server.")
 
@app.route('/logout', methods=['POST'])
def logout():
    print("Logout route hit")
    try:
        print(f"Sending logout request to {API_SERVER}/logout")
        response = requests.post(f"{API_SERVER}/logout", timeout=5)
        print(f"Received response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            session.clear()  # Clear Flask session
            print("Flask session cleared")
            return redirect('/')  # Redirect to the homepage
        else:
            print("Failed to log out on Node.js side")
            return render_template('dashboard.html', message="Failed to log out. Please try again.")
    except Exception as e:
        print(f"Error during logout: {e}")
        return render_template('dashboard.html', message="Unable to connect to the server.")

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/photo')  # Change this route to '/photo' or whatever fits your use case
def photo():
    global countdown_active, seconds
    upload.main()
    return render_template('photo.html', countdown_active=countdown_active, seconds=seconds)

@app.route('/update_countdown', methods=['POST'])
def update_countdown():
    global seconds, countdown_active

    # Decrease countdown every second until it reaches 0
    if countdown_active and seconds > 0:
        seconds -= 1
    else:
        countdown_active = False

    return jsonify({'active': countdown_active, 'countdown': seconds})

@app.route('/classphotos')
def viewclassphotos():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if user not in session
    try:
        # Fetch private photos for the logged-in user
        classCode = 'SE101'
        response = requests.get(f"{API_SERVER}/getPublicPhotos/{classCode}")
        print(f"API Response Status: {response.status_code}")  # Debug response status
        print(f"API Response Content: {response.json()}")  # Debug response content
        
        if response.status_code == 200:
            photos = response.json()  # List of photo objects
        else:
            photos = []  # Default to empty list if API fails

        # Pass photos to the template
        return render_template('viewclassphotos.html', photos=photos)
    except Exception as e:
        print(f"Error fetching photos for class {e}")
        return render_template('viewclassphotos.html', error="Unable to load photos.")

@app.route('/yourphotos')
def viewyourphotos():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if user not in session

    username = session['username']  # Get logged-in username
    try:
        # Fetch private photos for the logged-in user
        response = requests.get(f"{API_SERVER}/getPrivatePhotos/{username}")
        if response.status_code == 200:
            photos = response.json()  # List of photo objects
        else:
            photos = []  # Default to empty list if API fails

        # Pass photos to the template
        return render_template('viewyourphotos.html', photos=photos)
    except Exception as e:
        print(f"Error fetching photos for user {username}: {e}")
        return render_template('viewyourphotos.html', error="Unable to load photos.")

comments = [
        "cutie!", "stunner!", "looking gorgeous!", "amazing!", 
        "absolutely glowing!", "love this look!", "fantastic!", 
        "queen behavior!", "iconic!", "serving looks!", "perfect!", 
        "goals!!!", "oh not your best eh", "obsessed!", "slaying!", 
        "beautiful!"
    ]


@app.route('/postphoto', methods=['GET', 'POST'])
def postphoto():
    if request.method == 'GET':
        try:
            # Fetch photos for CURRENT-SESSION
            photo_response = requests.get(f"{API_SERVER}/getPrivatePhotos/CURRENT-SESSION")
            if photo_response.status_code != 200:
                return "Failed to fetch photos.", 500
            
            photos = photo_response.json()[:4]  # Limit to 4 photos
            photo_urls = [
                {"id": photo["photoID"], "url": f"https://drive.google.com/thumbnail?id={photo['photoID']}"}
                for photo in photos
            ]

            # Fetch users for the dropdown
            class_code = "SE101"  # Replace with the actual class code for the session
            user_response = requests.get(f"{API_SERVER}/getAllUsers/{class_code}")
            if user_response.status_code != 200:
                return "Failed to fetch users.", 500
            
            users = user_response.json()  # Get the list of users

            # Render the template with photos and users
            return render_template(
                'postphoto.html',
                photos=photo_urls,
                users=users
            )
        except Exception as e:
            return f"An error occurred: {str(e)}", 500

    elif request.method == 'POST':
        # Get the selected photos and users from the form
        selected_photos = request.form.getlist('selected_photos')  # Get selected photos (list)
        selected_users = request.form.getlist('selected_users')  # Get selected users (list)
        action = request.form.get('action')  # Action to be performed (sendToUser, finish, etc.)
        username = session['username']  # Get logged-in username
        print(f"Session username: {username}, Action: {action}")
        classCode='SE101'
        
        # Validate that at least one photo is selected if action is not finish
        if not selected_photos and action != "finish":
            return "No photos selected.", 400

        # Perform actions based on the selected action
        if action == "postToClass":
            for photo_id in selected_photos:
                requests.post(f"{API_SERVER}/assignPhotoToUser/{photo_id}/{classCode}")
            return redirect('/postphoto')
        elif action == "sendToSelf":
            for photo_id in selected_photos:
                print(f"Assigning photo {photo_id} to {username}")  # Debugging log
                requests.post(f"{API_SERVER}/assignPhotoToUser/{photo_id}/{username}")
            return redirect('/postphoto')
        elif action == "sendToUser" and selected_users:
            # For each selected user, assign each selected photo to them
            for user_id in selected_users:
                for photo_id in selected_photos:
                    requests.post(f"{API_SERVER}/assignPhotoToUser/{photo_id}/{user_id}")
            return redirect('/postphoto')
        elif action == "finish":
            print("Deleting photos for CURRENT-SESSION")
            user = 'CURRENT-SESSION'
            try:
                response = requests.delete(f"{API_SERVER}/deletePhotoFromUser/{user}")
                print(f"API Response: {response.status_code}, {response.text}")
                if response.status_code != 200:
                    return f"Failed to delete photos for {user}.", 500
            except Exception as e:
                print(f"Error during DELETE request: {e}")
                return f"Error during DELETE request: {e}", 500
            return redirect('/dashboard')

        return f"Action '{action}' performed on photos {selected_photos} for users {selected_users}.", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)