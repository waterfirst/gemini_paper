import requests
import xmltodict

# REST API 호출 URL 입력(입력 파라미터, KEY값 포함)
url1 = "http://plus.kipris.or.kr" \
       "/kipo-api/kipi/patUtiModInfoSearchSevice/getBibliographySumryInfoSearch"

applno = "1020050050026"
key = ""

# 입력 파라미터 변수 및 값 설정
url2 = "?applicationNumber=" + applno
url3 = "&ServiceKey="+key

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
# - 값이 없는 경우 두 가지 형태
#  1) 태그가 조회되지 않음 2) 태그정보에 None으로 값 출력
# - body 이하 태그는 KIPRISPlus 웹 페이지의 API 상품 설명 참조 또는 print(dict_type)에서 출력되는 사전정보 참고
body = dict_type['response']['body']['items']['item']
print(body)

dictKey = body.keys()

# 2) 값이 None으로 출력되는 경우 아래 프로세스에서 제거
print('\n\n## API 호출 파싱 결과 출력 ##\n')
for i in dictKey:
       dictValue = str(body[i]) if body[i] is not None else ''
       print(i + str('\t:\t') + dictValue)




