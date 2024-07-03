import yfinance as yf
import requests
import os
import logging
import json
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_exchange_rate():
    ticker = yf.Ticker("USDJPY=X")
    try:
        data = ticker.info
        if 'regularMarketPrice' in data:
            return data['regularMarketPrice']
        
        hist = ticker.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        
        raise ValueError("Exchange rate data not available")
    except Exception as e:
        logging.error(f"Error fetching exchange rate: {e}")
        return None

def send_line_notification(message):
    line_notify_token = os.environ.get('LINE_NOTIFY_TOKEN')
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    data = {'message': message}
    
    try:
        response = requests.post(line_notify_api, headers=headers, data=data)
        response.raise_for_status()
        logging.info("LINE通知を送信しました")
        return True
    except requests.RequestException as e:
        logging.error(f"LINE通知送信エラー: {e}")
        return False

def save_last_notification_time(time):
    data = {'last_notification': time.isoformat()}
    try:
        with open('last_notification.json', 'w') as f:
            json.dump(data, f)
        logging.info(f"最終通知時刻を保存しました: {time.isoformat()}")
    except IOError as e:
        logging.error(f"最終通知時刻の保存中にエラーが発生しました: {e}")

def load_last_notification_time():
    if not os.path.exists('last_notification.json'):
        logging.info("last_notification.jsonが存在しません。デフォルトの時刻で作成します。")
        save_last_notification_time(datetime.min)
        return datetime.min
    try:
        with open('last_notification.json', 'r') as f:
            data = json.load(f)
            return datetime.fromisoformat(data['last_notification'])
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logging.error(f"最終通知時刻の読み込み中にエラーが発生しました: {e}")
        return datetime.min

def main():
    try:
        target_rate = float(os.environ.get('TARGET_RATE', 110.0))
        notification_interval = timedelta(minutes=int(os.environ.get('NOTIFICATION_INTERVAL', 60)))
        
        current_rate = get_exchange_rate()
        
        if current_rate is not None:
            logging.info(f"現在のドル円レート: {current_rate:.2f}")
            
            last_notification = load_last_notification_time()
            now = datetime.now()
            
            if current_rate >= target_rate and now - last_notification >= notification_interval:
                message = f"\nドル円レートが{target_rate}円に達しました。\n現在のレート: {current_rate:.2f}円"
                if send_line_notification(message):
                    save_last_notification_time(now)
        else:
            logging.warning("レートの取得に失敗しました。")
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
