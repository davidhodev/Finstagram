from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

# Instantiating the MySQL connections
connection = pymysql.connect(host="localhost",
                             user="root",
                             password="root",
                             db="Finstagram",
                             charset="utf8mb4",
                             port=8889,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

#Making sure that the log in is required
def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

# Default page
#Home page if logged in and index.html if not logged in
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

# Home page that shows all available photos
#Currently shows all photos (Need to only photos that are visibile to the logged in user.)
@app.route("/home")
@login_required
def home():
    user = session['username']
    cursor = connection.cursor();
    query = 'SELECT * FROM Photo ORDER BY timestamp DESC' # Natural Join Tag GROUP BY photoID
    cursor.execute(query)
    data = cursor.fetchall()
    query2 = 'SELECT * FROM Tag Natural Join Person WHERE acceptedTag = 1'
    cursor.execute(query2)
    tagData = cursor.fetchall()
    cursor.close()
    return render_template('home.html', username=user, posts=data, tagPosts = tagData)


#Loads the image
@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")


#Page that allows you to select the blogger
@app.route('/select_blogger')
@login_required
def select_blogger():
    #check that user is logged in
    #username = session['username']
    #should throw exception if username not found

    cursor = connection.cursor();
    query = 'SELECT DISTINCT username FROM Person'
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template('select_blogger.html', user_list=data)


#Manage Followers and Tags
@app.route('/manage')
@login_required
def manage():
    username = session['username']
    cursor = connection.cursor();
    query = 'SELECT * FROM Tag NATURAL JOIN Photo WHERE acceptedTag = 0 AND username = %s'
    cursor.execute(query, (username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('manage.html', tagData=data)

@app.route('/tagAcceptOrDecline')
@login_required
def tagAcceptOrDecline():
    username = session['username']
    print(request.form)
    if ("accept" in request.form):
        print ("ACCEPTED")
    elif ("decline" in request.form):
        print ("DECLINED")
    else:
        print ("DIDN'T WORK")
    # print("ACCEPTED TAG TEST:", acceptedTag)
    cursor = connection.cursor();
    query = 'SELECT * FROM Tag NATURAL JOIN Photo WHERE acceptedTag = 0 AND username = %s'
    cursor.execute(query, (username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('manage.html', tagData=data)



@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)



# Post the image
@app.route('/post', methods=['GET', 'POST'])
def post():
    username = session['username']
    cursor = connection.cursor();
    blog = request.form['blog'] #Blog is the caption of the image
    image_file = request.files.get("pic", "")
    image_name = image_file.filename
    filepath = os.path.join(IMAGES_DIR, image_name)
    image_file.save(filepath)
    try:
        #Checks to see if allFollowers box is checked.
        # Visible to all Followers

        allFollowers = request.form['allFollowers']
        query = 'INSERT INTO Photo (caption, filePath, photoOwner, timestamp, allFollowers) VALUES(%s, %s, %s, %s, %s)'
        cursor.execute(query, (blog, image_name, username, time.strftime('%Y-%m-%d %H:%M:%S'), '1' ))
    except:
        #Checks to see if allFollowers box is not checked
        # Visible to Close Friends Group

        query = 'INSERT INTO Photo (caption, filePath, photoOwner, timestamp, allFollowers) VALUES(%s, %s, %s, %s, %s)'
        cursor.execute(query, (blog, image_name, username, time.strftime('%Y-%m-%d %H:%M:%S'), '0' ))

    connection.commit()
    cursor.close()
    return redirect(url_for('home'))


# Showinbg posts from a specific user
@app.route('/show_posts', methods=["GET", "POST"])
def show_posts():
    poster = request.args['poster']
    cursor = connection.cursor();
    query = 'SELECT * FROM Photo WHERE photoOwner = %s ORDER BY timestamp DESC'
    cursor.execute(query, (poster))
    data = cursor.fetchall()
    cursor.close()
    return render_template('show_posts.html', poster_name=poster, posts=data)




# When you press Register
@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO Person (username, password, fname, lname) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)

#
@app.route("/follow", methods=["GET", "POST"])
def follow():
    username = session['username']
    print(username)
    poster = request.args['poster']
    print(poster)

    cursor = connection.cursor();
    if (username != poster):
        query = 'INSERT INTO Follow (followerUsername, followeeUsername, acceptedfollow) VALUES(%s, %s, %s)'
        cursor.execute(query, (username, poster, 0))
    else:
        print("ERROR. TRYING TO FOLLOW YOURSELF!")

    connection.commit()
    cursor.close()
    return redirect(url_for('home'))
    # return render_template('show_posts.html', poster_name=poster, posts=data)



@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")


if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()
