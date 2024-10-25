from flask import Flask, render_template, redirect, url_for, request, flash, send_file, jsonify
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
from src.query_handler import process_query, get_all_vectors_in_namespace
from src.study_planner import (
    create_study_schedule,
    save_study_schedule,
    generate_notes_for_chunks,
    mark_day_completed
)
from datetime import datetime
from config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, COHERE_API_KEY, PINECONE_INDEX_NAME
import markdown
from bson.errors import InvalidId


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

@login_manager.unauthorized_handler
def unauthorized():
    flash('You need to be logged in to access this page.', 'warning')
    return redirect(url_for('login'))
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        
        if users.find_one({'username': username}):
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))
        
        users.insert_one({
            'username': username,
            'password': hashed_password,
            'first_name': first_name.capitalize(),
            'last_name': last_name.capitalize(),
            'email': email
        })
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
    if request.method == 'POST':
        try:
            file = request.files['file']
            num_days = int(request.form['num_days'])
            
            if num_days <= 0:
                flash('Please enter a valid number of days.', 'error')
                return redirect(url_for('upload'))
            
            # Upload file to GridFS
            file_id = fs.put(file, filename=file.filename, user_id=current_user.id)
            
            # Process the PDF
            file.seek(0)
            document_text = read_pdf(file)
            text_chunks = chunk_text(document_text)
            
            # Create and save study schedule
            schedule = create_study_schedule(text_chunks, num_days)
            schedule_id = save_study_schedule(mongo.db, file.filename, current_user.id, file_id, schedule)

            mongo.db['fs.files'].update_one(
                {'_id': ObjectId(file_id)},
                {'$set': {'schedule_id': schedule_id}}
            )
            
            # Store embeddings in Pinecone
            namespace = f"user_{current_user.id}_file_{file_id}"
            store_embeddings_in_pinecone(namespace, index, text_chunks)
            
            return redirect(url_for('study_schedule', schedule_id=schedule_id))
            
        except Exception as e:
            print(f"Error during file upload: {e}")
            flash('An error occurred during file upload. Please try again.', 'error')
            return redirect(url_for('upload'))
            
    return render_template('upload.html')

@app.route('/study/<schedule_id>')
@login_required
def study_schedule(schedule_id):
    schedule = mongo.db.study_schedules.find_one({'_id': ObjectId(schedule_id)})
    if not schedule or schedule['user_id'] != current_user.id:
        flash('Schedule not found or access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get the file information
    file_info = mongo.db['fs.files'].find_one({'_id': ObjectId(schedule['file_id'])})
    if file_info:
        schedule['title'] = file_info['filename']
        schedule['file_id'] = str(file_info['_id'])
    
    user_pdfs = fs.find({'user_id': current_user.id})
    user = users.find_one({'_id': ObjectId(current_user.id)})
    
    return render_template('study_schedule.html', 
                         schedule=schedule,
                         user_pdfs=user_pdfs,
                         user=user)

@app.route('/generate_notes/<schedule_id>/<date>')
@login_required
def generate_daily_notes(schedule_id, date):
    schedule = mongo.db.study_schedules.find_one({'_id': ObjectId(schedule_id)})
    if not schedule or schedule['user_id'] != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        day_data = schedule['schedule'][date]
        if day_data['generated']:
            return jsonify({'success': True, 'notes': day_data['notes']})
        
        day_number = list(schedule['schedule'].keys()).index(date) + 1
        total_days = len(schedule['schedule'])
        notes = generate_notes_for_chunks(day_data['chunks'], day_number, total_days)
        
        mongo.db.study_schedules.update_one(
            {'_id': ObjectId(schedule_id)},
            {
                '$set': {
                    f'schedule.{date}.generated': True,
                    f'schedule.{date}.notes': notes
                }
            }
        )
        
        return jsonify({'success': True, 'notes': notes})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/mark_complete/<schedule_id>/<date>', methods=['POST'])
@login_required
def mark_complete(schedule_id, date):
    if mark_day_completed(mongo.db, ObjectId(schedule_id), date):
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

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

@app.route('/dashboard')
@login_required
def dashboard():
    user_pdfs = fs.find({'user_id': current_user.id})  
    user = users.find_one({'_id': ObjectId(current_user.id)}) 
    if user:
        print(f"User: {user['first_name']}")
    return render_template('dashboard.html', user_pdfs=user_pdfs, user = user)

@app.route('/profile')
@login_required
def profile():
    user = users.find_one({'_id': ObjectId(current_user.id)}) 
    return render_template('profile.html', user=user)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']

    users.update_one(
        {'_id': ObjectId(current_user.id)},
        {'$set': {
            'first_name': first_name.capitalize(),
            'last_name': last_name.capitalize(),
            'email': email
        }}
    )
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout successful!', 'success')
    return redirect(url_for('home'))

@app.route('/query', methods=['POST'])
@login_required
def query():
    data = request.json
    query_text = data.get('query')
    pdf_id = data.get('pdf_id')
    print(f"Query: {query_text}, PDF ID: {pdf_id}")
    
    if not query_text or not pdf_id:
        return jsonify({'error': 'No query or PDF ID provided'}), 400

    # Generate a unique namespace for the current user and PDF
    namespace = f"user_{current_user.id}_file_{pdf_id}"
    print(f"Namespace: {namespace}")

    try:
        # Process query and generate answer
        generated_answer = process_query(query_text, COHERE_API_KEY, namespace)
        generated_answer = markdown.markdown(generated_answer)
        # print(get_all_vectors_in_namespace(namespace))
        print(f"Generated answer: {generated_answer}")
        return jsonify({'answer': generated_answer})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings')
@login_required
def settings():
    user_pdfs = fs.find({'user_id': current_user.id})
    return render_template('settings.html', user_pdfs=user_pdfs)

@app.route('/delete_pdf/<pdf_id>', methods=['POST'])
@login_required
def delete_pdf(pdf_id):
    try:
        # Verify the PDF belongs to the current user
        pdf = fs.find_one({'_id': ObjectId(pdf_id), 'user_id': current_user.id})
        if not pdf:
            flash('PDF not found or access denied.', 'error')
            return redirect(url_for('settings'))
        
        # Delete associated study schedule if it exists
        schedule = mongo.db.study_schedules.find_one({'file_id': ObjectId(pdf_id)})
        if schedule:
            mongo.db.study_schedules.delete_one({'_id': schedule['_id']})
        
        # Delete the PDF from GridFS
        fs.delete(ObjectId(pdf_id))
        
        # Delete associated vectors from Pinecone
        namespace = f"user_{current_user.id}_file_{pdf_id}"
        index.delete(deleteAll='true', namespace=namespace)
        
        flash('PDF deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting PDF: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    try:
        # Delete all PDFs belonging to the user
        user_pdfs = fs.find({'user_id': current_user.id})
        for pdf in user_pdfs:
            # Delete associated study schedules
            schedule = mongo.db.study_schedules.find_one({'file_id': pdf._id})
            if schedule:
                mongo.db.study_schedules.delete_one({'_id': schedule['_id']})
            
            # Delete vectors from Pinecone
            namespace = f"user_{current_user.id}_file_{str(pdf._id)}"
            index.delete(deleteAll='true', namespace=namespace)
            
            # Delete the PDF
            fs.delete(pdf._id)
        
        # Delete user's study schedules
        mongo.db.study_schedules.delete_many({'user_id': current_user.id})
        
        # Delete the user
        users.delete_one({'_id': ObjectId(current_user.id)})
        
        # Log out the user
        logout_user()
        
        flash('Your account has been successfully deleted.', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        flash(f'Error deleting account: {str(e)}', 'error')
        return redirect(url_for('settings'))
    
if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=4040)
