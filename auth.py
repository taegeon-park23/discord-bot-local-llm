from pydrive2.auth import GoogleAuth

gauth = GoogleAuth()
# 갱신 토큰(Refresh Token)을 확실하게 받기 위한 설정
gauth.settings['get_refresh_token'] = True
gauth.flow_params = {'access_type': 'offline', 'approval_prompt': 'force'}

print("브라우저가 열리면 로그인을 진행해주세요...")
gauth.LocalWebserverAuth(port_numbers=[8090]) 
gauth.SaveCredentialsFile("mycreds.txt")
print("✅ 인증 완료! mycreds.txt 파일이 갱신되었습니다.")
print("이제 봇을 재시작하면 갱신 토큰이 적용됩니다.")