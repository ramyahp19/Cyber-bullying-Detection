import os
import pickle
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import string
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import json
import re  # for lightweight text preprocessing



# Download NLTK data if not already present
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('wordnet', quiet=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instagram.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

# Initialize cyberbullying detection components
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))
stop_words.update(list(string.punctuation))

# Load the trained model and word index
try:
    model = load_model('nagesh.h5')
    with open('word_to_index.pkl', 'rb') as f:
        word_to_index = pickle.load(f)
    max_len = 30
    print("Cyberbullying detection model loaded successfully")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None
    word_to_index = {}

def get_simple_pos(tag):
    if tag.startswith('J'):
        return wordnet.ADJ
    elif tag.startswith('V'):
        return wordnet.VERB
    elif tag.startswith('N'):
        return wordnet.NOUN
    elif tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN

def clean_text(text):
    words = word_tokenize(text)
    output_words = []
    for word in words:
        if word.lower() not in stop_words:
            pos = pos_tag([word])
            clean_word = lemmatizer.lemmatize(word, pos=get_simple_pos(pos[0][1]))
            output_words.append(clean_word.lower())
    return " ".join(output_words)

def sentences_to_indices(X, max_len):
    X_indices = np.zeros((len(X), max_len))
    for i, sentence in enumerate(X):
        sentence_words = [w.lower() for w in sentence.split()]
        j = 0
        for word in sentence_words:
            if word in word_to_index and j < max_len:
                X_indices[i, j] = word_to_index[word]
                j += 1
    return X_indices

def detect_cyberbullying(text):
    if model is None:
        return 0.0  # Default to no bullying if model not loaded
    
    cleaned_text = clean_text(text)
    text_indices = sentences_to_indices([cleaned_text], max_len)
    prediction = model.predict(text_indices)[0][0]
    return float(prediction)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, default='')
    profile_pic = db.Column(db.String(200), default='default_profile.png')
    reputation_score = db.Column(db.Float, default=10.0)  # Changed to Float
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', backref='followed', lazy='dynamic')
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower', lazy='dynamic')
    likes = db.relationship('Like', backref='user', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='post', lazy=True)
    likes = db.relationship('Like', backref='post', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    bullying_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Session validation middleware
@app.before_request
def before_request():
    # Skip for static files and auth pages
    if request.endpoint in ['static', 'login', 'register', 'logout']:
        return
    
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user is None:
            session.pop('user_id', None)
            flash('Session expired. Please log in again.', 'error')
            return redirect(url_for('login'))

# Helper function to get current user safely
def get_current_user():
    if 'user_id' not in session:
        return None
    return db.session.get(User, session['user_id'])

# Routes
@app.route('/')
def index():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    try:
        # Safely get following IDs
        following_ids = []
        try:
            following_ids = [f.followed_id for f in user.following.all()]
        except Exception as e:
            print(f"Error getting following list: {e}")
            following_ids = []
        
        following_ids.append(user.id)  # Include user's own posts
        
        # Get posts from users that the current user follows
        posts = Post.query.filter(Post.user_id.in_(following_ids)).order_by(Post.created_at.desc()).all()
        
        # Get suggestions for users to follow
        suggestions = []
        try:
            all_users = User.query.filter(User.id != user.id).all()
            suggestions = [u for u in all_users if u.id not in following_ids]
            suggestions = suggestions[:5]
        except Exception as e:
            print(f"Error getting suggestions: {e}")
        
        return render_template('index.html', user=user, posts=posts, suggestions=suggestions)
        
    except Exception as e:
        print(f"Error in index route: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            full_name=full_name
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/profile/<username>')
def profile(username):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    profile_user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=profile_user.id).order_by(Post.created_at.desc()).all()
    
    # Check if current user follows this profile
    is_following = False
    if profile_user.id != user.id:
        is_following = Follow.query.filter_by(
            follower_id=user.id, 
            followed_id=profile_user.id
        ).first() is not None
    
    return render_template('profile.html', user=user, profile_user=profile_user, posts=posts, is_following=is_following)

@app.route('/upload', methods=['POST'])
def upload_post():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    if 'image' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['image']
    caption = request.form.get('caption', '')
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        new_post = Post(
            image=filename,
            caption=caption,
            user_id=user.id
        )
        
        db.session.add(new_post)
        db.session.commit()
        
        flash('Post uploaded successfully!', 'success')
    
    return redirect(url_for('index'))

@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Check if user already liked the post
    existing_like = Like.query.filter_by(
        user_id=user.id,
        post_id=post_id
    ).first()
    
    if existing_like:
        # Unlike the post
        db.session.delete(existing_like)
        db.session.commit()
        return jsonify({'liked': False})
    else:
        # Like the post
        new_like = Like(
            user_id=user.id,
            post_id=post_id
        )
        db.session.add(new_like)
        db.session.commit()
        return jsonify({'liked': True})

@app.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Get JSON data
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    comment_text = data.get('comment', '').strip()
    
    if not comment_text:
        return jsonify({'error': 'Comment cannot be empty'}), 400
    
    # Check if user is restricted
    if user.reputation_score < 5:
        return jsonify({'error': 'Your account is restricted. You cannot comment on posts.'}), 403
    
    # Detect cyberbullying
    bullying_score = detect_cyberbullying(comment_text)
    
    # Create the comment
    new_comment = Comment(
        text=comment_text,
        user_id=user.id,
        post_id=post_id,
        bullying_score=bullying_score
    )
    
    db.session.add(new_comment)
    
    # Update user reputation if bullying is detected
    reputation_loss = 0
    if bullying_score > 0.4:
        # Decrease reputation by the bullying_score value
        reputation_loss = bullying_score
        user.reputation_score = max(0.0, user.reputation_score - reputation_loss)
        
        # Flash message for bullying detection
        flash(f'🚨 Cyberbullying detected! Your reputation score decreased by {reputation_loss:.2f} points. Current score: {user.reputation_score:.1f}/10', 'warning')
        
        # If reputation drops below 5, user is blocked
        if user.reputation_score < 5:
            flash('❌ Your account has been restricted due to low reputation score.', 'error')
    
    db.session.commit()
    
    # Return comment data for frontend
    return jsonify({
        'success': True,
        'comment': {
            'id': new_comment.id,
            'text': new_comment.text,
            'author': user.username,
            'author_pic': user.profile_pic,
            'created_at': new_comment.created_at.strftime('%b %d, %Y at %I:%M %p'),
            'bullying_detected': bullying_score > 0.4,
            'user_reputation': user.reputation_score,
            'reputation_loss': reputation_loss
        }
    })

@app.route('/follow/<int:user_id>', methods=['POST'])
def follow_user(user_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Check if user is trying to follow themselves
    if user_id == user.id:
        return jsonify({'error': 'Cannot follow yourself'}), 400
    
    # Check if already following
    existing_follow = Follow.query.filter_by(
        follower_id=user.id,
        followed_id=user_id
    ).first()
    
    if existing_follow:
        # Unfollow
        db.session.delete(existing_follow)
        db.session.commit()
        return jsonify({'following': False})
    else:
        # Check if user reputation allows following
        if user.reputation_score < 5:
            return jsonify({'error': 'Your account is restricted. You cannot follow other users.'}), 403
        
        # Follow
        new_follow = Follow(
            follower_id=user.id,
            followed_id=user_id
        )
        db.session.add(new_follow)
        db.session.commit()
        return jsonify({'following': True})

@app.route('/explore')
def explore():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Get random posts from users not followed by current user
    following_ids = []
    try:
        following_ids = [f.followed_id for f in user.following.all()]
    except:
        following_ids = []
    following_ids.append(user.id)
    
    posts = Post.query.filter(~Post.user_id.in_(following_ids)).order_by(db.func.random()).limit(20).all()
    
    # If no posts found, show some random posts
    if not posts:
        posts = Post.query.order_by(db.func.random()).limit(20).all()
    
    return render_template('explore.html', user=user, posts=posts)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user.full_name = request.form.get('full_name', user.full_name)
        user.bio = request.form.get('bio', user.bio)
        user.email = request.form.get('email', user.email)
        
        # Handle profile picture upload
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                user.profile_pic = filename
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('settings'))
    
    return render_template('settings.html', user=user)

@app.route('/search')
def search():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    query = request.args.get('q', '')
    users = []
    
    if query:
        users = User.query.filter(
            (User.username.contains(query)) | 
            (User.full_name.contains(query))
        ).all()
    
    return render_template('search.html', user=user, users=users, query=query)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
