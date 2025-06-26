from flask import Flask, request, redirect, render_template, send_file, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from config import MONGO_URI, DB_NAME, COLLECTION_NAME
from login_system import register_routes, protect
import csv
import io
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Setup MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
equity_collection = db['equity']
users_collection = db['users']

register_routes(app, users_collection)

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
    return render_template("index.html", trades=trades, stats=stats)

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
    return render_template("set_equity.html")

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
