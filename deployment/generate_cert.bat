@echo off
mkdir nginx\certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx\certs\server.key -out nginx\certs\server.crt -subj "/C=FI/ST=NorthOstrobothnia/L=Oulu/O=DBMS/CN=localhost"
echo Certificate generated in nginx/certs/
pause