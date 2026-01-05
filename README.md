# Where is Nagi? - Adafruit IO 位置送信アプリ

Adafruit IO を介して MQTT 接続された M5Stack ATOM Lite に「現在地」を送信するための Streamlit Web アプリケーションです。

## 機能

- 4つの場所（研究室、大学構内、自宅、その他）から選択して送信
- 最後に送信した値と時刻を表示
- エラーハンドリング付き

## 必要な環境変数

以下の環境変数を設定してください：

- `AIO_USERNAME`: Adafruit IO のユーザー名
- `AIO_KEY`: Adafruit IO の API キー

## ローカルでの実行方法

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

#### macOS/Linux

```bash
export AIO_USERNAME="your_username"
export AIO_KEY="your_api_key"
```

#### Windows (PowerShell)

```powershell
$env:AIO_USERNAME="your_username"
$env:AIO_KEY="your_api_key"
```

#### Windows (Command Prompt)

```cmd
set AIO_USERNAME=your_username
set AIO_KEY=your_api_key
```

### 3. アプリケーションの起動

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

## Streamlit Cloud でのデプロイ方法

### 1. GitHub リポジトリにプッシュ

このプロジェクトを GitHub リポジトリにプッシュしてください。

### 2. Streamlit Cloud でアプリを作成

1. [Streamlit Cloud](https://streamlit.io/cloud) にアクセス
2. "New app" をクリック
3. GitHub リポジトリを選択
4. Branch、Main file path (`app.py`) を指定

### 3. 環境変数の設定

Streamlit Cloud のアプリ設定画面で、以下の Secrets を追加：

```
AIO_USERNAME = "your_username"
AIO_KEY = "your_api_key"
```

または、Settings > Secrets から以下の形式で追加：

```toml
AIO_USERNAME = "your_username"
AIO_KEY = "your_api_key"
```

### 4. デプロイ

"Deploy" をクリックしてデプロイを開始します。

## Adafruit IO 側で必要な設定

### 1. Feed の作成

1. [Adafruit IO](https://io.adafruit.com/) にログイン
2. "Feeds" タブを開く
3. "New Feed" をクリック
4. Feed 名を `where` として作成

### 2. API キーの取得

1. Adafruit IO のダッシュボードで "My Key" をクリック
2. "Active Key" をコピー（これが `AIO_KEY` になります）
3. ユーザー名も確認（これが `AIO_USERNAME` になります）

### 3. M5Stack ATOM Lite 側の設定

ATOM Lite 側は既に以下の設定で動作している前提です：

- Feed 名: `where`
- MQTT トピック: `{username}/feeds/where`
- 値の形式: `"LAB"`, `"CAMPUS"`, `"HOME"`, `"ELSE"` のいずれか

## 送信される値

- `LAB`: 研究室
- `CAMPUS`: 大学構内
- `HOME`: 自宅
- `ELSE`: その他

## トラブルシューティング

### エラー: "環境変数 AIO_USERNAME または AIO_KEY が設定されていません"

→ 環境変数が正しく設定されているか確認してください。

### エラー: "通信エラー: 401 Unauthorized"

→ API キーが正しいか確認してください。

### エラー: "通信エラー: 404 Not Found"

→ Feed 名が `where` で正しく作成されているか、ユーザー名が正しいか確認してください。

## ライセンス

MIT

