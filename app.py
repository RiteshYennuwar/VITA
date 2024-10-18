from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import gridfs
import io
from bson import ObjectId
import os
from src.document_processor import read_pdf, chunk_text
from src.embedding_handler import store_embeddings_in_pinecone
from src.pinecone_manager import initialize_pinecone
from src.query_handler import process_query
from config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, COHERE_API_KEY

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/your_db'
mongo = PyMongo(app)
fs = gridfs.GridFS(mongo.db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
index = initialize_pinecone(PINECONE_API_KEY, PINECONE_ENVIRONMENT)

# User collection
users = mongo.db.users

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    print(f"Loading user: {user_id}")
    user = users.find_one({'_id': ObjectId(user_id)})
    if user:
        print("User found in database")
        return User(str(user['_id']))
    print("User not found")
    return None

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        
        if users.find_one({'username': username}):
            flash('Username already exists.','error')
            return redirect(url_for('register'))
        
        users.insert_one({'username': username, 'password': hashed_password})
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            login_user(User(user['_id']))
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password.', 'error') 
    return render_template('login.html')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    print(f"Current user: {current_user}")
    if request.method == 'POST':
        file = request.files['file']
        file_id = fs.put(file, filename=file.filename, user_id=current_user.id)
        flash('File uploaded successfully in mongo!', 'success')
        file.seek(0)
        document_text = read_pdf(file)
        flash('PDF processed successfully!', 'info')
        text_chunks = chunk_text(document_text)
        flash('Text chunked successfully!', 'info')
        namespace = f"user_{current_user.id}_file_{file_id}"
        store_embeddings_in_pinecone(namespace,index, text_chunks)
        flash('File uploaded successfully in pinecone!', 'success')
    return render_template('upload.html')


@app.route('/download/<filename>')
@login_required
def download(filename):
    file = fs.find_one({'filename': filename, 'user_id': current_user.id})
    if file:
        file_stream = io.BytesIO(file.read())  
        file_stream.seek(0) 
        return send_file(file_stream, download_name=filename, as_attachment=True)
    else:
        flash('File not found or access denied.','error')
        return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_pdfs = fs.find({'user_id': current_user.id})  
    return render_template('dashboard.html', user_pdfs=user_pdfs)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout successful!', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=4040)
