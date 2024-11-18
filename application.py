from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import mysql.connector
import jwt
import datetime
from functools import wraps
import json
import logging
import os

# ログ設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
SECRET_KEY = "sadjfljsiejfoj"
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "https://ambitious-beach-0099da600.5.azurestaticapps.net"}})

# Azure Database for MySQL 接続設定
DB_HOST = 'qiita.mysql.database.azure.com'  # Azure MySQL のホスト


DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# MySQL 接続関数
def get_db_connection():
    connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        ssl_ca='path/to/your/ssl/certificate.pem',  # 必要に応じてSSL証明書を設定
        ssl_disabled=False
    )
    return connection

# セッション用のデコレータ
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('myapp_token')

        if not token:
            return jsonify({'error': 'Token is missing!'}), 403

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 403

        return f(*args, **kwargs)

    return decorated

# ログインしたユーザー名とIDを返すデコレータ
def token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('myapp_token')

        if not token:
            return jsonify({'error': 'Token is missing!'}), 405

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 403

        name = data.get('user')
        user_id = data.get('id')
        return f(name=name, id=user_id, *args, **kwargs)

    return decorated

@app.route("/")
def index():
    return """
    <h1>Welcome!</h1>
    <div><a href='/order/time'>タイム</a></div>
    <div><a href='/order/trend'>トレンド</a></div>
    """

# 時間順のカード情報を取得
@app.route("/order/time", methods=['GET'])
def get_order_time():
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                c.cardid,
                c.name,
                c.detail,
                c.tag,
                c.heart,
                c.time,
                c.userid,
                a.user AS username
            FROM 
                card c
            JOIN 
                account a ON c.userid = a.userid
            ORDER BY 
                c.time DESC;
        """)
        data = cursor.fetchall()

        # ローカル形式にデータを変換
        formatted_data = []
        for row in data:
            # 時間のフォーマットを変更
            time = row['time'].strftime("%a, %d %b %Y %H:%M:%S GMT") if isinstance(row['time'], datetime.datetime) else row['time']

            # ローカルデータ形式に合わせて整形
            formatted_data.append([
                row['cardid'],
                row['name'],
                row['detail'],
                row['tag'],
                row['heart'],
                time,
                row['userid'],
                row['username']
            ])

        return jsonify(formatted_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()


# いいね数順のカード情報を取得
@app.route("/order/trend", methods=['GET'])
def get_order_trend():
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                c.cardid,
                c.name,
                c.detail,
                c.tag,
                c.heart,
                c.time,
                c.userid,
                a.user AS username
            FROM 
                card c
            JOIN 
                account a ON c.userid = a.userid
            ORDER BY 
                c.heart DESC;
        """)
        data = cursor.fetchall()
        # ローカル形式にデータを変換
        formatted_data = []
        for row in data:
            # 時間のフォーマットを変更
            time = row['time'].strftime("%a, %d %b %Y %H:%M:%S GMT") if isinstance(row['time'], datetime.datetime) else row['time']

            # ローカルデータ形式に合わせて整形
            formatted_data.append([
                row['cardid'],
                row['name'],
                row['detail'],
                row['tag'],
                row['heart'],
                time,
                row['userid'],
                row['username']
            ])

        return jsonify(formatted_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

# アカウント認証
@app.route('/account/verification', methods=['POST'])
def account_verification():
    data = request.json
    if request.method == 'POST':
        user = data['data'][0]
        pw = data['data'][1]

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT user, pas FROM account WHERE user = %s", (user,))
        data2 = cursor.fetchall()
        cursor.close()

        if data2:
            if data2[0][1] == pw:
                return jsonify({'success': True, 'name': user}), 201
            else:
                return jsonify({'success': False}), 202
        return jsonify({'success': False}), 404

# アカウント作成
@app.route('/account/add', methods=['POST'])
def account_add():
    data = request.json
    user = data['data'][0]
    pw = data['data'][1]

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('INSERT INTO account(user, pas) VALUES(%s, %s)', (user, pw))
    connection.commit()

    if cursor.rowcount == 1:
        return jsonify({'success': True, 'name': user}), 200
    else:
        return jsonify({'success': False}), 210

# ログイン処理
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    try:
        if request.method == 'POST':
            user = data.get('name')
            pw = data.get('password')

            # データベース接続を開く
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT user, pas, userid FROM account WHERE user = %s", (user,))
            data2 = cursor.fetchall()
            cursor.close()

            # ログ出力: データベースの結果を確認
            logger.debug(f"Database query result: {data2}")

            if data2:
                if data2[0][1] == pw:
                    # JWTを生成
                    id = data2[0][2]
                    payload = {
                        'user': user,
                        'id': id,
                        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=10)  # 有効期限
                    }
                    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

                    # トークンの型確認
                    if isinstance(token, bytes):
                        token = token.decode('utf-8')

                    response = make_response(jsonify({'message': 'Token created', 'success': True}))
                    response.set_cookie('myapp_token', token, httponly=True, secure=False)

                    return response
                else:
                    logger.error(f"Invalid password for user: {user}")
                    return jsonify({'success': False}), 401  # Unauthorized
            else:
                logger.error(f"User not found: {user}")
                return jsonify({'error': 'Invalid credentials'}), 404  # Not Found

    except Exception as e:
        logger.error(f"Error during login: {str(e)}")  # エラー内容をログに記録
        return jsonify({'error': str(e), 'success': False}), 500

# ログアウト処理
@app.route('/logout', methods=['POST'])
def logout():
    try:
        response = make_response(jsonify({'message': 'Logged out successfully', 'success': True}))
        response.set_cookie('myapp_token', '', expires=0, httponly=True, secure=False)
        return response
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

# 特別ページ（認証されたユーザー専用）
@app.route('/special', methods=['GET'])
@token_required
def special():
    return jsonify({'message': 'This is a special page for logged-in users!'})

# ユーザー名とIDを取得するためのエンドポイント
@app.route('/confirmation_name', methods=['GET'])
@token
def required(name, id):
    return jsonify({'name': name, 'id': id})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)