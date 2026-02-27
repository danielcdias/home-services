@ECHO OFF
REM Script para carregar dados de produção para o ambiente local
REM Certifique-se de que o arquivo prod_data.json esteja localizado em D:\temp\
DEL db.sqlite3
python manage.py migrate
python manage.py loaddata D:\temp\prod_data.json
