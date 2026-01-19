from pydrive2.auth import GoogleAuth
gauth = GoogleAuth()
gauth.LocalWebserverAuth(port_numbers=[8090]) # 브라우저가 열리고 로그인하면 끝!
gauth.SaveCredentialsFile("mycreds.txt")