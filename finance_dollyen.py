import yfinance as yf
import requests
import os
import logging
import json
from datetime import datetime, timedelta

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def get_exchange_rate():
    ticker = yf.Ticker("USDJPY=X")
    try:
        data = ticker.info
        if 'regularMarketPrice' in data:
            rate = data['regularMarketPrice']
            logging.debug(f"yfinance APIから取得したレート: {rate}")
            return rate
        
        hist = ticker.history(period="1d")
        if not hist.empty:
            rate = hist['Close'].iloc[-1]
            logging.debug(f"yfinance 履歴データから取得したレート: {rate}")
            return rate
        
        raise ValueError("Exchange rate data not available")
    except Exception as e:
        logging.error(f"為替レート取得エラー: {e}")
        return None

def send_line_notification(message):
    line_notify_token = os.environ.get('LINE_NOTIFY_TOKEN')
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    data = {'message': message}
    
    logging.debug(f"LINE通知を送信しようとしています: {message}")
    try:
        response = requests.post(line_notify_api, headers=headers, data=data)
        response.raise_for_status()
        logging.info(f"LINE通知を送信しました。ステータスコード: {response.status_code}")
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
            last_time = datetime.fromisoformat(data['last_notification'])
            logging.debug(f"読み込んだ最終通知時刻: {last_time}")
            return last_time
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logging.error(f"最終通知時刻の読み込み中にエラーが発生しました: {e}")
        return datetime.min

def main():
    try:
        target_rate = float(os.environ.get('TARGET_RATE', 110.0))
        notification_interval = timedelta(minutes=int(os.environ.get('NOTIFICATION_INTERVAL', 60)))
        
        logging.info(f"設定値 - 目標レート: {target_rate}, 通知間隔: {notification_interval}")
        
        current_rate = get_exchange_rate()
        
        if current_rate is not None:
            logging.info(f"現在のドル円レート: {current_rate:.2f}")
            
            last_notification = load_last_notification_time()
            now = datetime.now()
            
            logging.debug(f"最終通知時刻: {last_notification}, 現在時刻: {now}")
            
            if current_rate >= target_rate:
                logging.info(f"現在のレート（{current_rate}）が目標レート（{target_rate}）以上です。")
                if now - last_notification >= notification_interval:
                    logging.info("通知間隔を超えました。LINE通知を送信します。")
                    message = f"\nドル円レートが{target_rate}円に達しました。\n現在のレート: {current_rate:.2f}円"
                    if send_line_notification(message):
                        save_last_notification_time(now)
                else:
                    logging.info("通知間隔内です。通知は送信されません。")
            else:
                logging.info(f"現在のレート（{current_rate}）が目標レート（{target_rate}）未満です。通知は送信されません。")
        else:
            logging.warning("レートの取得に失敗しました。")
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)

if __name__ == "__main__":
    main()
