from flask import Flask,render_template,redirect,request,send_from_directory,url_for,g,session,flash
#from flask import *
from tensorflow.keras.models import load_model
import tensorflow as tf
from keras.backend import set_session
import os
from PIL import Image
import numpy as np
from werkzeug.utils import secure_filename
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

global sess
sess = tf.compat.v1.Session()
tf.compat.v1.keras.backend.get_session(sess)
global model
model = load_model('model.h5')
global graph
graph = tf.compat.v1.get_default_graph()

#flask app configuration
app = Flask(__name__,template_folder='templates')
UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER 
#DB configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'flask'

app.secret_key = 'secretkey'

mysql = MySQL(app)

def makePredictions(path):
  #Method to predict if the image uploaed is healthy or pneumonic
  img = Image.open(path) # we open the image
  img_d = img.resize((224,224))
  # we resize the image for the model
  rgbimg=None
  #We check if image is RGB or not
  if len(np.array(img_d).shape)<3:
    rgbimg = Image.new("RGB", img_d.size)
    rgbimg.paste(img_d)
  else:
      rgbimg = img_d
  rgbimg = np.array(rgbimg,dtype=np.float32)
  rgbimg = rgbimg.reshape((1,224,224,3))
  predictions = model.predict(rgbimg) #using model for prediction
  a = int(np.argmax(predictions))
  #checking prediction class and returing result
  if a==1:
    a = "pneumonic"
  else:
    a="healthy"
  return a

@app.route("/")
def index():
    return render_template("index.html") 

#for patients to register
@app.route("/register", methods=['GET','POST'])
def register():
    if request.method=='POST':
        # Fetch form data
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        doctor = request.form['physician']
        referal = request.form['clinic']
        docphone = request.form['phyphone'] 
        doc_comment = request.form['comment']
        add_comment = request.form['addcomment']
        #creating DB cursor
        cur = mysql.connection.cursor()
        #sql querry to store patient details in DB
        cur.execute("INSERT INTO register(patient,age,gender,phone,email,address,doctor,referal,doc_phone,doc_comm,add_comm) VAlUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(name,age,gender,phone,email,address,doctor,referal,docphone,doc_comment,add_comment))
        mysql.connection.commit()
        cur.close()
        #redirecting to user dashboard 
        return redirect(url_for("dashboard"))
    
    return render_template('register.html')

#dashboard for user to upload X-ray image and get result
@app.route("/dashboard", methods=['GET','POST'])
def dashboard():
    if request.method=='POST':
        #Check for file input and handle exceptions
        if 'img' not in request.files:
            return render_template('home.html',filename="unnamed.png",message="Please upload an file")
        f = request.files['img'] 
        filename = secure_filename(f.filename) 
        if f.filename=='':
            return render_template('home.html',filename="unnamed.png",message="No file selected")
        if not ('jpeg' in f.filename or 'png' in f.filename or 'jpg' in f.filename):
            return render_template('home.html',filename="unnamed.png",message="please upload an image with .png or .jpg/.jpeg extension")
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        if len(files)==1:
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
        else:
            files.remove("unnamed.png")
            file_ = files[0]
            os.remove(app.config['UPLOAD_FOLDER']+'/'+file_)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
        #calling predction function
        prediction = makePredictions(os.path.join(app.config['UPLOAD_FOLDER'],filename)) 
        cur = mysql.connection.cursor()
        number_of_rows = cur.execute("SELECT * FROM register")
        #saving prediction result into DB
        cur.execute("UPDATE register SET results=%s WHERE regno=%s",(prediction,number_of_rows))
        mysql.connection.commit()
        cur.close()
        return render_template('home.html',filename=f.filename,message=prediction,show=True)
    return render_template('home.html',filename='unnamed.png')

#admin login page
@app.route("/admin", methods=['GET','POST'])
def authenticate():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password))
        # Fetch one record and return result
        account = cursor.fetchone()
        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            # Redirect to home page
            return redirect(url_for("admindashboard"))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
    # Show the login form with message (if any)
    return render_template('admin_login.html', msg=msg)

#admin dashboard after login
@app.route("/admindashboard", methods=['GET'])
def admindashboard():
    cur = mysql.connection.cursor()
    value=cur.execute('SELECT * FROM register')
    if value >0:
        data = cur.fetchall()
        return render_template("admindash.html", data=data)

@app.route("/logout")
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('index'))

if __name__=="__main__":
    app.run(debug=True)
    