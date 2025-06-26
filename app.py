from flask import Flask, request, redirect, render_template_string, send_file, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from config import MONGO_URI, DB_NAME, COLLECTION_NAME
from login_system import register_routes, protect
import csv
import io

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Setup MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
equity_collection = db['equity']
users_collection = db['users']

register_routes(app, users_collection)

HTML_TEMPLATE = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <title>Jurnal Trading</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
  <link href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css\" rel=\"stylesheet\">
  <link href=\"https://cdn.datatables.net/1.13.5/css/dataTables.bootstrap5.min.css\" rel=\"stylesheet\">
  <style>
    body.dark { background-color: #121212 !important; color: #f0f0f0; }
    .dark .table, .dark .form-control, .dark .btn { background-color: #333 !important; color: #fff; border-color: #555; }
    .dark .card { background-color: #1e1e1e; border-color: #444; }
    .dark .card-title, .dark .card-text { color: #f0f0f0 !important; }
    .result-tp { color: limegreen; font-weight: bold; }
    .result-sl { color: red; font-weight: bold; }
    .theme-toggle { position: fixed; top: 1rem; right: 1rem; cursor: pointer; }
  </style>
</head>
<body class=\"bg-light p-4\" id=\"body\">
  <div class=\"theme-toggle\">
    <button class=\"btn btn-outline-secondary\" onclick=\"toggleTheme()\">🌙☀️</button>
  </div>
  <div class=\"container\">
    <div class=\"d-flex justify-content-end\">
      <a href=\"/logout\" class=\"btn btn-outline-danger mb-3\">Logout ({{ session['username'] }})</a>
    </div>
    <h2 class=\"text-center mb-4\">Jurnal Trading XAUUSD</h2>
    <form method=\"POST\" class=\"mb-5\" onsubmit=\"return confirm('Yakin data sudah benar?')\">
      <div class=\"row g-3\">
        <div class=\"col-md-4\">
          <label>Lot Size</label>
          <input type=\"number\" step=\"0.01\" min=\"0.01\" name=\"lot\" class=\"form-control\" required>
        </div>
        <div class=\"col-md-4\">
          <label>Open Price</label>
          <input type=\"number\" step=\"0.001\" name=\"open_price\" class=\"form-control\" required>
        </div>
        <div class=\"col-md-4\">
          <label>Stop Loss</label>
          <input type=\"number\" step=\"0.001\" name=\"sl\" class=\"form-control\" required>
        </div>
        <div class=\"col-md-4\">
          <label>Take Profit</label>
          <input type=\"number\" step=\"0.001\" name=\"tp\" class=\"form-control\" required>
        </div>
        <div class=\"col-md-4\">
          <label>Hasil</label>
          <select name=\"result\" class=\"form-control\" required>
            <option value=\"TP\">✔️ TP</option>
            <option value=\"SL\">❌ SL</option>
          </select>
        </div>
        <div class=\"col-md-4\">
          <label>Keterangan</label>
          <select name=\"note\" class=\"form-control\">
            <option value=\"Buy\">Buy</option>
            <option value=\"Sell\">Sell</option>
          </select>
        </div>
      </div>
      <button type=\"submit\" class=\"btn btn-primary mt-4\">Simpan</button>
      <a href=\"/export\" class=\"btn btn-success mt-4 ms-2\">Export CSV</a>
      <a href=\"/set-equity\" class=\"btn btn-secondary mt-4 ms-2\">Atur Equity Awal</a>
    </form>
    <div class=\"row mb-4\">
      <div class=\"col-md-3\">
        <div class=\"card text-center\">
          <div class=\"card-body\">
            <h5 class=\"card-title\">Total Trades</h5>
            <p class=\"card-text fs-4\">{{ stats.total }}</p>
          </div>
        </div>
      </div>
      <div class=\"col-md-3\">
        <div class=\"card text-center\">
          <div class=\"card-body\">
            <h5 class=\"card-title\">Total TP</h5>
            <p class=\"card-text fs-4 text-success\">{{ stats.tp }}</p>
          </div>
        </div>
      </div>
      <div class=\"col-md-3\">
        <div class=\"card text-center\">
          <div class=\"card-body\">
            <h5 class=\"card-title\">Total SL</h5>
            <p class=\"card-text fs-4 text-danger\">{{ stats.sl }}</p>
          </div>
        </div>
      </div>
      <div class=\"col-md-3\">
        <div class=\"card text-center\">
          <div class=\"card-body\">
            <h5 class=\"card-title\">Winrate</h5>
            <p class=\"card-text fs-4\">{{ stats.winrate }}%</p>
          </div>
        </div>
      </div>
      <div class=\"col-md-3 mt-3\">
        <div class=\"card text-center\">
          <div class=\"card-body\">
            <h5 class=\"card-title\">PnL (Growth)</h5>
            <p class=\"card-text fs-4\">${{ '%.2f'|format(stats.growth) }}</p>
          </div>
        </div>
      </div>
    </div>
    <div class=\"table-responsive\">
      <table id=\"tradeTable\" class=\"table table-bordered table-striped shadow-sm\">
        <thead>
          <tr>
            <th>No</th>
            <th>Tanggal & Waktu</th>
            <th>Lot</th>
            <th>Open Price</th>
            <th>SL</th>
            <th>TP</th>
            <th>Hasil</th>
            <th>Keterangan</th>
            <th>Profit</th>
            <th>Equity After</th>
          </tr>
        </thead>
        <tbody>
          {% for trade in trades %}
          <tr>
            <td>{{ loop.index }}</td>
            <td>{{ trade.date }}</td>
            <td>{{ trade.lot }}</td>
            <td>{{ trade.open_price }}</td>
            <td>{{ trade.sl }}</td>
            <td>{{ trade.tp }}</td>
            <td class=\"{{ 'result-tp' if trade.result == 'TP' else 'result-sl' }}\">{{ trade.result }}</td>
            <td>{{ trade.note }}</td>
            <td>${{ '%.2f'|format(trade.profit) }}</td>
            <td>${{ '%.2f'|format(trade.equity_after) }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  <script src=\"https://code.jquery.com/jquery-3.7.0.min.js\"></script>
  <script src=\"https://cdn.datatables.net/1.13.5/js/jquery.dataTables.min.js\"></script>
  <script src=\"https://cdn.datatables.net/1.13.5/js/dataTables.bootstrap5.min.js\"></script>
  <script>
    $(document).ready(function() {
      $('#tradeTable').DataTable();
    });
    function toggleTheme() {
      const body = document.getElementById('body');
      const dark = body.classList.toggle('dark');
      localStorage.setItem('theme', dark ? 'dark' : 'light');
    }
    window.onload = () => {
      if (localStorage.getItem('theme') === 'dark') {
        document.getElementById('body').classList.add('dark');
      }
    }
  </script>
</body>
</html>
"""
@app.route('/', methods=['GET', 'POST'])
def index():
    check = protect()
    if check: return check

    if request.method == 'POST':
        lot = float(request.form['lot'])
        open_price = float(request.form['open_price'])
        sl = float(request.form['sl'])
        tp = float(request.form['tp'])
        result = request.form['result']
        note = request.form['note']
        pip_value = 100 * lot

        last_equity_data = equity_collection.find_one(sort=[("_id", -1)])
        if not last_equity_data:
            return "Equity awal belum diatur. Silakan atur dulu di halaman 'Atur Equity Awal'."

        last_trade = collection.find_one(sort=[("date", -1)])
        current_equity = last_trade['equity_after'] if last_trade else last_equity_data['amount']

        if note == 'Buy':
            profit = (tp - open_price) * pip_value if result == 'TP' else (sl - open_price) * pip_value
        else:
            profit = (open_price - tp) * pip_value if result == 'TP' else (sl - open_price) * pip_value * -1

        equity_after = current_equity + profit

        trade = {
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "lot": lot,
            "open_price": open_price,
            "sl": sl,
            "tp": tp,
            "result": result,
            "note": note,
            "profit": profit,
            "equity_after": equity_after
        }
        collection.insert_one(trade)
        return redirect('/')

    trades = list(collection.find().sort("date", 1))
    tp_count = sum(1 for t in trades if t['result'] == 'TP')
    sl_count = sum(1 for t in trades if t['result'] == 'SL')
    total = len(trades)
    winrate = round((tp_count / total) * 100, 2) if total else 0
    equity_start = equity_collection.find_one(sort=[("_id", -1)])
    start = equity_start['amount'] if equity_start else 0
    end = trades[-1]['equity_after'] if trades else start
    stats = {
        "tp": tp_count,
        "sl": sl_count,
        "total": total,
        "winrate": winrate,
        "growth": end - start
    }
    return render_template_string(HTML_TEMPLATE, trades=trades, stats=stats)

@app.route('/set-equity', methods=['GET', 'POST'])
def set_equity():
    check = protect()
    if check: return check

    if request.method == 'POST':
        amount = float(request.form['amount'])
        equity_collection.insert_one({
            "amount": amount,
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        recalculate_equity(amount)
        return redirect('/')
    return '''
        <form method="POST">
            <label>Masukkan Equity Awal ($):</label>
            <input type="number" step="0.01" name="amount" required>
            <button type="submit">Simpan</button>
        </form>
    '''

def recalculate_equity(initial_equity):
    trades = list(collection.find().sort("date", 1))
    equity = initial_equity
    for trade in trades:
        lot = trade['lot']
        open_price = trade['open_price']
        sl = trade['sl']
        tp = trade['tp']
        result = trade['result']
        note = trade['note']
        pip_value = 100 * lot

        if note == 'Buy':
            profit = (tp - open_price) * pip_value if result == 'TP' else (sl - open_price) * pip_value
        else:
            profit = (open_price - tp) * pip_value if result == 'TP' else (sl - open_price) * pip_value * -1

        equity += profit
        collection.update_one({"_id": trade['_id']}, {"$set": {
            "profit": profit,
            "equity_after": equity
        }})

@app.route('/export')
def export():
    check = protect()
    if check: return check
    trades = list(collection.find().sort("date", 1))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Tanggal', 'Lot', 'Open Price', 'SL', 'TP', 'Hasil', 'Keterangan', 'Profit', 'Equity After'])
    for t in trades:
        writer.writerow([t['date'], t['lot'], t['open_price'], t['sl'], t['tp'], t['result'], t['note'], t['profit'], t['equity_after']])
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype='text/csv', as_attachment=True, download_name='jurnal_trading.csv')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
