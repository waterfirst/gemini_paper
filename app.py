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
        params = {"applicationNumber": application_number, "ServiceKey": self.api_key}

        try:
            response = self._make_request(endpoint, params)
            return self._parse_detail_response(response)
        except Exception as e:
            st.error(f"상세 정보 조회 중 오류 발생: {str(e)}")
            return {}

    def _make_request(self, endpoint: str, params: Dict) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"API 호출 실패 (상태 코드: {response.status_code})")
        return response

    def _parse_search_response(self, response: requests.Response) -> List[Dict]:
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
                # 필요한 필드만 추출
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

    def _parse_detail_response(self, response: requests.Response) -> Dict:
        try:
            dict_data = xmltodict.parse(response.content)
            item = dict_data.get("response", {}).get("body", {}).get("item", {})
            if item:
                return {
                    "inventionTitle": item.get("inventionTitle", ""),
                    "applicantName": item.get("applicantName", ""),
                    "abstractContent": self._summarize_abstract(
                        item.get("abstractContent", "")
                    ),
                    "applicationDate": item.get("applicationDate", ""),
                    "registerStatus": item.get("registerStatus", ""),
                }
            return {}
        except Exception:
            return {}

    def _summarize_abstract(self, text: str, max_length: int = 100) -> str:
        """특허 요약을 간단하게 요약합니다."""
        if not text:
            return "요약 정보 없음"
        # 첫 문장 추출 (마침표 기준)
        first_sentence = text.split(".")[0]
        if len(first_sentence) > max_length:
            return first_sentence[:max_length] + "..."
        return first_sentence


def display_patent_table(df: pd.DataFrame):
    """특허 검색 결과를 테이블로 표시합니다."""
    # 컬럼 이름 한글화
    column_names = {
        "applicationNumber": "출원번호",
        "inventionTitle": "발명의 명칭",
        "applicationDate": "출원일자",
        "applicantName": "출원인",
        "abstractContent": "요약",
    }

    df = df.rename(columns=column_names)

    # 테이블 스타일링
    st.markdown(
        """
        <style>
        .dataframe {
            font-size: 14px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: none !important;
        }
        .dataframe td {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 300px !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.dataframe(df, hide_index=True)


def main():
    st.set_page_config(page_title="KIPRIS 특허 분석 시스템", layout="wide")

    st.title("KIPRIS 특허 분석 시스템")

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

            st.subheader("검색 결과")
            st.write(f"총 {len(patents)}건의 특허가 검색되었습니다.")

            # 데이터프레임 생성 및 표시
            df = pd.DataFrame(patents)
            display_patent_table(df)

            # CSV 다운로드
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="CSV 다운로드",
                data=csv,
                file_name=f"patent_search_{search_query}.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
