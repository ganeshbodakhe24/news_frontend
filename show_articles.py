from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
from flask import flash
from flask_mail import Mail, Message
# for search article
from sentence_transformers import SentenceTransformer, util
import torch


import MySQLdb

app = Flask(__name__)
app.secret_key = 'your_secret_key'
# for search article
model = SentenceTransformer('all-MiniLM-L6-v2')


from datetime import timedelta

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Keep the session alive for 7 days

# MySQL Configurations
app.config['MYSQL_HOST'] = 'sql10.freesqldatabase.com'
app.config['MYSQL_USER'] = 'sql10783591'
app.config['MYSQL_PASSWORD'] = 'ID27NUfEnS'
app.config['MYSQL_DB'] = 'sql10783591'
mysql = MySQL(app)

# Mail Send

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'ehr.management.team@gmail.com'  # Your Gmail address
app.config['MAIL_PASSWORD'] = 'rfwpembbvqvpmqps'     # Gmail app password (recommended)
app.config['MAIL_DEFAULT_SENDER'] = ('Your App Name', 'ehr.management.team@gmail.com')

mail = Mail(app)

@app.route('/')
def home():
    # Check if user is already logged in
    if 'username' in session:
        return redirect(url_for('articles'))  # Redirect to the articles page if logged in
    return render_template('summaries.html')  # Render the login page if not logged in


@app.route('/articles')
def articles():
    logged_in = 'username' in session
    return render_template('summaries.html', logged_in=logged_in)


# Content-Based Matching Function
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    logged_in = 'username' in session
    username = session.get('username') if logged_in else None

    if not query:
        # No query: return latest articles (limit 20 for performance)
        cursor.execute('''
            SELECT id, title, summary, question, link, image_url AS category_image, category, timestamp, sentiment
            FROM articles
            ORDER BY timestamp DESC
            LIMIT 20
        ''')
        articles = cursor.fetchall()

        for article in articles:
            if article['timestamp']:
                article['timestamp'] = article['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

        return render_template(
            'search_results.html',
            articles=articles,
            query=query,
            logged_in=logged_in,
            username=username
        )

    # 1. Fetch candidate articles (limit 100 for speed)
    cursor.execute('''
        SELECT id, title, summary, question, link, image_url AS category_image, category, timestamp, sentiment
        FROM articles
        LIMIT 100
    ''')
    articles = cursor.fetchall()

    # 2. Prepare text data to embed
    texts = [' '.join(filter(None, [a.get('title'), a.get('summary'), a.get('question')])) for a in articles]

    # 3. Encode all articles and query
    article_embeddings = model.encode(texts, convert_to_tensor=True)
    query_embedding = model.encode(query, convert_to_tensor=True)

    # 4. Compute cosine similarity
    cosine_scores = util.cos_sim(query_embedding, article_embeddings)[0]
    top_results = torch.topk(cosine_scores, k=min(10, len(articles)))

    # 5. Prepare matched articles
    matched_articles = []
    for score, idx in zip(top_results.values, top_results.indices):
        art = articles[idx.item()]
        art['similarity_score'] = score.item()
        if art['timestamp']:
            art['timestamp'] = art['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        matched_articles.append(art)

    return render_template(
    'search_results.html',
    articles=matched_articles,
    query=query,
    logged_in=logged_in,
    username=username
)



@app.route('/articles_data')
def articles_data():
    if 'username' in session:
        username = session['username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT preferences FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        preferences = account['preferences'].split(',') if account['preferences'] else []

        if preferences:
            placeholders = ', '.join(['%s'] * len(preferences))
            query = f'''
                SELECT id,title, summary, link, image_url, category, timestamp
                FROM articles
                WHERE category IN ({placeholders})
                ORDER BY timestamp DESC
                LIMIT 5
            '''
            cursor.execute(query, preferences)
        else:
            cursor.execute('''
                SELECT id,title, summary, link, image_url, category, timestamp
                FROM articles
                ORDER BY timestamp DESC
                LIMIT 5
            ''')
        articles = cursor.fetchall()
        for article in articles:
            if article['timestamp']:
                article['timestamp'] = article['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(articles)
    else:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            SELECT id,title, summary, link, image_url, category, timestamp
            FROM articles
            ORDER BY timestamp DESC
            LIMIT 5
        ''')
        articles = cursor.fetchall()
        for article in articles:
            if article['timestamp']:
                article['timestamp'] = article['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(articles)
    
@app.route('/all_trending_articles')
def trending_data():
    if 'username' in session:
        username = session['username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT preferences FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        preferences = account['preferences'].split(',') if account['preferences'] else []

        if preferences:
            placeholders = ', '.join(['%s'] * len(preferences))
            query = f'''
                SELECT id,title, summary, link, image_url, category, timestamp
                FROM articles
                WHERE category IN ({placeholders})
                ORDER BY timestamp DESC
            '''
            cursor.execute(query, preferences)
        else:
            cursor.execute('''
                SELECT id,title, summary, link, image_url, category, timestamp
                FROM articles
                ORDER BY timestamp DESC
            ''')
        articles = cursor.fetchall()
        for article in articles:
            if article['timestamp']:
                article['timestamp'] = article['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(articles)
    else:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            SELECT id,title, summary, link, image_url, category, timestamp
            FROM articles
            ORDER BY timestamp DESC
        ''')
        articles = cursor.fetchall()
        for article in articles:
            if article['timestamp']:
                article['timestamp'] = article['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(articles)

@app.route('/all_trending_articles_page')
def all_trending_articles_page():
    logged_in = 'username' in session
    username = session.get('username') if logged_in else None
    return render_template('trending.html', logged_in=logged_in, username=username)


@app.route('/About')
def About():
    logged_in = 'username' in session
    username = session.get('username') if logged_in else None
    return render_template('About.html', logged_in=logged_in, username=username)



@app.route('/navbar')
def navbar():
    return render_template('navbar.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('articles'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s OR email = %s', (username, email))
        account = cursor.fetchone()
        
        if account:
            msg = 'Username or email already exists!'
        else:
            cursor.execute('INSERT INTO accounts (username, password, email) VALUES (%s, %s, %s)', (username, password, email))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
            return redirect(url_for('login'))

        cursor.close()
    return render_template('register.html', msg=msg)

@app.before_request
def refresh_session():
    session.permanent = True  # Ensure session remains active if "Remember Me" was selected

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember_me = request.form.get('rememberMe')  # 'on' if checked, None if not

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM accounts WHERE email = %s AND password = %s', (email, password))
            account = cursor.fetchone()

        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['email'] = account['email']  # Ensure email is stored in session


            if remember_me:  
                session.permanent = True  # Keeps session active
            else:
                session.permanent = False  # Session expires on browser close

            return redirect(url_for('articles'))
        else:
            msg = 'Incorrect email/password!'

    return render_template('login.html', msg=msg)


@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    username = session['username']
    logged_in = 'username' in session
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        selected_preferences = request.form.getlist('preferences')
        preferences_str = ','.join(selected_preferences)
        
        cursor.execute('UPDATE accounts SET preferences = %s WHERE username = %s', (preferences_str, username))
        mysql.connection.commit()
        return redirect(url_for('articles'))
    else:
        available_keywords = ['Sports', 'Lifestyle', 'Entertainment', 'Technology', 'India News', 'Trending', 'Cities', 'Education', 'World News']
        cursor.execute('SELECT preferences FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        existing_preferences = account['preferences'].split(',') if account['preferences'] else []

        return render_template(
        'preferences.html',
        available_keywords=available_keywords,
        existing_preferences=existing_preferences,
        logged_in='username' in session,
        username=session.get('username'),
        on_preferences_page=True  # Pass the flag to the template
    )



@app.route('/add_comment/<int:article_id>', methods=['POST'])
def add_comment(article_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    comment_text = request.form.get('comment')
    username = session['username']
    email = session['email']
    user_id=session['id']

    if not comment_text.strip():
        return redirect(url_for('full_summary', article_id=article_id))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        'INSERT INTO comments (article_id, user_id, comment_text, timestamp) VALUES (%s, %s, %s, NOW())',
        (article_id, user_id, comment_text)
    )
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('full_summary', article_id=article_id))



@app.route('/full_summary/<int:article_id>')
def full_summary(article_id):
    logged_in = 'username' in session
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch current article
    cursor.execute('SELECT * FROM articles WHERE id = %s', (article_id,))
    article = cursor.fetchone()
    if not article:
        return "Article not found", 404

    user_id = session.get('id') if logged_in else None

    # Track view
    if user_id:
        cursor.execute('INSERT INTO views (user_id, article_id) VALUES (%s, %s)', (user_id, article_id))
        mysql.connection.commit()

    # Combine summary, title, and category for similarity
    target_text = f"{article['title']} {article['category']} {article['summary']}"
    target_embedding = model.encode(target_text, convert_to_tensor=True)

    # Fetch other articles (excluding current one)
    cursor.execute('SELECT * FROM articles WHERE id != %s', (article_id,))
    all_articles = cursor.fetchall()

    # Prepare similarity scoring
    candidate_texts = [f"{a['title']} {a['category']} {a['summary']}" for a in all_articles]
    candidate_embeddings = model.encode(candidate_texts, convert_to_tensor=True)

    # Compute cosine similarities
    similarities = util.pytorch_cos_sim(target_embedding, candidate_embeddings)[0]

    # Get top 3 indices
    top_indices = torch.topk(similarities, k=3).indices.tolist()
    related_articles = [all_articles[i] for i in top_indices]

    # Fetch comments
    cursor.execute("""
        SELECT comments.comment_text, comments.timestamp, comments.user_id, accounts.username 
        FROM comments 
        JOIN accounts ON comments.user_id = accounts.id
        WHERE comments.article_id = %s
        ORDER BY comments.timestamp DESC
    """, (article_id,))
    comments = cursor.fetchall()

    return render_template(
        'full_summary.html',
        article=article,
        related_articles=related_articles,
        comments=comments,
        logged_in=logged_in
    )


@app.route('/recommended_articles')
def recommended_articles():
    if 'id' not in session:
        # flash("Please login to see your recommendations.", "warning")
        return redirect(url_for('login'))

    logged_in = 'username' in session
    username = session.get('username') if logged_in else None
    user_id = session['id']  # ✅ Fix added here

    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Step 1: Get IDs of articles the user has viewed
    cursor.execute("SELECT article_id FROM views WHERE user_id = %s", (user_id,))
    viewed_ids = [row['article_id'] for row in cursor.fetchall()]

    if not viewed_ids:
        return render_template('recommendations.html', recommendations=[], logged_in=logged_in, username=username)

    # Step 2: Get full data of viewed articles
    format_ids = ','.join(['%s'] * len(viewed_ids))
    cursor.execute(f"SELECT id, title, summary FROM articles WHERE id IN ({format_ids})", tuple(viewed_ids))
    viewed_articles = cursor.fetchall()

    # Step 3: Fetch all articles
    cursor.execute("SELECT id, title, summary, image_url, link FROM articles")
    all_articles = cursor.fetchall()

    # Step 4: Encode text for similarity comparison
    viewed_texts = [f"{a['title']} - {a['summary']}" for a in viewed_articles]
    all_texts = [f"{a['title']} - {a['summary']}" for a in all_articles]

    viewed_embeddings = model.encode(viewed_texts, convert_to_tensor=True)
    all_embeddings = model.encode(all_texts, convert_to_tensor=True)

    # Step 5: Create user profile by averaging embeddings
    user_profile = viewed_embeddings.mean(dim=0)

    # Step 6: Compute similarity
    similarities = util.pytorch_cos_sim(user_profile, all_embeddings)[0]

    # Step 7: Filter out already viewed articles
    recommendations = []
    for idx, score in enumerate(similarities):
        article = all_articles[idx]
        if article['id'] not in viewed_ids:
            article['score'] = float(score)
            recommendations.append(article)

    # Step 8: Sort and limit results
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    top_recommendations = recommendations[:15]

    return render_template('recommendations.html', recommendations=top_recommendations, logged_in=logged_in, username=username)

    # Step 8: Sort and limit results
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    top_recommendations = recommendations[:15]

    return render_template(
        'recommendations.html',
        recommendations=top_recommendations,
        logged_in=logged_in,
        username=username
    )



@app.route('/user_comments/<int:user_id>')
def user_comments(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch the user info
    cursor.execute("SELECT username FROM accounts WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        return "User not found", 404

    # Fetch all comments by this user
    cursor.execute("""
        SELECT comments.comment_text, comments.timestamp, articles.title, articles.id as article_id
        FROM comments
        JOIN articles ON comments.article_id = articles.id
        WHERE comments.user_id = %s
        ORDER BY comments.timestamp DESC
    """, (user_id,))
    user_comments = cursor.fetchall()

    return render_template("user_comments.html", user=user, user_comments=user_comments)



@app.route('/contact', methods=['GET', 'POST'])
def contact():
    logged_in = 'username' in session
    username = session.get('username') if logged_in else None

    if request.method == 'POST':
        first_name = request.form.get('first-name', '').strip()
        last_name = request.form.get('last-name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        message = request.form.get('message', '').strip()

        if not first_name or not last_name or not email or not message:
            flash('Please fill in all required fields.', 'error')
            return render_template('contact.html', logged_in=logged_in, username=username)

        try:
            cursor = mysql.connection.cursor()
            sql = """
                INSERT INTO user_contact (first_name, last_name, email, phone, message)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (first_name, last_name, email, phone, message))
            mysql.connection.commit()
            cursor.close()

            # Email notification
            subject = f'New Contact Form Submission from {first_name} {last_name}'
            body = f"""
            You have received a new contact form submission:

            Name: {first_name} {last_name}
            Email: {email}
            Phone: {phone}
            Message:
            {message}
            """

            msg = Message(subject=subject,
                          recipients=['ehr.maharastra.'],  # Replace with actual admin email
                          body=body)
            mail.send(msg)

            flash('Thank you for contacting us! We will get back to you shortly.', 'success')
            return redirect(url_for('contact'))

        except Exception as e:
            flash(f'Error: {e}', 'error')
            return render_template('contact.html', logged_in=logged_in, username=username)

    return render_template('contact.html', logged_in=logged_in, username=username)




if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
