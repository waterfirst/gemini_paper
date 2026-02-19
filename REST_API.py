import requests
import xmltodict

# url 생성(입력값, KEY값 포함)
url1 = "http://plus.kipris.or.kr" \
       "/openapi/rest/patUtiModInfoSearchSevice/patentIpcInfo"

applno = "1020060118886"
key = ""

url2 = "?applicationNumber=" + applno
url3 = "&accessKey="+key

# REST API 호출
reponse = requests.get(url1+url2+url3)
print(reponse)

# 호출 결과 확인
content = reponse.content
print(content)

# XML 형태를 DICT(딕셔너리) 형태로 변경
dict_type = xmltodict.parse(content)
print(dict_type)

# 결과에서 body 부분만 추출
body = dict_type['response']['body']
print(body)
print("IPC : "+body['items']['patentIpcInfo']['InternationalpatentclassificationNumber'])
print("일자 : "+body['items']['patentIpcInfo']['InternationalpatentclassificationDate'])

