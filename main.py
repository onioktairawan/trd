from flask import Flask, request, redirect, render_template_string, send_file, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from config import MONGO_URI, DB_NAME, COLLECTION_NAME
import csv
import io

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Ganti dengan yang lebih aman

# Setup MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
users = db['users']

# Template HTML Login/Register
AUTH_TEMPLATE = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <title>{{ title }}</title>
  <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
</head>
<body class=\"bg-light\">
  <div class=\"container mt-5\">
    <h2 class=\"text-center mb-4\">{{ title }}</h2>
    {% if error %}<div class=\"alert alert-danger\">{{ error }}</div>{% endif %}
    <form method=\"POST\">
      <div class=\"mb-3\">
        <label>Username</label>
        <input type=\"text\" name=\"username\" class=\"form-control\" required>
      </div>
      <div class=\"mb-3\">
        <label>Password</label>
        <input type=\"password\" name=\"password\" class=\"form-control\" required>
      </div>
      <button type=\"submit\" class=\"btn btn-primary\">{{ action }}</button>
    </form>
    <div class=\"mt-3\">
      {% if title == 'Login' %}
        Belum punya akun? <a href=\"/register\">Daftar di sini</a>
      {% else %}
        Sudah punya akun? <a href=\"/login\">Login</a>
      {% endif %}
    </div>
  </div>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.find_one({'username': username, 'password': password})
        if user:
            session['user'] = username
            return redirect('/')
        else:
            return render_template_string(AUTH_TEMPLATE, title='Login', action='Login', error='Username atau password salah.')
    return render_template_string(AUTH_TEMPLATE, title='Login', action='Login', error=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users.find_one({'username': username}):
            return render_template_string(AUTH_TEMPLATE, title='Register', action='Daftar', error='Username sudah digunakan.')
        users.insert_one({'username': username, 'password': password})
        session['user'] = username
        return redirect('/')
    return render_template_string(AUTH_TEMPLATE, title='Register', action='Daftar', error=None)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' not in session:
        return redirect('/login')

    user = session['user']

    if request.method == 'POST':
        equity = float(request.form['equity'])
        lot = float(request.form['lot'])
        open_price = float(request.form['open_price'])
        sl = float(request.form['sl'])
        tp = float(request.form['tp'])
        result = request.form['result']
        note = request.form['note']

        pip_value = 10
        if result == 'TP':
            pnl = (tp - open_price) * lot * pip_value
        else:
            pnl = (open_price - sl) * lot * pip_value * -1

        equity_after = equity + pnl

        trade = {
            "user": user,
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "equity": equity,
            "lot": lot,
            "open_price": open_price,
            "sl": sl,
            "tp": tp,
            "result": result,
            "note": note,
            "equity_after": equity_after
        }

        collection.insert_one(trade)
        return redirect('/')

    trades = list(collection.find({"user": user}).sort("date", -1))
    tp_count = sum(1 for t in trades if t['result'] == 'TP')
    sl_count = sum(1 for t in trades if t['result'] == 'SL')
    total = len(trades)
    start_equity = trades[-1]['equity'] if trades else 0
    end_equity = trades[0]['equity_after'] if trades else 0
    winrate = round((tp_count / total) * 100, 2) if total else 0

    stats = {
        "tp": tp_count,
        "sl": sl_count,
        "total": total,
        "winrate": winrate,
        "growth": end_equity - start_equity
    }

    return render_template_string(HTML_TEMPLATE, trades=trades, stats=stats, edit_data=None)

@app.route('/delete/<id>')
def delete(id):
    if 'user' not in session:
        return redirect('/login')
    collection.delete_one({"_id": ObjectId(id), "user": session['user']})
    return redirect('/')

@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    if 'user' not in session:
        return redirect('/login')

    user = session['user']

    if request.method == 'POST':
        equity = float(request.form['equity'])
        lot = float(request.form['lot'])
        open_price = float(request.form['open_price'])
        sl = float(request.form['sl'])
        tp = float(request.form['tp'])
        result = request.form['result']
        note = request.form['note']

        pip_value = 10
        if result == 'TP':
            pnl = (tp - open_price) * lot * pip_value
        else:
            pnl = (open_price - sl) * lot * pip_value * -1

        equity_after = equity + pnl

        collection.update_one({"_id": ObjectId(id), "user": user}, {"$set": {
            "equity": equity,
            "lot": lot,
            "open_price": open_price,
            "sl": sl,
            "tp": tp,
            "result": result,
            "note": note,
            "equity_after": equity_after
        }})
        return redirect('/')

    trade = collection.find_one({"_id": ObjectId(id), "user": user})
    trades = list(collection.find({"user": user}).sort("date", -1))
    tp_count = sum(1 for t in trades if t['result'] == 'TP')
    sl_count = sum(1 for t in trades if t['result'] == 'SL')
    total = len(trades)
    start_equity = trades[-1]['equity'] if trades else 0
    end_equity = trades[0]['equity_after'] if trades else 0
    winrate = round((tp_count / total) * 100, 2) if total else 0
    stats = {
        "tp": tp_count,
        "sl": sl_count,
        "total": total,
        "winrate": winrate,
        "growth": end_equity - start_equity
    }
    return render_template_string(HTML_TEMPLATE, trades=trades, stats=stats, edit_data=trade)

@app.route('/export')
def export():
    if 'user' not in session:
        return redirect('/login')
    user = session['user']
    trades = list(collection.find({"user": user}).sort("date", -1))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Tanggal', 'Equity', 'Lot', 'Open Price', 'SL', 'TP', 'Hasil', 'Keterangan', 'Equity After'])
    for t in trades:
        writer.writerow([t['date'], t['equity'], t['lot'], t['open_price'], t['sl'], t['tp'], t['result'], t['note'], t['equity_after']])
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype='text/csv', as_attachment=True, download_name='jurnal_trading.csv')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
