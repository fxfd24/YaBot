from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import pandas as pd
import os
import re

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Необходимо для использования flash сообщений

# Путь к вашему CSV-файлу
CSV_FILE = 'data.csv'
TIMER_FILE = 'timer.txt'

def check_and_create_timer_file():
    # Проверяем, существует ли файл
    if not os.path.exists(TIMER_FILE):
        # Если файл не существует, создаем его
        with open(TIMER_FILE, 'w') as file:
            # Записываем текущее время в файл
            file.write("00:01:00")

def write_timer_file(delay_timer):
    with open(TIMER_FILE, 'w') as file:
        # Записываем текущее время в файл
        file.write(delay_timer)

def get_timer_file():
    with open(TIMER_FILE, 'r') as file:
        value = file.read().strip()
        return value

check_and_create_timer_file()

# Функция для проверки существования файла и его создания, если он отсутствует
def ensure_csv_exists():
    if not os.path.isfile(CSV_FILE):
        # Создаем DataFrame с нужными колонками
        df = pd.DataFrame(columns=['target_chat_id', 'name_chat', 'dest_email'])
        # Сохраняем его в CSV-файл
        df.to_csv(CSV_FILE, index=False)

@app.route('/')
def index():
    ensure_csv_exists()
    df = pd.read_csv(CSV_FILE)
    timer_value = get_timer_file()
    return render_template('index.html', data=df.to_dict(orient='records'), timer_value=timer_value)

@app.route('/edit/<int:index>', methods=['GET', 'POST'])
def edit(index):
    ensure_csv_exists()
    df = pd.read_csv(CSV_FILE)
    if request.method == 'POST':
        df.at[index, 'target_chat_id'] = int(request.form['target_chat_id'])
        df.at[index, 'name_chat'] = request.form['name_chat']
        df.at[index, 'dest_email'] = request.form['dest_email']
        df.to_csv(CSV_FILE, index=False)
        return redirect(url_for('index'))
    row = df.iloc[index]
    return render_template('edit.html', row=row, index=index)

@app.route('/download_logs')
def download_logs():
    return send_file('telegram_bot.log', as_attachment=True)

@app.route('/add_row', methods=['GET', 'POST'])
def add_row():
    ensure_csv_exists()
    df = pd.read_csv(CSV_FILE)
    if request.method == 'POST':
        new_row = pd.DataFrame({
            'target_chat_id': [int(request.form['target_chat_id'])],
            'name_chat': [request.form['name_chat']],
            'dest_email': [request.form['dest_email']]
        })
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(CSV_FILE, index=False)
        return redirect(url_for('index'))
    return render_template('add_row.html')

@app.route('/delete_row/<int:index>')
def delete_row(index):
    ensure_csv_exists()
    df = pd.read_csv(CSV_FILE)
    df = df.drop(index)
    df.to_csv(CSV_FILE, index=False)
    return redirect(url_for('index'))

@app.route('/update_timer', methods=['POST'])
def update_timer():
    new_timer_value = request.form['new_timer_value']
    # Регулярное выражение для проверки формата hh:mm:ss
    time_pattern = re.compile(r'^\d{2}:\d{2}:\d{2}$')
    if time_pattern.match(new_timer_value):
        write_timer_file(new_timer_value)
        flash('Timer value updated successfully.', 'success')
    else:
        flash('Invalid timer format. Please use hh:mm:ss.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
