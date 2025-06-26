#app.py
from flask import Flask, request, redirect, render_template_string, send_file, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from config import MONGO_URI, DB_NAME, COLLECTION_NAME, SECRET_KEY
from login_system import register_routes, protect
import csv
import io

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Setup MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
users_collection = db['users']

register_routes(app, users_collection)

# --- HTML Templates ---
LAYOUT_TEMPLATE = """
<!doctype html>
<html lang='en'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>{{ title }}</title>
  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>
  <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
  <style>
    body { padding: 0; margin: 0; }
    .sidebar {
      width: 220px;
      height: 100vh;
      position: fixed;
      background-color: #343a40;
      color: #fff;
    }
    .sidebar a {
      display: block;
      padding: 15px;
      color: white;
      text-decoration: none;
    }
    .sidebar a:hover {
      background-color: #495057;
    }
    .content {
      margin-left: 220px;
      padding: 20px;
    }
  </style>
</head>
<body>
  <div class='sidebar'>
    <h4 class='p-3'>📊 Jurnal</h4>
    <a href='/dashboard'>Dashboard</a>
    <a href='/jurnal'>Jurnal Trading</a>
    <a href='/logout'>Logout ({{ session['username'] }})</a>
  </div>
  <div class='content'>
    {% block content %}{% endblock %}
  </div>
</body>
</html>
"""
JURNAL_TEMPLATE = """
<!doctype html>
<html lang='en'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Jurnal Trading</title>
  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>
  <style>
    body { padding: 0; margin: 0; }
    .sidebar {
      width: 220px;
      height: 100vh;
      position: fixed;
      background-color: #343a40;
      color: #fff;
    }
    .sidebar a {
      display: block;
      padding: 15px;
      color: white;
      text-decoration: none;
    }
    .sidebar a:hover {
      background-color: #495057;
    }
    .content {
      margin-left: 220px;
      padding: 20px;
    }
  </style>
</head>
<body>
  <div class='sidebar'>
    <h4 class='p-3'>📊 Jurnal</h4>
    <a href='/dashboard'>Dashboard</a>
    <a href='/jurnal'>Jurnal Trading</a>
    <a href='/logout'>Logout ({{ session['username'] }})</a>
  </div>
  <div class='content'>
    <h2>Jurnal Trading</h2>
    <form method='POST' class='row g-3'>
      <div class='col-md-4'>
        <label>Equity</label>
        <input type='number' step='0.01' name='equity' class='form-control' required>
      </div>
      <div class='col-md-4'>
        <label>Lot</label>
        <input type='number' step='0.01' name='lot' class='form-control' required>
      </div>
      <div class='col-md-4'>
        <label>Open Price</label>
        <input type='number' step='0.01' name='open_price' class='form-control' required>
      </div>
      <div class='col-md-4'>
        <label>SL</label>
        <input type='number' step='0.01' name='sl' class='form-control' required>
      </div>
      <div class='col-md-4'>
        <label>TP</label>
        <input type='number' step='0.01' name='tp' class='form-control' required>
      </div>
      <div class='col-md-4'>
        <label>Result</label>
        <select name='result' class='form-control'>
          <option value='TP'>TP</option>
          <option value='SL'>SL</option>
        </select>
      </div>
      <div class='col-md-12'>
        <label>Keterangan</label>
        <select name='note' class='form-control'>
          <option value='Buy'>Buy</option>
          <option value='Sell'>Sell</option>
        </select>
      </div>
      <div class='col-md-12'>
        <button class='btn btn-primary'>Simpan</button>
        <a href='/export' class='btn btn-success'>Export CSV</a>
      </div>
    </form>
    <hr>
    <table class='table table-bordered'>
      <thead><tr>
        <th>No</th><th>Tanggal</th><th>Equity</th><th>Lot</th><th>Open</th><th>SL</th><th>TP</th><th>Result</th><th>Note</th><th>Profit</th><th>Equity After</th>
      </tr></thead>
      <tbody>
      {% for t in trades %}
      <tr>
        <td>{{ loop.index }}</td>
        <td>{{ t.date }}</td>
        <td>{{ t.equity }}</td>
        <td>{{ t.lot }}</td>
        <td>{{ t.open_price }}</td>
        <td>{{ t.sl }}</td>
        <td>{{ t.tp }}</td>
        <td>{{ t.result }}</td>
        <td>{{ t.note }}</td>
        <td>{{ '%.2f' % (t.equity_after - t.equity) }}</td>
        <td>{{ t.equity_after }}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang='en'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Dashboard</title>
  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>
  <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
  <style>
    body { padding: 0; margin: 0; }
    .sidebar {
      width: 220px;
      height: 100vh;
      position: fixed;
      background-color: #343a40;
      color: #fff;
    }
    .sidebar a {
      display: block;
      padding: 15px;
      color: white;
      text-decoration: none;
    }
    .sidebar a:hover {
      background-color: #495057;
    }
    .content {
      margin-left: 220px;
      padding: 20px;
    }
  </style>
</head>
<body>
  <div class='sidebar'>
    <h4 class='p-3'>📊 Jurnal</h4>
    <a href='/dashboard'>Dashboard</a>
    <a href='/jurnal'>Jurnal Trading</a>
    <a href='/logout'>Logout ({{ session['username'] }})</a>
  </div>
  <div class='content'>
    <h2>Dashboard</h2>
    <form method='POST' class='row g-3'>
      <div class='col-md-4'>
        <label>Dari Tanggal</label>
        <input type='date' name='date_from' value='{{ date_from or "" }}' class='form-control'>
      </div>
      <div class='col-md-4'>
        <label>Sampai Tanggal</label>
        <input type='date' name='date_to' value='{{ date_to or "" }}' class='form-control'>
      </div>
      <div class='col-md-4 align-self-end'>
        <button class='btn btn-primary'>Tampilkan</button>
      </div>
    </form>
    <hr>
    <div class='row'>
      <div class='col-md-3'><div class='card'><div class='card-body'><h5>Total TP</h5><p class='fs-4 text-success'>{{ stats.tp }}</p></div></div></div>
      <div class='col-md-3'><div class='card'><div class='card-body'><h5>Total SL</h5><p class='fs-4 text-danger'>{{ stats.sl }}</p></div></div></div>
      <div class='col-md-3'><div class='card'><div class='card-body'><h5>Winrate</h5><p class='fs-4'>{{ stats.winrate }}%</p></div></div></div>
      <div class='col-md-3'><div class='card'><div class='card-body'><h5>Total Profit</h5><p class='fs-4'>${{ '%.2f'|format(stats.profit) }}</p></div></div></div>
    </div>
    <hr>
    <canvas id='chart' height='100'></canvas>
    <script>
      const ctx = document.getElementById('chart').getContext('2d');
      const chart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: {{ trades | map(attribute='date') | list | tojson }},
          datasets: [{
            label: 'Profit/Loss',
            data: {{ trades | map(attribute='profit') | list | tojson }},
            backgroundColor: {{ trades | map(attribute='color') | list | tojson }}
          }]
        },
        options: {
          scales: {
            y: { beginAtZero: true }
          }
        }
      });
    </script>
  </div>
</body>
</html>
"""

# --- ROUTES ---
@app.route('/')
def home():
    return redirect('/dashboard')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    check = protect()
    if check: return check

    date_from = request.form.get("date_from")
    date_to = request.form.get("date_to")
    trades = []
    stats = {}

    if date_from and date_to:
        try:
            date_start = datetime.strptime(date_from, '%Y-%m-%d')
            date_end = datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
            query = {
                "username": session['username'],
                "date": {"$gte": date_start.strftime('%Y-%m-%d'), "$lte": date_end.strftime('%Y-%m-%d %H:%M:%S')}
            }
            trades = list(collection.find(query))
        except:
            trades = []

    # Tambahkan 'profit' dan 'color' ke setiap trade
    for t in trades:
        t['profit'] = t['equity_after'] - t['equity']
        t['color'] = 'green' if t['result'] == 'TP' else 'red'

    tp = sum(1 for t in trades if t['result'] == 'TP')
    sl = sum(1 for t in trades if t['result'] == 'SL')
    total = len(trades)
    winrate = round((tp / total) * 100, 2) if total else 0
    profit_total = sum(t['profit'] for t in trades)

    stats = {
        "tp": tp,
        "sl": sl,
        "total": total,
        "winrate": winrate,
        "profit": profit_total
    }

    return render_template_string(DASHBOARD_TEMPLATE, stats=stats, trades=trades, date_from=date_from, date_to=date_to)

@app.route('/jurnal', methods=['GET', 'POST'])
def jurnal():
    check = protect()
    if check: return check

    if request.method == 'POST':
        form = request.form
        equity = float(form['equity'])
        lot = float(form['lot'])
        open_price = float(form['open_price'])
        sl = float(form['sl'])
        tp = float(form['tp'])
        result = form['result']
        note = form['note']
        pip_value = 100 * lot
        if note == 'Buy':
            pnl = (tp - open_price) * pip_value if result == 'TP' else (sl - open_price) * pip_value
        else:
            pnl = (open_price - tp) * pip_value if result == 'TP' else (sl - open_price) * pip_value * -1
        equity_after = equity + pnl

        trade = {
            "username": session['username'],
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
        return redirect('/jurnal')

    trades = list(collection.find({"username": session['username']}).sort("date", -1))
    tp = sum(1 for t in trades if t['result'] == 'TP')
    sl = sum(1 for t in trades if t['result'] == 'SL')
    total = len(trades)
    winrate = round((tp / total) * 100, 2) if total else 0

    stats = {"tp": tp, "sl": sl, "total": total, "winrate": winrate}
    return render_template_string(JURNAL_TEMPLATE, trades=trades, stats=stats, edit_data=None)

@app.route('/delete/<id>')
def delete(id):
    check = protect()
    if check: return check
    collection.delete_one({"_id": ObjectId(id), "username": session['username']})
    return redirect('/jurnal')

@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    check = protect()
    if check: return check

    if request.method == 'POST':
        form = request.form
        equity = float(form['equity'])
        lot = float(form['lot'])
        open_price = float(form['open_price'])
        sl = float(form['sl'])
        tp = float(form['tp'])
        result = form['result']
        note = form['note']
        pip_value = 100 * lot
        if note == 'Buy':
            pnl = (tp - open_price) * pip_value if result == 'TP' else (sl - open_price) * pip_value
        else:
            pnl = (open_price - tp) * pip_value if result == 'TP' else (sl - open_price) * pip_value * -1
        equity_after = equity + pnl

        collection.update_one({"_id": ObjectId(id), "username": session['username']}, {"$set": {
            "equity": equity,
            "lot": lot,
            "open_price": open_price,
            "sl": sl,
            "tp": tp,
            "result": result,
            "note": note,
            "equity_after": equity_after
        }})
        return redirect('/jurnal')

    trade = collection.find_one({"_id": ObjectId(id), "username": session['username']})
    trades = list(collection.find({"username": session['username']}).sort("date", -1))
    tp = sum(1 for t in trades if t['result'] == 'TP')
    sl = sum(1 for t in trades if t['result'] == 'SL')
    total = len(trades)
    winrate = round((tp / total) * 100, 2) if total else 0
    stats = {"tp": tp, "sl": sl, "total": total, "winrate": winrate}
    return render_template_string(JURNAL_TEMPLATE, trades=trades, stats=stats, edit_data=trade)

@app.route('/export')
def export():
    check = protect()
    if check: return check
    trades = list(collection.find({"username": session['username']}).sort("date", -1))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Tanggal', 'Equity', 'Lot', 'Open Price', 'SL', 'TP', 'Hasil', 'Keterangan', 'Equity After'])
    for t in trades:
        writer.writerow([t['date'], t['equity'], t['lot'], t['open_price'], t['sl'], t['tp'], t['result'], t['note'], t['equity_after']])
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype='text/csv', as_attachment=True, download_name='jurnal_trading.csv')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
