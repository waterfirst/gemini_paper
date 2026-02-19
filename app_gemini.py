import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime
import requests
import xmltodict
from typing import Dict, List, Optional
import os

# Streamlit 페이지 설정
st.set_page_config(page_title="KIPRIS 특허 분석 시스템", layout="wide")

# secrets.toml에서 API 키 로드
try:
    KIPRIS_API_KEY = st.secrets["KIPRIS_API_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error("secrets.toml 파일에서 API 키를 로드할 수 없습니다.")
    KIPRIS_API_KEY = None
    GEMINI_API_KEY = None

class KiprisAPI:
    def __init__(self, api_key: str):
        """KIPRIS API 클라이언트를 초기화합니다."""
        self.api_key = api_key
        self.base_url = "http://plus.kipris.or.kr/kipo-api/kipi"
        
    def search_patents(self, search_type: str, search_query: str) -> List[Dict]:
        """특허 검색을 수행합니다."""
        if search_type == "키워드":
            endpoint = "/patUtiModInfoSearchSevice/getWordSearch"
            params = {"word": search_query, "ServiceKey": self.api_key}
        else:
            endpoint = "/patUtiModInfoSearchSevice/getAdvancedSearch"
            params = {"inventor": search_query, "ServiceKey": self.api_key}
            
        try:
            response = self._make_request(endpoint, params)
            return self._parse_search_response(response)
        except Exception as e:
            st.error(f"검색 중 오류 발생: {str(e)}")
            return []

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

    def _make_request(self, endpoint: str, params: Dict) -> requests.Response:
        """API 요청을 수행합니다."""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"API 호출 실패 (상태 코드: {response.status_code})")
        return response

    def _parse_search_response(self, response: requests.Response) -> List[Dict]:
        """검색 결과를 파싱합니다."""
        try:
            dict_data = xmltodict.parse(response.content)
            items = dict_data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if items:
                if isinstance(items, dict):
                    items = [items]
                return [{
                    'applicationNumber': item.get('applicationNumber', ''),
                    'inventionTitle': item.get('inventionTitle', ''),
                    'applicationDate': item.get('applicationDate', ''),
                    'applicantName': item.get('applicantName', ''),
                    'abstractContent': self._summarize_abstract(item.get('abstractContent', ''))
                } for item in items]
            return []
        except Exception as e:
            st.error(f"응답 파싱 중 오류 발생: {str(e)}")
            return []

    def _parse_detail_response(self, response: requests.Response) -> Dict:
        """상세 정보를 파싱합니다."""
        try:
            dict_data = xmltodict.parse(response.content)
            item = dict_data.get('response', {}).get('body', {}).get('item', {})
            if item:
                return {
                    'inventionTitle': item.get('inventionTitle', ''),
                    'applicantName': item.get('applicantName', ''),
                    'abstractContent': self._summarize_abstract(item.get('abstractContent', '')),
                    'applicationDate': item.get('applicationDate', ''),
                    'registerStatus': item.get('registerStatus', '')
                }
            return {}
        except Exception:
            return {}

    def _summarize_abstract(self, text: str, max_length: int = 100) -> str:
        """특허 요약을 간단하게 요약합니다."""
        if not text:
            return "요약 정보 없음"
        first_sentence = text.split('.')[0]
        if len(first_sentence) > max_length:
            return first_sentence[:max_length] + "..."
        return first_sentence

@st.cache_data
def analyze_patents_with_gemini(patents: List[Dict], api_key: str) -> str:
    """Gemini API를 사용하여 특허 데이터를 분석합니다."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    # 분석을 위한 특허 데이터 준비
    patent_summaries = "\n".join([
        f"제목: {p['inventionTitle']}\n요약: {p['abstractContent']}\n출원인: {p['applicantName']}\n"
        for p in patents[:5]  # 처음 5개 특허만 분석
    ])
    
    prompt = f"""
    다음 특허 데이터를 분석하여 주요 트렌드와 인사이트를 도출해주세요:
    
    {patent_summaries}
    
    다음 항목들을 포함해 분석해주세요:
    1. 주요 기술 분야 및 트렌드
    2. 주요 출원인 분석
    3. 기술적 특징 및 혁신 포인트
    4. 향후 발전 방향
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Gemini API 분석 중 오류 발생: {str(e)}")
        return "분석 실패"

@st.cache_data
def create_trend_visualizations(df: pd.DataFrame) -> Dict:
    """특허 데이터 시각화를 생성합니다."""
    # 연도별 출원 동향
    df['year'] = pd.to_datetime(df['applicationDate']).dt.year
    yearly_patents = df.groupby('year').size().reset_index(name='count')
    
    fig_yearly = px.line(yearly_patents, x='year', y='count',
                        title='연도별 특허 출원 동향',
                        labels={'year': '출원연도', 'count': '특허 수'})
    
    # 출원인별 특허 수
    top_applicants = df['applicantName'].value_counts().head(10)
    fig_applicants = px.bar(x=top_applicants.index, y=top_applicants.values,
                           title='상위 10개 출원인별 특허 수',
                           labels={'x': '출원인', 'y': '특허 수'})
    
    return {
        'yearly_trend': fig_yearly,
        'applicant_distribution': fig_applicants
    }

def display_analysis_report(analysis_result: str, visualizations: Dict):
    """분석 보고서를 표시합니다."""
    st.subheader("특허 분석 보고서")
    
    # Gemini 분석 결과 표시
    st.markdown("### AI 분석 결과")
    st.write(analysis_result)
    
    # 시각화 표시
    st.markdown("### 데이터 시각화")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(visualizations['yearly_trend'], use_container_width=True)
    with col2:
        st.plotly_chart(visualizations['applicant_distribution'], use_container_width=True)

def main():
    st.title("KIPRIS 특허 분석 시스템")
    
    # API 키 확인
    if not KIPRIS_API_KEY or not GEMINI_API_KEY:
        st.error("API 키가 설정되지 않았습니다. secrets.toml 파일을 확인해주세요.")
        st.info("""
        secrets.toml 파일을 다음과 같이 설정해주세요:
        ```toml
        KIPRIS_API_KEY = "your_kipris_api_key"
        GEMINI_API_KEY = "your_gemini_api_key"
        ```
        """)
        return
    
    with st.sidebar:
        st.header("검색 설정")
        search_type = st.selectbox("검색 유형", ["키워드", "발명자"])
        search_query = st.text_input(f"{search_type}를 입력하세요")
    
    if st.sidebar.button("검색 및 분석") and search_query:
        client = KiprisAPI(KIPRIS_API_KEY)
        
        with st.spinner("특허 검색 및 분석 중..."):
            patents = client.search_patents(search_type, search_query)
            
            if not patents:
                st.warning("검색 결과가 없습니다.")
                return
            
            df = pd.DataFrame(patents)
            
            st.subheader("기본 검색 결과")
            st.write(f"총 {len(patents)}건의 특허가 검색되었습니다.")
            
            # 데이터프레임 표시 설정
            st.dataframe(
                df,
                column_config={
                    "applicationNumber": "출원번호",
                    "inventionTitle": "발명의 명칭",
                    "applicationDate": "출원일자",
                    "applicantName": "출원인",
                    "abstractContent": "요약"
                },
                hide_index=True
            )
            
            # Gemini 분석 수행
            analysis_result = analyze_patents_with_gemini(patents, GEMINI_API_KEY)
            
            # 시각화 생성
            visualizations = create_trend_visualizations(df)
            
            # 분석 보고서 표시
            display_analysis_report(analysis_result, visualizations)
            
            # CSV 다운로드
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="CSV 다운로드",
                data=csv,
                file_name=f"patent_analysis_{search_query}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()