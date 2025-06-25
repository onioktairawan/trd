from flask import request, redirect, render_template_string, session

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Login</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light d-flex align-items-center justify-content-center" style="height: 100vh;">
  <div class="card p-4 shadow" style="width: 350px;">
    <h4 class="text-center mb-3">{{ title }}</h4>
    {% if message %}
    <div class="alert alert-info">{{ message }}</div>
    {% endif %}
    <form method="POST">
      <input type="text" name="username" placeholder="Username" class="form-control mb-2" required>
      <input type="password" name="password" placeholder="Password" class="form-control mb-3" required>
      <button type="submit" class="btn btn-primary w-100">{{ button }}</button>
    </form>
    <div class="text-center mt-2">
      {% if title == 'Login' %}
        <a href="/register">Belum punya akun? Register</a>
      {% else %}
        <a href="/login">Sudah punya akun? Login</a>
      {% endif %}
    </div>
  </div>
</body>
</html>
"""

def register_routes(app, users_collection):
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if users_collection.find_one({'username': username}):
                return render_template_string(LOGIN_TEMPLATE, title="Register", button="Daftar", message="Username sudah digunakan.")
            users_collection.insert_one({'username': username, 'password': password})
            return render_template_string(LOGIN_TEMPLATE, title="Login", button="Login", message="Berhasil mendaftar, silakan login.")
        return render_template_string(LOGIN_TEMPLATE, title="Register", button="Daftar", message=None)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = users_collection.find_one({'username': username, 'password': password})
            if user:
                session['username'] = username
                return redirect('/')
            else:
                return render_template_string(LOGIN_TEMPLATE, title="Login", button="Login", message="Username atau password salah.")
        return render_template_string(LOGIN_TEMPLATE, title="Login", button="Login", message=None)

    @app.route('/logout')
    def logout():
        session.pop('username', None)
        return redirect('/login')

def protect():
    if 'username' not in session:
        return redirect('/login')
