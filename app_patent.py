import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests
import xmltodict
import google.generativeai as genai
from typing import Dict, List

# 스타일 설정
COLORS = {
    "primary": "#1E88E5",
    "secondary": "#FFC107",
    "background": "#0E1117",
    "text": "#FFFFFF",
    "graph": ["#1E88E5", "#FFC107", "#4CAF50", "#E91E63", "#9C27B0"],
}

# Streamlit 페이지 설정
st.set_page_config(page_title="KIPRIS & Gemini 특허 분석 시스템", layout="wide")

# API 키 로드
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
            items = (
                dict_data.get("response", {})
                .get("body", {})
                .get("items", {})
                .get("item", [])
            )
            if items:
                if isinstance(items, dict):
                    items = [items]
                return [
                    {
                        "applicationNumber": item.get("applicationNumber", ""),
                        "inventionTitle": item.get("inventionTitle", ""),
                        "applicationDate": item.get("applicationDate", ""),
                        "applicantName": item.get("applicantName", ""),
                        "abstractContent": self._summarize_abstract(
                            item.get("abstractContent", "")
                        ),
                    }
                    for item in items
                ]
            return []
        except Exception as e:
            st.error(f"응답 파싱 중 오류 발생: {str(e)}")
            return []

    def _summarize_abstract(self, text: str, max_length: int = 100) -> str:
        """특허 요약을 간단하게 요약합니다."""
        if not text:
            return "요약 정보 없음"
        first_sentence = text.split(".")[0]
        if len(first_sentence) > max_length:
            return first_sentence[:max_length] + "..."
        return first_sentence


@st.cache_data
def analyze_patents_with_gemini(patents: List[Dict], api_key: str) -> str:
    """Gemini API를 사용하여 특허 데이터를 분석합니다."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")

    # 분석을 위한 특허 데이터 준비
    patent_summaries = "\n".join(
        [
            f"제목: {p['inventionTitle']}\n요약: {p['abstractContent']}\n출원인: {p['applicantName']}\n"
            for p in patents[:5]  # 처음 5개 특허만 분석
        ]
    )

    prompt = f"""
    다음 특허 데이터를 분석하여 주요 트렌드와 인사이트를 도출해주세요:
    
    {patent_summaries}
    
    다음 항목들을 포함해 분석해주세요:
    1. 주요 기술 분야 및 트렼드
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
def analyze_patent_trends(df: pd.DataFrame) -> dict:
    """특허 데이터의 트렌드를 분석합니다."""
    # 연도별 출원 동향
    df["year"] = pd.to_datetime(df["applicationDate"]).dt.year
    yearly_patents = df.groupby("year").size().reset_index(name="count")

    # 출원인별 특허 수
    applicant_patents = df["applicantName"].value_counts().reset_index()
    applicant_patents.columns = ["applicant", "count"]

    # 기술 분야 분류
    tech_fields = pd.DataFrame(
        {
            "field": ["AR/VR", "OLED", "디스플레이", "AI/ML", "기타"],
            "count": [
                df["inventionTitle"]
                .str.contains("AR|VR|증강현실|가상현실", case=False)
                .sum(),
                df["inventionTitle"].str.contains("OLED|올레드", case=False).sum(),
                df["inventionTitle"]
                .str.contains("디스플레이|표시|화면", case=False)
                .sum(),
                df["inventionTitle"]
                .str.contains("AI|인공지능|머신러닝|학습", case=False)
                .sum(),
                len(df),
            ],
        }
    )

    return {
        "yearly_trend": yearly_patents,
        "applicant_trend": applicant_patents,
        "tech_fields": tech_fields,
    }


def create_visualizations(analysis_data: dict) -> dict:
    """분석 데이터를 시각화합니다."""
    # 연도별 트렌드 그래프
    fig_yearly = go.Figure()
    fig_yearly.add_trace(
        go.Scatter(
            x=analysis_data["yearly_trend"]["year"],
            y=analysis_data["yearly_trend"]["count"],
            mode="lines+markers",
            line=dict(color=COLORS["primary"], width=3),
            marker=dict(size=8),
        )
    )
    fig_yearly.update_layout(
        title="연도별 특허 출원 동향",
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        font=dict(color=COLORS["text"]),
        xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
    )

    # 출원인별 특허 수 그래프
    fig_applicant = go.Figure()
    fig_applicant.add_trace(
        go.Bar(
            x=analysis_data["applicant_trend"]["applicant"][:10],
            y=analysis_data["applicant_trend"]["count"][:10],
            marker_color=COLORS["secondary"],
        )
    )
    fig_applicant.update_layout(
        title="상위 10개 출원인별 특허 수",
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        font=dict(color=COLORS["text"]),
        xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
    )

    return {"yearly_trend": fig_yearly, "applicant_trend": fig_applicant}


def main():
    st.title("KIPRIS & Gemini 특허 분석 시스템")

    if not KIPRIS_API_KEY or not GEMINI_API_KEY:
        st.error("API 키가 설정되지 않았습니다. secrets.toml 파일을 확인해주세요.")
        st.info(
            """
        secrets.toml 파일을 다음과 같이 설정해주세요:
        ```toml
        KIPRIS_API_KEY = "your_kipris_api_key"
        GEMINI_API_KEY = "your_gemini_api_key"
        ```
        """
        )
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

            # 특허 분석 수행
            analysis_data = analyze_patent_trends(df)
            visuals = create_visualizations(analysis_data)

            # Gemini 분석 수행
            ai_analysis = analyze_patents_with_gemini(patents, GEMINI_API_KEY)

            # 분석 결과 표시
            st.header("특허 분석 결과")

            # AI 분석 결과 표시
            st.subheader("AI 분석 리포트")
            st.write(ai_analysis)

            # 시각화 표시
            st.subheader("데이터 시각화")
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(visuals["yearly_trend"], use_container_width=True)
            with col2:
                st.plotly_chart(visuals["applicant_trend"], use_container_width=True)

            # 데이터 테이블
            st.subheader("특허 목록")
            st.dataframe(
                df,
                column_config={
                    "applicationNumber": "출원번호",
                    "inventionTitle": "발명의 명칭",
                    "applicationDate": "출원일자",
                    "applicantName": "출원인",
                    "abstractContent": "요약",
                },
                hide_index=True,
            )

            # CSV 다운로드
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="CSV 다운로드",
                data=csv,
                file_name=f"patent_analysis_{search_query}.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
