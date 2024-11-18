## Mysqlスキーマ定義
```
CREATE TABLE account (
    userid INT AUTO_INCREMENT PRIMARY KEY,
    user VARCHAR(255) NOT NULL,
    pas VARCHAR(255) NOT NULL
);


CREATE TABLE card (
    cardid INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    detail TEXT,
    tag JSON,  
    heart INT DEFAULT 0,
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    userid INT,
    FOREIGN KEY (userid) REFERENCES account(userid) 
);

```
### テスト用データ
```
INSERT INTO account (user, pas) 
VALUES
('user1', 'password1'),
('user2', 'password2'),
('user3', 'password3'),
('user4', 'password4'),
('user5', 'password5'),
('user6', 'password6'),
('user7', 'password7'),
('user8', 'password8'),
('user9', 'password9'),
('user10', 'password10');


INSERT INTO card (name, detail, tag, heart, userid) 
VALUES
('Card 1', 'Detail of card 1', JSON_ARRAY('tag1', 'tag2'), 0, 1),
('Card 2', 'Detail of card 2', JSON_ARRAY('tag1', 'tag3'), 0, 2),
('Card 3', 'Detail of card 3', JSON_ARRAY('tag2', 'tag4'), 0, 3),
('Card 4', 'Detail of card 4', JSON_ARRAY('tag5'), 0, 4),
('Card 5', 'Detail of card 5', JSON_ARRAY('tag2', 'tag6'), 0, 5),
('Card 6', 'Detail of card 6', JSON_ARRAY('tag3', 'tag7'), 0, 6),
('Card 7', 'Detail of card 7', JSON_ARRAY('tag4', 'tag8'), 0, 7),
('Card 8', 'Detail of card 8', JSON_ARRAY('tag5', 'tag9'), 0, 8),
('Card 9', 'Detail of card 9', JSON_ARRAY('tag1', 'tag7'), 0, 9),
('Card 10', 'Detail of card 10', JSON_ARRAY('tag2', 'tag8'), 0, 10);

```

## 仮想環境を構築
```
py -3 -m venv venv
```
## 仮想環境上に移動
```
venv\Scripts\activate
```
## flaskをインストール
```
pip install Flask
pip install pyjwt
```


## 環境変数を定義
```
$env:FLASK_APP = "main"
```

## flaskを起動
```
$env:DB_USER=""
$env:DB_PASSWORD=""
$env:DB_NAME=""
flask run
```
