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
HTML_TEMPLATE = """
<!doctype html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <title>Histori Trading</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script>
      function toggleTheme() {
        const html = document.documentElement;
        if (html.getAttribute('data-theme') === 'dark') {
            html.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        } else {
            html.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
      }
      window.onload = () => {
        const saved = localStorage.getItem('theme');
        if (saved) document.documentElement.setAttribute('data-theme', saved);
      }
    </script>
    <style>
      [data-theme="dark"] body {
        background-color: #121212;
        color: white;
      }
      [data-theme="dark"] .form-control, 
      [data-theme="dark"] .table, 
      [data-theme="dark"] .form-select {
        background-color: #1e1e1e;
        color: white;
      }
      .tp-result { color: green; }
      .sl-result { color: red; }
    </style>
</head>
<body>
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center">
        <h2>Histori Trading</h2>
        <div>
            <button onclick="toggleTheme()" class="btn btn-secondary">🌙/☀️</button>
            <a href="/logout" class="btn btn-outline-danger">Logout</a>
        </div>
    </div>

    <form method="POST" class="row g-3 mt-2">
        {% if edit_data %}
        <input type="hidden" name="edit_id" value="{{ edit_data['_id'] }}">
        {% endif %}
        <div class="col-md-2"><input step="0.01" min="0.01" name="equity" required class="form-control" placeholder="Equity Awal" value="{{ edit_data.equity if edit_data }}"></div>
        <div class="col-md-1"><input type="number" step="0.01" min="0.01" name="lot" required class="form-control" placeholder="Lot" value="{{ edit_data.lot if edit_data }}"></div>
        <div class="col-md-1"><input type="number" step="0.001" name="open_price" required class="form-control" placeholder="Open Price" value="{{ edit_data.open_price if edit_data }}"></div>
        <div class="col-md-1"><input type="number" step="0.001" name="sl" required class="form-control" placeholder="SL" value="{{ edit_data.sl if edit_data }}"></div>
        <div class="col-md-1"><input type="number" step="0.001" name="tp" required class="form-control" placeholder="TP" value="{{ edit_data.tp if edit_data }}"></div>
        <div class="col-md-1">
            <select name="result" class="form-select">
                <option value="TP" {% if edit_data and edit_data.result == 'TP' %}selected{% endif %}>TP</option>
                <option value="SL" {% if edit_data and edit_data.result == 'SL' %}selected{% endif %}>SL</option>
            </select>
        </div>
        <div class="col-md-2">
            <select name="note" class="form-select">
                <option value="Buy" {% if edit_data and edit_data.note == 'Buy' %}selected{% endif %}>Buy</option>
                <option value="Sell" {% if edit_data and edit_data.note == 'Sell' %}selected{% endif %}>Sell</option>
            </select>
        </div>
        <div class="col-md-2">
            <button class="btn btn-success w-100" type="submit">{{ 'Update' if edit_data else 'Tambah' }}</button>
        </div>
    </form>

    <table class="table table-bordered table-hover table-sm mt-4">
        <thead class="table-light">
            <tr>
                <th>Aksi</th>
                <th>No</th>
                <th>Tanggal & Waktu</th>
                <th>Equity Awal</th>
                <th>Lot</th>
                <th>Open</th>
                <th>SL</th>
                <th>TP</th>
                <th>Hasil</th>
                <th>Keterangan</th>
                <th>Profit</th>
                <th>Equity After</th>
            </tr>
        </thead>
        <tbody>
            {% for i, t in enumerate(trades) %}
            <tr>
                <td>
                    <a href="/edit/{{ t._id }}" class="btn btn-sm btn-warning">✏️</a>
                    <a href="/delete/{{ t._id }}" onclick="return confirm('Yakin mau hapus?')" class="btn btn-sm btn-danger">🗑️</a>
                </td>
                <td>{{ loop.index }}</td>
                <td>{{ t.date }}</td>
                <td>${{ '%.2f'|format(t.equity) }}</td>
                <td>{{ t.lot }}</td>
                <td>{{ t.open_price }}</td>
                <td>{{ t.sl }}</td>
                <td>{{ t.tp }}</td>
                <td class="{{ 'tp-result' if t.result == 'TP' else 'sl-result' }}">{{ t.result }}</td>
                <td>{{ t.note }}</td>
                <td>${{ '%.2f'|format(t.equity_after - t.equity) }}</td>
                <td>${{ '%.2f'|format(t.equity_after) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="row mt-4">
        <div class="col-md-6">
            <strong>Statistik:</strong><br>
            Total Trade: {{ stats.total }}<br>
            TP: {{ stats.tp }} | SL: {{ stats.sl }}<br>
            Winrate: {{ stats.winrate }}%<br>
            Growth: ${{ '%.2f'|format(stats.growth) }}
        </div>
        <div class="col-md-6 text-end">
            <a href="/export" class="btn btn-outline-success">⬇️ Export CSV</a>
        </div>
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
