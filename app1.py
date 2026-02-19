import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import xmltodict
from typing import Dict, List, Optional

class KiprisAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://plus.kipris.or.kr/kipo-api/kipi"
        
    def get_patent_detail(self, application_number: str) -> Dict:
        """특허 상세 정보를 조회합니다."""
        endpoint = "/patUtiModInfoSearchSevice/getBibliographyDetailInfoSearch"
        params = {
            "applicationNumber": application_number,
            "ServiceKey": self.api_key
        }
        
        try:
            response = self._make_request(endpoint, params)
            return self._parse_detail_response(response)
        except Exception as e:
            st.error(f"상세 정보 조회 중 오류 발생: {str(e)}")
            return {}

    def get_patent_drawings(self, application_number: str) -> List[Dict]:
        """특허 도면 정보를 조회합니다."""
        endpoint = "/patUtiModInfoSearchSevice/getDrawingInfoSearch"
        params = {
            "applicationNumber": application_number,
            "ServiceKey": self.api_key
        }
        
        try:
            response = self._make_request(endpoint, params)
            return self._parse_drawings_response(response)
        except Exception as e:
            st.error(f"도면 정보 조회 중 오류 발생: {str(e)}")
            return []

    def search_patents(self, search_type: str, search_query: str) -> List[Dict]:
        """특허 검색을 수행합니다."""
        if search_type == "키워드":
            endpoint = "/patUtiModInfoSearchSevice/getWordSearch"
            params = {
                "word": search_query,
                "ServiceKey": self.api_key
            }
        else:
            endpoint = "/patUtiModInfoSearchSevice/getAdvancedSearch"
            params = {
                "inventor": search_query,
                "ServiceKey": self.api_key
            }
            
        try:
            response = self._make_request(endpoint, params)
            return self._parse_search_response(response)
        except Exception as e:
            st.error(f"검색 중 오류 발생: {str(e)}")
            return []

    def _make_request(self, endpoint: str, params: Dict) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            raise Exception(f"API 호출 실패 (상태 코드: {response.status_code})")
            
        return response

    def _parse_search_response(self, response: requests.Response) -> List[Dict]:
        try:
            dict_data = xmltodict.parse(response.content)
            
            if not dict_data or 'response' not in dict_data:
                st.warning("유효하지 않은 응답 형식입니다.")
                return []
                
            body = dict_data['response'].get('body', {})
            if not body:
                st.warning("응답 본문이 비어있습니다.")
                return []
                
            items = body.get('items', {})
            if not items:
                st.warning("검색 결과가 없습니다.")
                return []
                
            if isinstance(items.get('item'), dict):
                return [items['item']]
            elif isinstance(items.get('item'), list):
                return items['item']
            
            return []
            
        except Exception as e:
            st.error(f"응답 파싱 중 오류 발생: {str(e)}")
            return []

    def _parse_detail_response(self, response: requests.Response) -> Dict:
        try:
            dict_data = xmltodict.parse(response.content)
            body = dict_data['response']['body']['item']
            return body if body else {}
        except Exception:
            return {}

    def _parse_drawings_response(self, response: requests.Response) -> List[Dict]:
        try:
            dict_data = xmltodict.parse(response.content)
            items = dict_data['response']['body']['items']['item']
            return items if isinstance(items, list) else [items]
        except Exception:
            return []

def display_patent_detail(client: KiprisAPI, application_number: str):
    """특허 상세 정보를 표시합니다."""
    with st.spinner("상세 정보 로딩 중..."):
        # 상세 정보 조회
        detail = client.get_patent_detail(application_number)
        
        if detail:
            st.subheader("특허 상세 정보")
            
            # 주요 정보 표시
            col1, col2 = st.columns(2)
            with col1:
                st.write("**발명의 명칭**")
                st.write(detail.get('inventionTitle', '정보 없음'))
                st.write("**출원인**")
                st.write(detail.get('applicantName', '정보 없음'))
                st.write("**발명자**")
                st.write(detail.get('inventorName', '정보 없음'))
            
            with col2:
                st.write("**출원번호**")
                st.write(detail.get('applicationNumber', '정보 없음'))
                st.write("**출원일자**")
                st.write(detail.get('applicationDate', '정보 없음'))
                st.write("**법적상태**")
                st.write(detail.get('registerStatus', '정보 없음'))
            
            # 요약 정보
            st.write("**요약**")
            st.write(detail.get('abstractInfo', '요약 정보가 없습니다.'))
            
            # 도면 정보 표시
            st.subheader("대표 도면")
            drawings = client.get_patent_drawings(application_number)
            if drawings:
                cols = st.columns(min(3, len(drawings)))
                for idx, drawing in enumerate(drawings[:3]):  # 최대 3개까지만 표시
                    with cols[idx]:
                        st.image(drawing.get('drawingPath', ''), 
                                caption=f"도면 {idx+1}",
                                use_column_width=True)
            else:
                st.write("도면 정보가 없습니다.")
        else:
            st.warning("상세 정보를 불러올 수 없습니다.")

def format_patent_link(application_number: str) -> str:
    """특허 번호를 클릭 가능한 링크로 변환합니다."""
    return f'<a href="#" onclick="handlePatentClick(\'{application_number}\')">{application_number}</a>'

def main():
    st.set_page_config(page_title="KIPRIS 특허 분석 시스템", layout="wide")
    
    # JavaScript 함수 추가
    st.markdown("""
    <script>
    function handlePatentClick(applicationNumber) {
        // Streamlit에 클릭 이벤트 전달
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: applicationNumber
        }, '*');
    }
    </script>
    """, unsafe_allow_html=True)
    
    st.title("KIPRIS 특허 분석 시스템")
    
    # 세션 상태 초기화
    if 'selected_patent' not in st.session_state:
        st.session_state.selected_patent = None
    
    with st.sidebar:
        st.header("검색 설정")
        api_key = st.text_input("KIPRIS API 키를 입력하세요", type="password")
        search_type = st.selectbox("검색 유형", ["키워드", "발명자"])
        search_query = st.text_input(f"{search_type}를 입력하세요")
    
    if not api_key:
        st.warning("API 키를 입력해주세요.")
        return
        
    client = KiprisAPI(api_key)
    
    if st.sidebar.button("검색") and search_query:
        with st.spinner("검색 중..."):
            patents = client.search_patents(search_type, search_query)
            
            if not patents:
                st.warning("검색 결과가 없습니다.")
                return
            
            # 검색 결과를 데이터프레임으로 변환
            df = pd.DataFrame(patents)
            
            # 결과 표시
            st.subheader("검색 결과")
            st.write(f"총 {len(patents)}건의 특허가 검색되었습니다.")
            
            # 특허 번호를 클릭 가능한 링크로 변환
            if 'applicationNumber' in df.columns:
                df['applicationNumber'] = df['applicationNumber'].apply(format_patent_link)
                
            # 데이터프레임 표시
            st.write(df.to_html(escape=False), unsafe_allow_html=True)
            
            # CSV 다운로드 버튼
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="CSV 다운로드",
                data=csv,
                file_name=f"patent_search_{search_query}.csv",
                mime="text/csv"
            )
    
    # 특허 상세 정보 표시
    if st.session_state.selected_patent:
        display_patent_detail(client, st.session_state.selected_patent)

if __name__ == "__main__":
    main()