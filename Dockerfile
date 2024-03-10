FROM python:3.10

# 設定工作目錄在容器內部
WORKDIR /usr/src/app

# 將當前目錄下的檔案複製到容器的工作目錄中
COPY . .

# 預先執行一些東西
RUN pip install -r requirements.txt

