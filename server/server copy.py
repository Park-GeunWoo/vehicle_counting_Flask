import csv
import logging
import threading
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

CSV_FILE_PATH = 'vehicle_data.csv'
CLIENT_URL = 'http://localhost:5001'  # 경로에서 '/start_signal' 제거
CLIENT_URS=[
    'http://localhost:5001',
    'http://localhost:5002',
    'http://localhost:5003'
]

stop_requested_lock = threading.Lock()
stop_requested = threading.Event()

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def init_csv_file():
    try:
        with open(CSV_FILE_PATH, mode='x', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Edge ID', 'Location', 'GPS', 'Time', 'Count'])
    except FileExistsError:
        pass

def input_user_command():
    command=input("'start' to send start signal, 'stop' to send the stop signal: ").strip().lower()
    return command

def send_start_signal():
    global stop_requested
    print("Sending start signal...")
    try:
        requests.post(f'{CLIENT_URL}/start_signal', json={"start": True})
    except requests.exceptions.RequestException as e:
        print(f"Error sending start signal: {e}")

@app.route('/receive_data', methods=['POST'])
def receive_data():
    data = request.get_json()
    count = data.get('count')
    data_store = data.get('data_store', {})
    edge_id = data_store.get('edge_id')
    location_name = data_store.get('location_name')
    gps_point = data_store.get('gps')
    time = data_store.get('time')

    with open(CSV_FILE_PATH, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([edge_id, location_name, gps_point, time, count])
    return jsonify({
        "message": f"ID {edge_id}, Received {location_name}, GPS {gps_point}, Count {count}, Time {time}"
    })

@app.route('/view_data')
def view_data():
    with open(CSV_FILE_PATH, mode='r') as file:
        csv_data = list(csv.reader(file))
    return render_template('view_data.html', data=csv_data)

@app.route('/start_signal', methods=['POST'])
def start_signal():
    """Clinet inf.py 실행 신호 전송"""
    return jsonify({"start": True})

@app.route('/stop_signal', methods=['POST'])
def stop_signal():
    """clinet 종료 신호 전송"""
    return jsonify({"stop": True})

def listen_for_signals():
    """콘솔에서 'start' 또는 'stop' 입력을 대기하고, 신호를 클라이언트로 전송"""
    global stop_requested
    task_thread = None
    while True:
        input_command=input_user_command()
        
        if input_command == 'start':
            if task_thread is None or not task_thread.is_alive():
                stop_requested.clear()
                task_thread=threading.Thread(target=send_start_signal)
                task_thread.start()
            else:
                print("Already running. Enter 'stop' to stop the process")
                
        elif input_command == 'stop':
            stop_requested.set()
            try:
                response = requests.post(f"{CLIENT_URL}/stop_signal", json={"stop": True})
                if response.status_code == 200:
                    print("Stop signal sent") 
                else:
                    print("Failed to send stop signal.")
            except requests.exceptions.RequestException as e:
                print(f"Error sending stop signal: {e}")

            if task_thread is not None:
                task_thread.join()
                task_thread = None
                
if __name__ == '__main__':
    init_csv_file()
    threading.Thread(target=listen_for_signals, daemon=True).start()  #'start' 입력 대기 스레드 시작
    app.run(debug=True, host='0.0.0.0', port=5000)
