from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import mysql.connector
import jwt
from datetime import datetime, timedelta
from functools import wraps
import json
import logging
import os

# ログ設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
SECRET_KEY = "sadjfljsiejfoj"
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})


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
            time = row['time'].strftime("%a, %d %b %Y %H:%M:%S GMT") if isinstance(row['time'], datetime) else row['time']

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
            time = row['time'].strftime("%a, %d %b %Y %H:%M:%S GMT") if isinstance(row['time'], datetime) else row['time']

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
    user = data.get("user")
    pw = data.get("pw")

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('INSERT INTO account(user, pas) VALUES(%s, %s)', (user, pw))
    connection.commit()

    if cursor.rowcount == 1:
        return jsonify({'success': True, 'name': user}), 200
    else:
        return jsonify({'success': False}), 210

@app.route('/card/add', methods=['POST'])
def card_add():
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    try:
        cur = connection.cursor()
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

        # 必須フィールドの取得とバリデーション
        name = data.get('name')
        detail = data.get('detail')
        tag = data.get('tag')
        userid = data.get('userid')

        if not all([name, detail, tag, userid]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        # JSON のタグを文字列に変換して保存
        tag_str = json.dumps(tag)

        # クエリ実行
        cur.execute(
            'INSERT INTO card (name, detail, tag, userid) VALUES (%s, %s, %s, %s)',
            (name, detail, tag_str, userid)
        )
        connection.commit()

        if cur.rowcount == 1:
            return jsonify({'success': True, 'name': name}), 200
        else:
            return jsonify({'success': False, 'message': 'Insert failed'}), 500
    except mysql.connector.Error as e:
        logger.error(f"Database query failed: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500
    finally:
        cur.close()
        connection.close()

# ログイン処理
@app.route('/login', methods=['POST'])
def login():
    connection = get_db_connection()
    data = request.json
    
    try:
        if request.method == 'POST':
            user = data.get('name')
            pw = data.get('password')
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT user, pas, userid FROM account WHERE user = %s", (user,))
            data2 = cursor.fetchall()
            cursor.close()

            if data2:
                if data2[0]['pas'] == pw:
                    if not user or not pw:
                        return jsonify({'error': 'user and pw are required.'}), 400

                    # JWTを作成 (有効期限を2日後に設定)
                    id = data2[0]['userid']  # idを取得
                    payload = {
                        'user': user,
                        'id': id,  # idをペイロードに追加
                        'exp': datetime.utcnow() + timedelta(days=2)  # 2日後に設定
                    }
                    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

                    if isinstance(token, bytes):
                        token = token.decode('utf-8')

                    response = make_response(jsonify({'message': 'Token created', 'success': True}))

                    # 現在時刻から2日後を設定
                    expires = datetime.utcnow() + timedelta(days=2)

                    # expiresをHTTP日付形式に変換
                    expires_str = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')

                    # クッキーをセット
                    response.set_cookie(
                        'myapp_token', 
                        token, 
                        httponly=True, 
                        secure=True,  # HTTPS通信を使っている場合はTrue
                        samesite='None',  # クロスサイトリクエストでも送信
                        expires=expires_str  # expiresを文字列で設定
                    )

                    return response
                else:
                    return jsonify({'success': False}), 202
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

@app.route('/logout', methods=['POST'])
def logout():
    try:
        response = make_response(jsonify({'message': 'Logged out successfully', 'success': True}))
        response.set_cookie('myapp_token', '', expires=0, httponly=True, secure=True, samesite='None')
        return response
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/mypage', methods=['GET'])
def get_mypage():
    try:
        # クエリパラメータからデータを取得
        name = request.args.get('name')
        user_id = request.args.get('id')
        # 必須パラメータのバリデーション
        if not name or not user_id:
            return jsonify({"error": "入力が無効です"}), 400
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT COUNT(name) AS sum, COALESCE(SUM(heart), 0) AS total_heart
            FROM card
            WHERE userid = (
                SELECT userid
                FROM account
                WHERE user = %s AND userid = %s
            );
        """
        cursor.execute(query, (name, user_id))
        result = cursor.fetchone()
        # 結果が見つからない場合の処理
        if not result or result["sum"] == 0:
            return jsonify({"error": "データが見つかりません"}), 404
        cursor.close()
        connection.close()
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": "サーバーエラーが発生しました", "details": str(e)}), 500

@app.route('/card/detail', methods=['GET'])
def detail():
    try:
        # クエリパラメータからカードIDを取得
        card_id = request.args.get('id')
        if not card_id:
            return jsonify({"error": "入力が無効です"}), 400
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)  
        query = """
        SELECT card.*, account.user
        FROM card
        JOIN account ON card.userid = account.userid
        WHERE card.cardid = %s;
        """
        cursor.execute(query, (card_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "カードが見つかりません"}), 404
        cursor.close()
        connection.close()
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": "サーバーエラーが発生しました", "details": str(e)}), 500
    
@app.route('/mk', methods=['GET'])
def mk():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)  
        query = "SELECT detail FROM card WHERE cardid = 8;"
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
@app.route('/user_ranking',methods=['GET'])
def rank():
    try:
        connection = get_db_connection()  
        cursor = connection.cursor(dictionary=True)  
        query = """
        SELECT account.user, SUM(card.heart) AS total_hearts
        FROM card
        JOIN account ON card.userid = account.userid
        GROUP BY account.user
        ORDER BY total_hearts DESC
        LIMIT 3;
        """
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "サーバーエラーが発生しました", "details": str(e)}), 500

@app.route('/Getcard',methods=['GET'])
def get():
    card_id = request.args.get('id')
    try:
        connection = get_db_connection()  
        cursor = connection.cursor(dictionary=True)
        query = """
                    SELECT * 
                    FROM card 
                    WHERE cardid = %s;
                """
        cursor.execute(query,(card_id,))
        result = cursor.fetchone()
        cursor.close()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "サーバーエラーが発生しました", "details": str(e)}), 500
    
@app.route('/Fixcard',methods=['PUT'])
def putCard():
    data = request.json
    connection = get_db_connection()
    cur = connection.cursor()
    try:
        name = data.get('name')
        detail = data.get('detail')
        tag = json.dumps(data.get('tag'))
        cardid = data.get('cardid')
        query = """
                UPDATE card
                SET name = %s, detail = %s, tag = %s
                WHERE cardid = %s
                """
        cur.execute(query,(name,detail,tag,cardid,))
        connection.commit()
        if cur.rowcount == 1:
            return jsonify({'succeess':True,'name':name}),200
    except Exception as e:
        return jsonify({"error": "サーバーエラーが発生しました", "details": str(e)}), 500

@app.route('/like', methods=['GET'])
def like():
    connection = get_db_connection()
    cur = connection.cursor()
    try:
        userid = request.args.get("userid")
        cardid = request.args.get("cardid")
        query = """
                SELECT * 
                FROM likes
                WHERE userid = %s AND cardid = %s
                """
        cur.execute(query, (userid, cardid,))
        
        # 結果を実際に取得する
        result = cur.fetchone()
        if result is not None:
            return jsonify({'success': False,})
        else:
            return jsonify({'success': True,})
    except Exception as e:
        return jsonify({"error": "サーバーエラーが発生しました", "details": str(e)}), 500

@app.route('/like', methods=["POST"])
def likeadd():
    connection = get_db_connection()
    cur = connection.cursor()
    data = request.json
    try:
        userid = data.get("userid")
        cardid = data.get("cardid")

        # likesテーブルにすでに存在するかを確認
        check_query = "SELECT COUNT(*) FROM likes WHERE userid = %s AND cardid = %s"
        cur.execute(check_query, (userid, cardid))
        like_exists = cur.fetchone()[0]

        if like_exists:
            return jsonify({"error": "既にいいねされています"}), 400

        # トランザクション開始
        connection.autocommit = False  # トランザクション開始を明示的に指定

        # likesテーブルに新しいレコードを挿入
        insert_query = """
            INSERT INTO likes (userid, cardid)
            VALUES (%s, %s)
        """
        cur.execute(insert_query, (userid, cardid))

        # cardテーブルのheartカウントをインクリメント
        update_query = """
            UPDATE card
            SET heart = heart + 1
            WHERE cardid = %s
        """
        cur.execute(update_query, (cardid,))

        # トランザクションコミット
        connection.commit()

        return jsonify({"success": True, "message": "いいねが追加されました"}), 200
    except Exception as e:
        # トランザクションロールバック
        connection.rollback()
        return jsonify({"error": "サーバーエラーが発生しました", "details": str(e)}), 500
    finally:
        cur.close()
        
@app.route("/like", methods=["DELETE"])
def likedel():
    cardid = request.args.get("cardid")
    userid = request.args.get("userid")
    try:
        connection = get_db_connection()
        cur = connection.cursor()
        
        # likesテーブルから指定されたuseridとcardidのレコードを削除
        delete_query = """
                DELETE FROM likes
                WHERE userid = %s AND cardid = %s
        """
        cur.execute(delete_query, (userid, cardid))
        
        # cardテーブルのheartを1減らす
        update_query = """
                UPDATE card
                SET heart = heart - 1
                WHERE cardid = %s
        """
        cur.execute(update_query, (cardid,))
        
        # トランザクションをコミット
        connection.commit()
        
        return jsonify({"success": True, "message": "いいねが削除されました"}), 200

    except Exception as e:
        # エラーが発生した場合、トランザクションをロールバック
        mysql.connection.rollback()
        return jsonify({"error": "サーバーエラーが発生しました", "details": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)