import time
import picamera
import pymysql

#for generating a unique photo path every time
import os
from datetime import datetime
import uuid

#for api session
import requests

#define a path that is on the rasberry pi
photo_dir = "/home/pi/current_photos"
os.makedirs(photo_dir, exist_ok=True) #confirm the directory exists


def get_logged_in_user():
    response = requests.get('http://localhost:3000/api/logged-in-user')
    if response.status_code == 200:
        return response.json().get('userID')
    return None

#generate a unique filename using timestamp and UUID
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  #formats into year-month-day_hour-minute-second
unique_id = uuid.uuid4().hex[:8]  # generates a short uuid in case 2 photos are captured at the exact same second
file_name = f"wam_{timestamp}_{unique_id}.jpg"

#create the full path/file name
photo_path = os.path.join(photo_dir, file_name)


#start the camera
camera = picamera.PiCamera() 
camera.capture(photo_path)
#print(f"Photo saved at {photo_path}")
camera.close()


# Database connection
connection = pymysql.connect(
    host = 'riku.shoshin.uwaterloo.ca',
    user = 'a498wang',
    password ='dbz4SLMtIM0bdgn8Q0%0',
    database= 'db101_a498wang'
)

def insert_photo(photo_file, user_id):
    try:
        with connection.cursor() as cursor:
        # Read the image file as binary
            with open(photo_path, 'rb') as file:
                binary_data = file.read()
        # Insert the image into the database
                sql = "INSERT INTO allPhotos (photoFile, photoDate, user) VALUES (%s, %s, %s)"
                cursor.execute(sql, (photo_file, timestamp, user_id))
                connection.commit()
                print("Photo inserted successfully!")
    finally:
        connection.close()

#call function
insert_photo(photo_path, get_logged_in_user())