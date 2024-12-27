import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import json
import time
import argparse
import requests
import subprocess

from datetime import datetime
from data.data_store import update, data_store_init
from flask import Flask, request, jsonify

#flask init
app = Flask(__name__)

stop_requested = False #종료 상태 변수
edge_id=None

# JSON 파일의 상대 경로 지정
JSON_FILE_PATH = os.path.join('..', 'data', 'data_store.json')
JSON_FILE_PATH = 'data_store.json'
SERVER_URL = 'http://203.250.35.96:5000'
CHECK_INTERVAL = 5  # 서버 신호 확인 간격
SEND_INTERVAL = 5  # 데이터 전송 간격


def load_data():
    '''전송될 데이터 불러오는 함수'''
    formatted_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    update(
        time=formatted_time # 포맷된 시간
    )
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            return data
    except FileNotFoundError:
        print("Error: Data store file not found.")
        return None
    
@app.route('/start_signal', methods=['POST', 'GET'])  # GET과 POST 둘 다 처리
def start_signal():
    global stop_requested

    # GET 요청 처리 (상태 확인)
    if request.method == 'GET':  
        return jsonify({"status": "alive"})  # 상태 확인 응답

    # POST 요청 처리 (신호 수신)
    stop_requested = False
    signal_data = request.get_json()
    if signal_data.get("start") is True:
        run_inf()  # inf.py 실행
    return jsonify({"message": "Signal received"}), 200



@app.route('/stop_signal', methods=['POST'])
def stop_signal():
    """서버에서 종료 신호를 받으면 데이터 전송 중지"""
    global stop_requested
    stop_requested = True
    print("Received stop signal. Stopping data transmission...")
    return jsonify({"message": "Stop signal received"}), 200

def send_data_to_server():
    '''추론 중 json 데이터 전송 함수'''
    data = load_data()
    if data:
        try:
            response = requests.post(f'{SERVER_URL}/receive_data', json=data)
            response.raise_for_status()
            print(response.json())
        except requests.exceptions.Timeout:
            print("Error: Request timed out.")
        except requests.exceptions.ConnectionError:
            print("Error: Connection error occurred.")
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
    else:
        print("Failed to load data from JSON.")
 
def run_inf():
    """inf.py 파일 실행 및 1분마다 데이터 전송 시작"""
    global stop_requested
    # inf.py 실행
    if os.path.isfile('inf.py'):
        subprocess.Popen(['python', 'inf.py'])
    # 1분마다 데이터 전송
    while not stop_requested:
        send_data_to_server()
        time.sleep(SEND_INTERVAL)
        

def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=str, default='0', help='Edge device ID')
    parser.add_argument('--location', type=str, default='Korea', help='Location name')
    parser.add_argument('--gps', type=str, default='Unknown', help='GPS coordinates')
    
    opt = parser.parse_args()
    return opt

if __name__ == '__main__':
    args = parse_opt()

    data_store_init(
        edge_id=args.id,
        location_name=args.location,
        gps=args.gps
    )
    port=5000+int(args.id)
    app.run(debug=True, host='0.0.0.0', port=port) #edge port : 5001 ~~ (5000은 서버)
