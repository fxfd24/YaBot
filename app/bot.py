import requests
import smtplib as smtp
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
import os
import time
import pandas as pd
import re
import logging
from datetime import datetime
import threading

# Настройка логирования
logging.basicConfig(filename='telegram_bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_updates(updates):
    with open('telegram_bot.log', 'a') as log_file:
        log_file.write(f"{updates}\n\n")

def check_and_create_timer_file(delay_timer):
    filename = "timer.txt"
    # Проверяем, существует ли файл
    if not os.path.exists(filename):
        # Если файл не существует, создаем его
        with open(filename, 'w') as file:
            # Записываем текущее время в файл
            file.write(delay_timer)

def get_timer_file(filename):
    with open(filename, 'r') as file:
        value = file.read().strip()
        return value

delay_timer = "00:01:00"
check_and_create_timer_file(delay_timer)

# Telegram bot token
TELEGRAM_BOT_TOKEN = '7876742659:AAFfD7H1lYPqXocj1zbs7oZUrZMbatsby5k'
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/'
# Email credentials
email = 'order@digitaldemon.studio'  # Ensure this is your full email address
password = 'nsqcnkwydcmpqfnk'  # Use an app-specific password if 2FA is enabled
subject = 'Заказ от КЛИКЛАБ'
CSV_FILE = 'data.csv'
CSV_FILE_TIMER = 'data_timer.csv'

# Функция для проверки существования файла и его создания, если он отсутствует
def ensure_csv_exists():
    if not os.path.isfile(CSV_FILE):
        # Создаем DataFrame с нужными колонками
        df = pd.DataFrame(columns=['target_chat_id', 'name_chat', 'dest_email'])
        # Сохраняем его в CSV-файл
        df.to_csv(CSV_FILE, index=False)

def ensure_csv_timer_exists():
    if not os.path.isfile(CSV_FILE_TIMER):
        # Создаем DataFrame с нужными колонками
        df = pd.DataFrame(columns=['target_chat_id', 'dest_email', 'sms_id'])
        # Сохраняем его в CSV-файл
        df.to_csv(CSV_FILE_TIMER, index=False)

ensure_csv_exists()
ensure_csv_timer_exists()

def add_row_to_csv(target_chat_id, dest_email, sms_id):
    ensure_csv_timer_exists()

    # Читаем существующий CSV-файл
    df = pd.read_csv(CSV_FILE_TIMER)

    # Создаем новую строку
    new_row = pd.DataFrame([{'target_chat_id': target_chat_id, 'dest_email': dest_email, 'sms_id': sms_id}])

    # Добавляем новую строку в DataFrame
    df = pd.concat([df, new_row], ignore_index=True)

    # Сохраняем обновленный DataFrame обратно в CSV-файл
    df.to_csv(CSV_FILE_TIMER, index=False)

def remove_row_by_sms_id(sms_id):
    ensure_csv_timer_exists()

    # Читаем существующий CSV-файл
    df = pd.read_csv(CSV_FILE_TIMER)

    # Удаляем строки, где значение в колонке 'sms_id' равно переданному значению
    df = df[df['sms_id'] != sms_id]

    # Сохраняем обновленный DataFrame обратно в CSV-файл
    df.to_csv(CSV_FILE_TIMER, index=False)


def check_and_remove_sms_id(chat_id, sms_id):
    # try:
    if chat_id and sms_id and TELEGRAM_BOT_TOKEN:
        return set_telegram_reaction(chat_id, sms_id, TELEGRAM_BOT_TOKEN, "👨‍💻")

    # except Exception as e:
    #     print("смс удалено из чата")
    #     return False


def add_message_id_to_csv(chat_id, dest_email, message_id):
    ensure_csv_timer_exists()

    # Читаем существующий CSV-файл
    df = pd.read_csv(CSV_FILE_TIMER)

    # Создаем новую строку
    new_row = pd.DataFrame([{'target_chat_id': chat_id, 'dest_email': dest_email, 'sms_id': message_id}])

    # Добавляем новую строку в DataFrame
    df = pd.concat([df, new_row], ignore_index=True)

    # Сохраняем обновленный DataFrame обратно в CSV-файл
    df.to_csv(CSV_FILE_TIMER, index=False)

def check_timer_and_remove_sms_id(chat_id, sms_id, delay_timer, file_id, file_path, text, dest_email, file_name, message_id):
    # Получаем текущее время
    current_time = datetime.now()

    # Преобразуем delay_timer в объект timedelta
    delay_time = datetime.strptime(delay_timer, "%H:%M:%S") - datetime.strptime("00:00:00", "%H:%M:%S")

    # Вычисляем время окончания таймера
    end_time = current_time + delay_time

    # Ждем до окончания таймера
    while datetime.now() < end_time:
        time.sleep(1)

    # Проверяем и удаляем sms_id после истечения времени
    if check_and_remove_sms_id(chat_id, sms_id):
        # Выполняем команды после завершения таймера
        download_file(file_id, file_path)
        text = text + f'\n{file_path}'
        print(dest_email)
        send_email(text, file_path, dest_email, returner_number_order(file_name), int(chat_id), message_id, TELEGRAM_BOT_TOKEN)
    else:
        print(f"Сообщение с message_id {message_id} было удалено пользователем.")
        remove_row_by_sms_id(message_id)


# Функция для установки реакции на сообщение в Telegram
def set_telegram_reaction(chat_id, message_id, bot_token, reaction):
    url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'reaction': [{"type": "emoji", "emoji": reaction}]
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Telegram reaction set successfully.")
        return True
    else:
        print(f"Failed to set Telegram reaction: {response.text}")
        return False

def send_email(email_text, file_path=None, dest_email=None, order=None, telegram_chat_id=None, telegram_message_id=None, telegram_bot_token=None):
    remove_row_by_sms_id(telegram_message_id)
    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = email
    msg['To'] = dest_email
    msg['Subject'] = Header(subject + f' {order}', 'utf-8')

    # Attach the email body
    msg.attach(MIMEText(email_text, 'plain', 'utf-8'))

    # Attach the file if provided
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as attachment:
            part = MIMEBase('application', get_mime_type(file_path))
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename = files{get_file_type(file_path)}',
            )
            msg.attach(part)
    else:
        print(f"File {file_path} does not exist.")

    # Connect to the SMTP server
    server = smtp.SMTP_SSL('smtp.yandex.com', 465)
    server.set_debuglevel(1)
    server.ehlo(email)

    # Login to the SMTP server
    try:
        server.login(email, password)
    except smtp.SMTPAuthenticationError as e:
        print(f"Authentication failed: {e}")
        server.quit()
        return

    # Send the email
    try:
        server.sendmail(email, dest_email, msg.as_string())
        print("Email sent successfully.")

        # If the email is sent successfully, set a heart reaction in Telegram
        if telegram_chat_id and telegram_message_id and telegram_bot_token:
            set_telegram_reaction(telegram_chat_id, telegram_message_id, telegram_bot_token, "❤️")

    except Exception as e:
        print(f"Failed to send email: {e}")
        # If the email is sent successfully, set a heart reaction in Telegram
        if telegram_chat_id and telegram_message_id and telegram_bot_token:
            set_telegram_reaction(telegram_chat_id, telegram_message_id, telegram_bot_token, "💩")
            send_message(telegram_chat_id, f"Опаньки, файл не отправлен. \nКод ошибки (для прогера): \n\n{e}", telegram_bot_token, telegram_message_id)

    # Quit the server
    server.quit()
    if file_path:
        os.remove(file_path)

def get_mime_type(file_path):
    # Determine the MIME type based on the file extension
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == '.stl':
        return 'sla'
    elif file_extension == '.zip':
        return 'zip'
    elif file_extension == '.rar':
        return 'x-rar-compressed'
    else:
        return 'octet-stream'

def get_file_type(file_path):
    # Determine the MIME type based on the file extension
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == '.stl':
        return '.stl'
    elif file_extension == '.zip':
        return '.zip'
    elif file_extension == '.rar':
        return '.rar'
    else:
        return ''

def get_updates(offset=None):
    url = TELEGRAM_API_URL + 'getUpdates'
    params = {'offset': offset, 'timeout': 30}
    response = requests.get(url, params=params)
    return response.json()

def download_file(file_id, file_path):
    url = TELEGRAM_API_URL + 'getFile'
    params = {'file_id': file_id}
    response = requests.get(url, params=params).json()
    file_url = f'https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{response["result"]["file_path"]}'
    file_response = requests.get(file_url)
    with open(file_path, 'wb') as file:
        file.write(file_response.content)

def extract_first_word(input_string):
    # Регулярное выражение для извлечения первого слова
    pattern = r'[-_]([^_-]+)[-_]'
    match = re.search(pattern, input_string)
    if match:
        # Извлекаем первое слово и удаляем начальные и конечные символы
        word = match.group(1)
        return word
    else:
        return None

def check_file_name(file_name):
    # Регулярное выражение для проверки формата имени файла
    pattern = r'^\d{4}[-_]\d{3}'
    return re.match(pattern, file_name) is not None

def returner_number_order(file_name):
    # Регулярное выражение для проверки формата имени файла
    pattern = r'^\d{4}[-_]\d{3}'
    match = re.match(pattern, file_name)
    if match:
        number = file_name[:8]
        input_string = file_name[8:]
        pattern2 = r'[-_]([^_-]+)[-_]'
        match2 = re.search(pattern2, input_string)
        if match2:
            # Извлекаем первое слово и удаляем начальные и конечные символы
            word = match2.group(1)
            return number + ' ' + word
        else:
            return number
    return None

def send_message(chat_id, text, bot_token, reply_to_message_id=None):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    if reply_to_message_id:
        payload['reply_to_message_id'] = reply_to_message_id

    response = requests.post(url, data=payload)
    return response.json()

def main():
    offset = None
    while True:
        # Перечитываем CSV-файл при каждом получении обновлений
        df = pd.read_csv(CSV_FILE)
        all_target_chat_id = df['target_chat_id'].to_list()
        all_dest_email = df['dest_email'].to_list()

        df_timer = pd.read_csv(CSV_FILE_TIMER)
        all_target_chat_id_timer = df_timer['target_chat_id'].to_list()
        all_dest_email_timer = df_timer['dest_email'].to_list()
        all_sms_id_timer = df_timer['sms_id'].to_list()

        updates = get_updates(offset)
        logging.info(updates)  # Логирование обновлений
        log_updates(updates)  # Сохранение обновлений в файл
        print(updates)
        if updates['ok']:
            for update in updates['result']:
                if 'message' in update:
                    message = update['message']
                    if 'document' in message:
                        file_id = None
                        file_path = None
                        file_id = message['document']['file_id']
                        file_name = message['document']['file_name']
                        file_path = f"{file_name}"
                        chat_id = message['chat']['id']
                        text = message.get('text') or message.get('caption')
                        print(text)
                        if text:
                            print(str(chat_id))
                            print(all_target_chat_id)
                            if int(chat_id) in all_target_chat_id:
                                if check_file_name(file_name):
                                    if file_id:
                                        # добавить message['message_id'] в CSV_FILE_TIMER и выполнить логику ниже, когда пройдет время, заданное в get_timer_file("timer.txt")

                                        # Добавляем message['message_id'] в CSV_FILE_TIMER
                                        add_message_id_to_csv(chat_id, all_dest_email[all_target_chat_id.index(int(chat_id))], message['message_id'])
                                        try:
                                            set_telegram_reaction(chat_id, message['message_id'], TELEGRAM_BOT_TOKEN, "🥱")
                                        except:
                                            print('sad')
                                        # Запускаем таймер в отдельном потоке
                                        delay_timer = get_timer_file("timer.txt")
                                        timer_thread = threading.Thread(target=check_timer_and_remove_sms_id, args=(chat_id, message['message_id'], delay_timer, file_id, file_path, text, all_dest_email[all_target_chat_id.index(int(chat_id))], file_name, message['message_id']))
                                        timer_thread.start()
                                else:
                                    send_message(chat_id, "Заполни имя файла в формате 0000-000 и пришли ещё раз", TELEGRAM_BOT_TOKEN, reply_to_message_id=message['message_id'])

        offset = update['update_id'] + 1
        time.sleep(1)

if __name__ == '__main__':
    main()
