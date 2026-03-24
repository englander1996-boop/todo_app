# 1. ベースとなる環境（軽量なPython 3.9）を用意する
FROM python:3.9-slim

# 2. コンテナの中での作業ディレクトリを /app に決める
WORKDIR /app

# 3. 必要なライブラリのメモ帳をコピーして、インストールする
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 今のフォルダにあるファイル（main.pyなど）をすべてコンテナにコピーする
COPY . .

# 5. コンテナが起動したときに、FastAPIのサーバーを立ち上げるコマンド
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]