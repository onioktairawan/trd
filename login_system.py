# login_system.py
from flask import request, redirect, session, render_template_string

LOGIN_FORM = """
<!doctype html>
<title>Login</title>
<h2>Login</h2>
<form method='POST'>
  <input type='text' name='username' placeholder='Username' required>
  <input type='password' name='password' placeholder='Password' required>
  <button type='submit'>Login</button>
</form>
<p>Belum punya akun? <a href='/register'>Daftar</a></p>
"""

REGISTER_FORM = """
<!doctype html>
<title>Register</title>
<h2>Register</h2>
<form method='POST'>
  <input type='text' name='username' placeholder='Username' required>
  <input type='password' name='password' placeholder='Password' required>
  <button type='submit'>Daftar</button>
</form>
<p>Sudah punya akun? <a href='/login'>Login</a></p>
"""

def protect():
    if 'username' not in session:
        return redirect('/login')

def register_routes(app, users_collection):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            user = users_collection.find_one({'username': request.form['username'], 'password': request.form['password']})
            if user:
                session['username'] = user['username']
                session['user_id'] = str(user['_id'])
                return redirect('/')
        return render_template_string(LOGIN_FORM)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            if users_collection.find_one({'username': request.form['username']}):
                return "Username sudah digunakan"
            users_collection.insert_one({
                'username': request.form['username'],
                'password': request.form['password']
            })
            return redirect('/login')
        return render_template_string(REGISTER_FORM)

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect('/login')
