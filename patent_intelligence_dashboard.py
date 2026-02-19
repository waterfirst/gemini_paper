"""
반도체/디스플레이 특허 인텔리전스 대시보드
- KIPRIS 공개특허 데이터 기반 기업별 기술 트렌드 분석
- 트리맵 드릴다운 시각화
- Strategic Spike 감지 (공개 급증 신호)
- 이메일 알림 서비스
- Antigravity 프롬프트 생성
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import xmltodict
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional, Tuple
import json
import time
import re

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="반도체 특허 인텔리전스 대시보드",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# 상수 정의
# ─────────────────────────────────────────────
KIPRIS_API_KEY = "qIq7ZsqpirwelaLXJZmwe=yjRgV0AbM=Oapp9CI=f6g="
KIPRIS_BASE_URL = "http://plus.kipris.or.kr/kipo-api/kipi"

COMPANIES = {
    "삼성전자":         {"name_en": "Samsung Electronics", "query": "삼성전자"},
    "SK하이닉스":       {"name_en": "SK Hynix",            "query": "SK하이닉스"},
    "삼성디스플레이":   {"name_en": "Samsung Display",     "query": "삼성디스플레이"},
    "LG디스플레이":     {"name_en": "LG Display",          "query": "LG디스플레이"},
    "LG전자":           {"name_en": "LG Electronics",      "query": "LG전자"},
    "TSMC":             {"name_en": "TSMC",                "query": "TSMC"},
    "인텔":             {"name_en": "Intel",               "query": "인텔"},
    "마이크론":         {"name_en": "Micron Technology",   "query": "마이크론"},
    "어플라이드머티":   {"name_en": "Applied Materials",   "query": "어플라이드머티어리얼즈"},
    "ASML":             {"name_en": "ASML",                "query": "ASML"},
}

# IPC 섹션 → 기술 분류 매핑
IPC_LEVEL1 = {
    "H01L": "반도체 소자/공정",
    "G03F": "포토리소그래피",
    "G09G": "디스플레이 구동",
    "G02F": "LCD/광학 소자",
    "H04N": "이미지센서",
    "H01M": "에너지저장/배터리",
    "H02M": "전력변환",
    "G06N": "AI/뉴로모픽",
}

IPC_LEVEL2 = {
    "H01L21": "반도체 제조공정 (전공정)",
    "H01L25": "패키징/어셈블리 (후공정)",
    "H01L27": "집적회로 설계",
    "H01L29": "트랜지스터/소자 구조",
    "H01L33": "LED/마이크로LED",
    "H01L51": "OLED 소자",
}

IPC_LEVEL3 = {
    "H01L21/02":   "기판/웨이퍼 처리",
    "H01L21/027":  "노광/포토리소그래피",
    "H01L21/306":  "식각(Etch)",
    "H01L21/3105": "CMP(화학기계연마)",
    "H01L21/44":   "금속배선/연결",
    "H01L21/768":  "다층배선",
    "H01L25/065":  "3D 스택/HBM",
    "H01L25/18":   "Hybrid Bonding",
    "H01L29/66":   "GAA/FinFET 트랜지스터",
    "H01L29/78":   "MOSFET/나노시트",
}

# 기술 키워드 → 카테고리 매핑 (spike 감지용)
TECH_KEYWORDS = {
    "HBM/고대역폭메모리":  ["HBM", "High Bandwidth Memory", "고대역폭", "wide IO"],
    "Hybrid Bonding":      ["Hybrid Bonding", "하이브리드 본딩", "직접접합", "Cu-Cu bonding"],
    "GAA 트랜지스터":      ["GAA", "Gate-All-Around", "나노시트", "Nanosheet", "MBCFET"],
    "EUV 리소그래피":      ["EUV", "극자외선", "High-NA", "euv lithography"],
    "TSV/3D 패키징":       ["TSV", "실리콘관통전극", "Through Silicon Via", "3D 패키징"],
    "Advanced Packaging":  ["칩렛", "Chiplet", "UCIe", "CoWoS", "FOPLP", "팬아웃"],
    "OLED/마이크로LED":    ["OLED", "유기발광", "MicroLED", "마이크로LED", "μLED"],
    "AI 가속기":           ["NPU", "AI 가속", "뉴로모픽", "neuromorphic", "PIM"],
}

PERIOD_MONTHS = {"1개월": 1, "3개월": 3, "6개월": 6, "12개월": 12}
SPIKE_COLORS = {
    "Strategic Spike 🔴": "#FF4B4B",
    "Emerging Signal 🟡": "#FFA500",
    "Normal ⚪":          "#AAAAAA",
}

# ─────────────────────────────────────────────
# KIPRIS API 클라이언트
# ─────────────────────────────────────────────
class KiprisClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = KIPRIS_BASE_URL
        self.session = requests.Session()

    def search_by_applicant(
        self,
        company_query: str,
        start_date: str,
        end_date: str,
        max_pages: int = 5,
    ) -> List[Dict]:
        """출원인명으로 공개 특허 검색 (openStartDate ~ openEndDate 기준)"""
        endpoint = "/patUtiModInfoSearchSevice/getWordSearch"
        all_patents: List[Dict] = []

        for page in range(1, max_pages + 1):
            params = {
                "word":          company_query,
                "ServiceKey":    self.api_key,
                "numOfRows":     "100",
                "pageNo":        str(page),
                "patent":        "Y",
                "utility":       "N",
                "openStartDate": start_date,
                "openEndDate":   end_date,
            }
            try:
                resp = self.session.get(
                    self.base_url + endpoint, params=params, timeout=15
                )
                if resp.status_code != 200:
                    break
                items = self._parse_xml(resp.content)
                if not items:
                    break
                all_patents.extend(items)
                if len(items) < 100:
                    break
                time.sleep(0.3)
            except Exception as e:
                st.warning(f"{company_query} 검색 오류 (페이지 {page}): {e}")
                break

        return all_patents

    def _parse_xml(self, content: bytes) -> List[Dict]:
        try:
            d = xmltodict.parse(content)
            body = d.get("response", {}).get("body", {})
            total = int(body.get("totalCount", 0))
            if total == 0:
                return []
            raw = body.get("items", {}).get("patentUtilityInfo", [])
            if isinstance(raw, dict):
                raw = [raw]
            result = []
            for item in raw:
                open_date = item.get("openDate", "") or ""
                if not open_date:          # 공개일 없으면 제외
                    continue
                result.append({
                    "applicationNumber": item.get("applicationNumber", ""),
                    "inventionTitle":    item.get("inventionTitle", ""),
                    "applicantName":     item.get("applicantName", ""),
                    "openDate":          open_date,
                    "applicationDate":   item.get("applicationDate", ""),
                    "ipcNumber":         item.get("ipcNumber", "") or "",
                    "registerStatus":    item.get("registerStatus", ""),
                    "abstract":          item.get("abstractContent", "") or "",
                })
            return result
        except Exception:
            return []


# ─────────────────────────────────────────────
# 특허 분석기
# ─────────────────────────────────────────────
class PatentAnalyzer:
    @staticmethod
    def bucket_by_period(patents: List[Dict]) -> Dict[str, List[Dict]]:
        """공개일 기준으로 1/3/6/12개월 버킷 분류"""
        now = datetime.now()
        cutoffs = {
            "1개월":  now - relativedelta(months=1),
            "3개월":  now - relativedelta(months=3),
            "6개월":  now - relativedelta(months=6),
            "12개월": now - relativedelta(months=12),
        }
        buckets: Dict[str, List[Dict]] = {k: [] for k in cutoffs}
        for p in patents:
            try:
                od = datetime.strptime(str(p["openDate"])[:8], "%Y%m%d")
            except Exception:
                continue
            for label, cutoff in cutoffs.items():
                if od >= cutoff:
                    buckets[label].append(p)
        return buckets

    @staticmethod
    def classify_ipc(ipc_str: str) -> Tuple[str, str, str]:
        """IPC 코드 → (level1 대분류, level2 중분류, level3 소분류) 반환"""
        ipc = (ipc_str or "").strip().upper().split(";")[0].strip()
        l1 = l2 = l3 = "기타"
        if not ipc:
            return l1, l2, l3

        # Level 1: 서브클래스 (H01L, G03F 등)
        m = re.match(r"([A-Z]\d+[A-Z]+)", ipc)
        sub = m.group(1) if m else ""
        if sub in IPC_LEVEL1:
            l1 = IPC_LEVEL1[sub]
        elif sub:
            l1 = sub

        # Level 2: 메인그룹 (H01L21 등)
        m2 = re.match(r"([A-Z]\d+[A-Z]+\d+)", ipc)
        mg = m2.group(1) if m2 else ""
        if mg in IPC_LEVEL2:
            l2 = IPC_LEVEL2[mg]
        elif mg:
            l2 = mg

        # Level 3: 서브그룹
        for code, label in IPC_LEVEL3.items():
            if ipc.startswith(code.replace("/", "").upper()) or code.upper() in ipc:
                l3 = label
                break

        return l1, l2, l3

    @staticmethod
    def classify_tech_keyword(title: str, abstract: str) -> str:
        """제목/초록 키워드로 기술 카테고리 분류"""
        text = (title + " " + abstract).lower()
        for category, keywords in TECH_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text:
                    return category
        return "기타"

    @staticmethod
    def build_treemap_data(patents: List[Dict], company: str) -> pd.DataFrame:
        """트리맵용 데이터프레임 생성"""
        rows = []
        for p in patents:
            l1, l2, l3 = PatentAnalyzer.classify_ipc(p["ipcNumber"])
            tech = PatentAnalyzer.classify_tech_keyword(
                p["inventionTitle"], p["abstract"]
            )
            rows.append({"company": company, "l1": l1, "l2": l2, "l3": l3, "tech": tech})
        return pd.DataFrame(rows)

    @staticmethod
    def detect_spikes(
        patents: List[Dict], threshold_pct: float = 200.0
    ) -> List[Dict]:
        """
        기술별 최근 1개월 공개 건수 vs 이전 11개월 월평균 비교
        threshold_pct 이상이면 Strategic Spike, 150% 이상이면 Emerging Signal
        """
        now = datetime.now()
        cutoff_1m  = now - relativedelta(months=1)
        cutoff_12m = now - relativedelta(months=12)

        # 기술 카테고리별 날짜 리스트
        tech_dates: Dict[str, List[datetime]] = {k: [] for k in TECH_KEYWORDS}

        for p in patents:
            try:
                od = datetime.strptime(str(p["openDate"])[:8], "%Y%m%d")
            except Exception:
                continue
            if od < cutoff_12m:
                continue
            cat = PatentAnalyzer.classify_tech_keyword(
                p["inventionTitle"], p["abstract"]
            )
            if cat in tech_dates:
                tech_dates[cat].append(od)

        alerts = []
        for tech, dates in tech_dates.items():
            recent   = [d for d in dates if d >= cutoff_1m]
            older    = [d for d in dates if d < cutoff_1m]
            count_1m = len(recent)
            avg_11m  = len(older) / 11.0 if older else 0.0
            ratio    = (count_1m / avg_11m * 100) if avg_11m > 0 else 0.0

            if count_1m == 0:
                continue

            if ratio >= threshold_pct:
                signal = "Strategic Spike 🔴"
            elif ratio >= 150:
                signal = "Emerging Signal 🟡"
            else:
                signal = "Normal ⚪"

            alerts.append({
                "기술 카테고리":    tech,
                "최근 1개월 공개":  count_1m,
                "이전 11개월 월평균": round(avg_11m, 1),
                "급증률(%)":        round(ratio, 1),
                "신호":             signal,
            })

        alerts.sort(key=lambda x: x["급증률(%)"], reverse=True)
        return alerts

    @staticmethod
    def monthly_trend(patents: List[Dict]) -> pd.DataFrame:
        """월별 공개 건수 집계"""
        rows = []
        for p in patents:
            try:
                od = datetime.strptime(str(p["openDate"])[:8], "%Y%m%d")
                rows.append({"year_month": od.strftime("%Y-%m")})
            except Exception:
                continue
        if not rows:
            return pd.DataFrame(columns=["year_month", "count"])
        df = pd.DataFrame(rows)
        return (
            df.groupby("year_month")
            .size()
            .reset_index(name="count")
            .sort_values("year_month")
        )


# ─────────────────────────────────────────────
# 이메일 알림 서비스
# ─────────────────────────────────────────────
class EmailAlertService:
    def __init__(self, smtp_host: str, smtp_port: int, user: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.user      = user
        self.password  = password

    def build_html(
        self,
        company: str,
        period: str,
        spikes: List[Dict],
        total_count: int,
    ) -> str:
        spike_rows = ""
        for s in spikes:
            color = SPIKE_COLORS.get(s["신호"], "#999")
            spike_rows += f"""
            <tr>
              <td style="padding:6px 12px;">{s['기술 카테고리']}</td>
              <td style="padding:6px 12px; text-align:center;">{s['최근 1개월 공개']}</td>
              <td style="padding:6px 12px; text-align:center;">{s['이전 11개월 월평균']}</td>
              <td style="padding:6px 12px; text-align:center; font-weight:bold;">
                {s['급증률(%)']:.0f}%
              </td>
              <td style="padding:6px 12px; color:{color}; font-weight:bold;">{s['신호']}</td>
            </tr>"""

        return f"""
        <html><body style="font-family:Arial,sans-serif; color:#333;">
        <h2 style="color:#1E88E5;">🔬 반도체 특허 인텔리전스 알림</h2>
        <p>기업: <strong>{company}</strong> | 분석기간: <strong>{period}</strong>
           | 총 공개특허: <strong>{total_count}건</strong></p>
        <h3>⚡ Strategic Spike 감지 결과</h3>
        <table border="1" cellspacing="0" style="border-collapse:collapse; width:100%;">
          <thead style="background:#1E88E5; color:white;">
            <tr>
              <th style="padding:8px 12px;">기술 카테고리</th>
              <th style="padding:8px 12px;">최근 1개월</th>
              <th style="padding:8px 12px;">월평균(11개월)</th>
              <th style="padding:8px 12px;">급증률</th>
              <th style="padding:8px 12px;">신호</th>
            </tr>
          </thead>
          <tbody>{spike_rows}</tbody>
        </table>
        <br>
        <p style="font-size:12px; color:#888;">
          본 메일은 KIPRIS 공개특허 데이터 기반 자동 분석 결과입니다.<br>
          생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M")}
        </p>
        </body></html>"""

    def send(self, to_list: List[str], subject: str, html_body: str) -> Tuple[bool, str]:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = self.user
            msg["To"]      = ", ".join(to_list)
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, to_list, msg.as_string())
            return True, "이메일 전송 성공"
        except Exception as e:
            return False, str(e)


# ─────────────────────────────────────────────
# Antigravity 프롬프트 생성기
# ─────────────────────────────────────────────
def build_antigravity_prompts(
    companies: List[str],
    period: str,
    spikes: List[Dict],
) -> str:
    company_str = ", ".join(companies)
    spike_str   = "\n".join(
        [f"  - {s['기술 카테고리']}: 급증률 {s['급증률(%)']:.0f}% ({s['신호']})"
         for s in spikes if "Spike" in s["신호"] or "Signal" in s["신호"]]
    ) or "  - 현재 감지된 급증 없음"

    return f"""
# ──────────────────────────────────────────────
# Antigravity IP_Strategist 실행 프롬프트
# 생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M")}
# ──────────────────────────────────────────────

antigravity execute "
[Role]: 반도체/디스플레이 20년 차 수석 엔지니어 겸 IP 전략가.
[Context]: KIPRIS 공개특허 데이터 분석 결과 기반.
[Target Companies]: {company_str}
[Analysis Period]: 최근 {period}

[Detected Spikes]:
{spike_str}

[Task 1 - Spike 심층 분석]:
  위 급증 기술 카테고리에 대해:
  1. 어떤 세부 공정/구조 특허가 집중 공개되고 있는지 분석하라.
  2. 경쟁사 대비 특허 포트폴리오 강도를 평가하라.
  3. 양산 적용 시점과 공개 타이밍의 전략적 의도를 해석하라.

[Task 2 - Treemap 트렌드 분석]:
  기업별 IPC 트리맵에서:
  1. Level 3 노드 중 최근 집중 배치(Stacking) 중인 세부 기술을 식별하라.
  2. 'Trend Velocity': 어떤 기술의 공개 속도가 가장 빠른지 순위를 매겨라.
  3. 전공정/후공정/설계 각 영역별 전략적 중점 이동을 설명하라.

[Task 3 - 위협도 평가]:
  수석 엔지니어 관점에서:
  1. 현재 공개 특허 중 양산 전환 가능성이 높은 기술 Top 3를 선정하라.
  2. 특허 회피(Design Around) 전략 3가지를 제시하라.
  3. 대표 도면 구조가 기존 표준 대비 구조적으로 차별화된 점을 요약하라.

[Output Format]:
  - 각 분석 결과를 JSON으로 출력하고 Firebase 'dashboard_stats' 컬렉션에 동기화하라.
  - Strategic Spike 항목에는 신호등 색상 'Green(#00FF00)' + 'Blink' 태그를 부여하라.
  - 급증 신호가 있는 기업에 이메일 알림(email_sender 스킬)을 즉시 발송하라.
"

# ──────────────────────────────────────────────
# Firebase 대시보드 업데이트 프롬프트
# ──────────────────────────────────────────────

antigravity run "
[대상 기업]: {company_str}
[시계열 분류]: 공개일 기준 1/3/6/12개월 버킷 생성.
[집중도 분석]: 최근 1개월 공개 건수가 11개월 월평균 대비 200% 초과 시 'Strategic Spike' 태그.
[트리 구조]:
  - Level 1: 전공정 / 후공정 / 설계 / 디스플레이
  - Level 2: 노광 / 식각 / 패키징 / HBM / Hybrid Bonding / GAA 등
  - Level 3: 세부 기술명 (IPC 서브그룹 매핑)
  - Strategic Spike 노드: 초록색(#00FF00) 신호등 + Blink 태그
[Firebase 연동]:
  - 'dashboard_trends' 컬렉션: 트리 JSON 저장
  - 'dashboard_stats' 컬렉션: KPI 지표(총 건수, Spike 수, Velocity) 저장
  - 'patent_alerts' 컬렉션: 신호 발생 이력 저장
"

# ──────────────────────────────────────────────
# 멀티모달 분석 프롬프트 (대표 도면 포함)
# ──────────────────────────────────────────────

antigravity execute "
[Role]: 반도체 공정 전문가 (20년 현장 경험).
[Input]: KIPRIS 공개특허 대표 도면 이미지 + IPC 코드 + 초록.
[Objective]:
  1. 대표 도면에서 기존 표준 공정 대비 구조적 변화를 식별하라.
  2. 핵심 혁신 포인트(예: 적층 수, 접합 방식, 재료 변경)를 수석 엔지니어 관점에서 요약하라.
  3. 기술적 위협도(High/Mid/Low)와 양산 가능성(12개월/24개월/36개월+)을 평가하라.
[Critical Constraint]: 기술적 타당성과 양산 리스크를 반드시 비평(Critique)할 것.
"
"""


# ─────────────────────────────────────────────
# 세션 상태 초기화
# ─────────────────────────────────────────────
def init_session():
    defaults = {
        "patents_cache":  {},   # company → list of patents
        "analysis_done":  False,
        "selected_companies": [],
        "selected_period": "6개월",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
def render_sidebar() -> Tuple[List[str], str, float, Dict]:
    with st.sidebar:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Stockage_de_d%C3%A9chets_radioactifs_%C3%A0_La_Hague.jpg/320px-Stockage_de_d%C3%A9chets_radioactifs_%C3%A0_La_Hague.jpg",
            use_container_width=True,
        ) if False else None
        st.title("🔬 설정")

        st.subheader("기업 선택")
        selected = st.multiselect(
            "분석할 기업을 선택하세요",
            list(COMPANIES.keys()),
            default=["삼성전자", "SK하이닉스"],
        )

        st.subheader("분석 기간")
        period = st.selectbox("공개일 기준 기간", list(PERIOD_MONTHS.keys()), index=2)

        st.subheader("Spike 임계값")
        threshold = st.slider(
            "Strategic Spike 판정 기준 (%)",
            min_value=100,
            max_value=500,
            value=200,
            step=50,
        )

        st.subheader("이메일 알림 설정")
        email_cfg = {
            "smtp_host":  st.text_input("SMTP 서버", value="smtp.gmail.com"),
            "smtp_port":  int(st.text_input("SMTP 포트", value="587")),
            "user":       st.text_input("발신 이메일"),
            "password":   st.text_input("앱 비밀번호", type="password"),
            "recipients": st.text_input("수신자 (쉼표 구분)"),
        }

        run_btn = st.button("🚀 분석 실행", type="primary", use_container_width=True)

    return selected, period, threshold, email_cfg, run_btn


# ─────────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_patents(company_query: str, start_date: str, end_date: str) -> List[Dict]:
    client = KiprisClient(KIPRIS_API_KEY)
    return client.search_by_applicant(company_query, start_date, end_date, max_pages=5)


# ─────────────────────────────────────────────
# Tab 1: 대시보드 개요
# ─────────────────────────────────────────────
def tab_overview(all_patents: Dict[str, List[Dict]], period: str):
    st.subheader("📊 대시보드 개요")

    # KPI 카드
    total = sum(len(v) for v in all_patents.values())
    spiky = sum(
        1 for v in all_patents.values()
        for s in PatentAnalyzer.detect_spikes(v)
        if "Spike" in s["신호"]
    )
    top_company = max(all_patents, key=lambda k: len(all_patents[k])) if all_patents else "-"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 공개 특허 (기간 내)", f"{total:,}건")
    c2.metric("Strategic Spike 기술 수", f"{spiky}개")
    c3.metric("최다 공개 기업", top_company)
    c4.metric("분석 기간", period)

    st.divider()

    # 기업별 공개 건수 비교 바 차트
    company_counts = {k: len(v) for k, v in all_patents.items()}
    if company_counts:
        fig_bar = px.bar(
            x=list(company_counts.keys()),
            y=list(company_counts.values()),
            labels={"x": "기업", "y": "공개 특허 수"},
            title=f"기업별 공개 특허 수 ({period})",
            color=list(company_counts.values()),
            color_continuous_scale="Blues",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # 기업별 월별 트렌드
    st.subheader("월별 공개 트렌드")
    trend_frames = []
    for company, patents in all_patents.items():
        df = PatentAnalyzer.monthly_trend(patents)
        df["company"] = company
        trend_frames.append(df)

    if trend_frames:
        df_all = pd.concat(trend_frames, ignore_index=True)
        fig_line = px.line(
            df_all,
            x="year_month", y="count",
            color="company",
            markers=True,
            title="기업별 월별 공개 특허 추이",
            labels={"year_month": "년월", "count": "공개 건수"},
        )
        fig_line.update_xaxes(tickangle=45)
        st.plotly_chart(fig_line, use_container_width=True)


# ─────────────────────────────────────────────
# Tab 2: 트리맵 드릴다운
# ─────────────────────────────────────────────
def tab_treemap(all_patents: Dict[str, List[Dict]]):
    st.subheader("🌳 IPC 기술 트리맵 드릴다운")

    # 기업 선택 (단일)
    company = st.selectbox("기업 선택", list(all_patents.keys()))
    patents = all_patents[company]

    if not patents:
        st.warning("해당 기업의 특허 데이터가 없습니다.")
        return

    df = PatentAnalyzer.build_treemap_data(patents, company)
    if df.empty:
        st.warning("분류 가능한 데이터가 없습니다.")
        return

    # ── Level 1/2 트리맵
    st.markdown("#### Level 1–2: 대분류 → 중분류")
    df_l2 = df.groupby(["company", "l1", "l2"]).size().reset_index(name="count")
    fig_tm = px.treemap(
        df_l2,
        path=["company", "l1", "l2"],
        values="count",
        title=f"{company} IPC 기술 분류 트리맵",
        color="count",
        color_continuous_scale="RdYlGn",
    )
    fig_tm.update_traces(textinfo="label+value+percent parent")
    st.plotly_chart(fig_tm, use_container_width=True)

    # ── Level 3 트리맵
    st.markdown("#### Level 2–3: 중분류 → 소분류")
    df_l3 = df.groupby(["l1", "l2", "l3"]).size().reset_index(name="count")
    fig_l3 = px.treemap(
        df_l3,
        path=["l1", "l2", "l3"],
        values="count",
        title=f"{company} IPC 세부 기술 트리맵 (Level 3)",
        color="count",
        color_continuous_scale="Blues",
    )
    fig_l3.update_traces(textinfo="label+value")
    st.plotly_chart(fig_l3, use_container_width=True)

    # ── 기술 키워드 트리맵
    st.markdown("#### 기술 키워드 분류 트리맵")
    df_tech = df.groupby(["l1", "tech"]).size().reset_index(name="count")
    fig_tech = px.treemap(
        df_tech,
        path=["l1", "tech"],
        values="count",
        title=f"{company} 기술 키워드 트리맵",
        color="count",
        color_continuous_scale="Viridis",
    )
    st.plotly_chart(fig_tech, use_container_width=True)

    # 상세 테이블
    with st.expander("📋 IPC 분류별 특허 목록"):
        show_df = pd.DataFrame(patents)[
            ["inventionTitle", "openDate", "ipcNumber", "applicantName"]
        ].rename(columns={
            "inventionTitle": "발명명칭",
            "openDate":       "공개일",
            "ipcNumber":      "IPC",
            "applicantName":  "출원인",
        })
        st.dataframe(show_df, use_container_width=True, height=400)


# ─────────────────────────────────────────────
# Tab 3: Spike 감지 (Green Light Signal)
# ─────────────────────────────────────────────
def tab_spikes(
    all_patents: Dict[str, List[Dict]],
    threshold: float,
    email_cfg: Dict,
):
    st.subheader("⚡ Strategic Spike 감지 — Green Light Signal")

    all_spikes: Dict[str, List[Dict]] = {}
    for company, patents in all_patents.items():
        spikes = PatentAnalyzer.detect_spikes(patents, threshold_pct=threshold)
        all_spikes[company] = spikes

    # 신호등 표시
    for company, spikes in all_spikes.items():
        with st.expander(f"🏢 {company}", expanded=True):
            if not spikes:
                st.info("현재 감지된 Spike 없음")
                continue
            for s in spikes:
                color = SPIKE_COLORS.get(s["신호"], "#AAA")
                badge_bg = color
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1.5, 1.5, 2])
                col1.markdown(f"**{s['기술 카테고리']}**")
                col2.markdown(f"{s['최근 1개월 공개']}건")
                col3.markdown(f"월평균 {s['이전 11개월 월평균']}건")
                col4.markdown(f"**{s['급증률(%)']:.0f}%**")
                col5.markdown(
                    f"<span style='background:{badge_bg};color:white;"
                    f"padding:3px 10px;border-radius:8px;font-weight:bold;'>"
                    f"{s['신호']}</span>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # 전체 비교 히트맵
    st.subheader("기업 × 기술 Spike 히트맵")
    heatmap_rows = []
    for company, spikes in all_spikes.items():
        for s in spikes:
            heatmap_rows.append({
                "기업":       company,
                "기술":       s["기술 카테고리"],
                "급증률(%)":  s["급증률(%)"],
            })
    if heatmap_rows:
        df_hm = pd.DataFrame(heatmap_rows).pivot_table(
            index="기업", columns="기술", values="급증률(%)", fill_value=0
        )
        fig_hm = px.imshow(
            df_hm,
            text_auto=".0f",
            aspect="auto",
            color_continuous_scale="RdYlGn",
            title="기업 × 기술 급증률(%) 히트맵",
            labels={"color": "급증률(%)"},
        )
        st.plotly_chart(fig_hm, use_container_width=True)

    # 이메일 발송
    st.subheader("📧 Spike 알림 이메일 발송")
    selected_company = st.selectbox("보고서 발송 기업", list(all_spikes.keys()))
    if st.button("이메일 발송", type="secondary"):
        cfg = email_cfg
        if not cfg["user"] or not cfg["password"] or not cfg["recipients"]:
            st.error("이메일 설정(발신자/비밀번호/수신자)을 사이드바에서 입력해주세요.")
        else:
            svc = EmailAlertService(
                cfg["smtp_host"], cfg["smtp_port"], cfg["user"], cfg["password"]
            )
            html = svc.build_html(
                company=selected_company,
                period=st.session_state.get("selected_period", ""),
                spikes=all_spikes[selected_company],
                total_count=len(all_patents[selected_company]),
            )
            recipients = [r.strip() for r in cfg["recipients"].split(",") if r.strip()]
            ok, msg = svc.send(
                recipients,
                f"[특허 인텔리전스] {selected_company} Spike 감지 알림",
                html,
            )
            if ok:
                st.success(msg)
            else:
                st.error(f"발송 실패: {msg}")


# ─────────────────────────────────────────────
# Tab 4: 기업별 상세
# ─────────────────────────────────────────────
def tab_company_detail(all_patents: Dict[str, List[Dict]]):
    st.subheader("🏢 기업별 상세 분석")

    company = st.selectbox("기업", list(all_patents.keys()), key="detail_company")
    patents = all_patents[company]

    if not patents:
        st.warning("데이터 없음")
        return

    # 기간별 버킷 건수
    buckets = PatentAnalyzer.bucket_by_period(patents)
    bucket_counts = {k: len(v) for k, v in buckets.items()}
    fig_bucket = px.bar(
        x=list(bucket_counts.keys()),
        y=list(bucket_counts.values()),
        title=f"{company} — 기간별 공개 특허 수",
        labels={"x": "기간", "y": "공개 건수"},
        color=list(bucket_counts.values()),
        color_continuous_scale="Teal",
    )
    st.plotly_chart(fig_bucket, use_container_width=True)

    # 기술 카테고리 도넛 차트
    tech_counts: Dict[str, int] = {}
    for p in patents:
        cat = PatentAnalyzer.classify_tech_keyword(p["inventionTitle"], p["abstract"])
        tech_counts[cat] = tech_counts.get(cat, 0) + 1

    fig_pie = px.pie(
        names=list(tech_counts.keys()),
        values=list(tech_counts.values()),
        title=f"{company} 기술 카테고리 분포",
        hole=0.4,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # IPC 상위 10개
    ipc_counts: Dict[str, int] = {}
    for p in patents:
        ipc = (p["ipcNumber"] or "").split(";")[0].strip()[:7]
        if ipc:
            ipc_counts[ipc] = ipc_counts.get(ipc, 0) + 1
    top_ipc = sorted(ipc_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    if top_ipc:
        fig_ipc = px.bar(
            x=[x[0] for x in top_ipc],
            y=[x[1] for x in top_ipc],
            title=f"{company} 상위 IPC 코드 (Top 10)",
            labels={"x": "IPC", "y": "건수"},
            color=[x[1] for x in top_ipc],
            color_continuous_scale="Oranges",
        )
        st.plotly_chart(fig_ipc, use_container_width=True)

    # 특허 목록 테이블
    with st.expander("📋 전체 특허 목록"):
        df_show = pd.DataFrame(patents)[
            ["inventionTitle", "openDate", "applicationDate",
             "ipcNumber", "applicantName", "registerStatus"]
        ].rename(columns={
            "inventionTitle":  "발명명칭",
            "openDate":        "공개일",
            "applicationDate": "출원일",
            "ipcNumber":       "IPC",
            "applicantName":   "출원인",
            "registerStatus":  "등록상태",
        })
        st.dataframe(df_show, use_container_width=True, height=500)
        csv = df_show.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv, f"{company}_patents.csv", "text/csv")


# ─────────────────────────────────────────────
# Tab 5: Antigravity 프롬프트
# ─────────────────────────────────────────────
def tab_antigravity(
    all_patents: Dict[str, List[Dict]],
    period: str,
    threshold: float,
):
    st.subheader("🔮 Antigravity 실행 프롬프트")
    st.caption("아래 프롬프트를 복사하여 Antigravity 에이전트에 붙여넣으세요.")

    all_spikes_flat: List[Dict] = []
    for patents in all_patents.values():
        all_spikes_flat.extend(
            PatentAnalyzer.detect_spikes(patents, threshold_pct=threshold)
        )

    prompt_text = build_antigravity_prompts(
        list(all_patents.keys()), period, all_spikes_flat
    )
    st.code(prompt_text, language="bash")

    if st.button("클립보드에 복사 (텍스트 영역)"):
        st.text_area("프롬프트 복사용", prompt_text, height=400)

    # Antigravity agent.config 미리보기
    st.divider()
    st.subheader("antigravity_agent.config 미리보기")
    cfg = {
        "name":    "IP_Strategist",
        "persona": "반도체 20년차 수석 엔지니어",
        "version": "2.0",
        "skills":  ["patent_search", "firebase_sync", "email_sender"],
        "analysis_config": {
            "target_companies": list(all_patents.keys()),
            "period":           period,
            "spike_threshold_pct": threshold,
            "signal_colors": {
                "strategic_spike": "#00FF00",
                "emerging_signal": "#FFA500",
                "normal":          "#AAAAAA",
            },
            "firebase_collections": {
                "trends":      "dashboard_trends",
                "stats":       "dashboard_stats",
                "alerts":      "patent_alerts",
            },
        },
        "prompt_templates": {
            "system_role": (
                "당신은 세계 최고의 반도체/디스플레이 공정 전문가로, "
                "20년 현장 경험을 보유한 수석 엔지니어입니다. "
                "특허 데이터에서 기술 동향과 전략적 신호를 포착하는 능력이 탁월합니다."
            ),
            "spike_analysis": (
                "공개일 기준 최근 1개월 건수가 이전 11개월 월평균의 {threshold}%를 초과하면 "
                "'Strategic Spike'로 분류하고 Green Light(#00FF00) 신호를 활성화하라."
            ),
        },
    }
    st.json(cfg)


# ─────────────────────────────────────────────
# Tab 6: Firebase 동기화
# ─────────────────────────────────────────────
def tab_firebase(all_patents: Dict[str, List[Dict]], period: str, threshold: float):
    st.subheader("🔥 Firebase 대시보드 데이터 구조")
    st.caption("실제 Firebase 연동 시 아래 JSON을 'dashboard_trends' 컬렉션에 저장합니다.")

    payload = {
        "generated_at": datetime.now().isoformat(),
        "period":        period,
        "companies": {},
    }
    for company, patents in all_patents.items():
        buckets = PatentAnalyzer.bucket_by_period(patents)
        spikes  = PatentAnalyzer.detect_spikes(patents, threshold_pct=threshold)
        df      = PatentAnalyzer.build_treemap_data(patents, company)

        tech_tree: Dict = {}
        if not df.empty:
            for _, row in df.iterrows():
                l1 = row["l1"]
                l2 = row["l2"]
                l3 = row["l3"]
                tech_tree.setdefault(l1, {}).setdefault(l2, {}).setdefault(l3, 0)
                tech_tree[l1][l2][l3] += 1  # type: ignore

        payload["companies"][company] = {
            "buckets": {k: len(v) for k, v in buckets.items()},
            "spikes":  [
                {**s, "signal_color": "#00FF00" if "Spike" in s["신호"] else "#FFA500"}
                for s in spikes
            ],
            "ipc_tree": tech_tree,
        }

    st.json(payload)

    json_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        "dashboard_trends.json 다운로드",
        json_bytes,
        "dashboard_trends.json",
        "application/json",
    )


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def main():
    init_session()

    st.title("🔬 반도체/디스플레이 특허 인텔리전스 대시보드")
    st.caption(
        "KIPRIS 공개특허 데이터 기반 · 기업별 기술 트렌드 분석 · "
        "Strategic Spike 감지 · Antigravity 연동"
    )

    selected, period, threshold, email_cfg, run_btn = render_sidebar()
    st.session_state["selected_period"]    = period
    st.session_state["selected_companies"] = selected

    if not selected:
        st.info("👈 사이드바에서 분석할 기업을 선택하고 **분석 실행** 버튼을 누르세요.")
        return

    if run_btn:
        months      = PERIOD_MONTHS[period]
        end_dt      = datetime.now()
        start_dt    = end_dt - relativedelta(months=months)
        start_str   = start_dt.strftime("%Y%m%d")
        end_str     = end_dt.strftime("%Y%m%d")

        all_patents: Dict[str, List[Dict]] = {}
        progress = st.progress(0, text="특허 데이터 수집 중...")
        for i, company in enumerate(selected, 1):
            progress.progress(i / len(selected), text=f"{company} 수집 중...")
            q = COMPANIES[company]["query"]
            patents = load_patents(q, start_str, end_str)
            all_patents[company] = patents
            st.toast(f"{company}: {len(patents)}건 수집 완료", icon="✅")
        progress.empty()

        st.session_state["patents_cache"] = all_patents

    all_patents = st.session_state.get("patents_cache", {})

    if not all_patents:
        return

    tabs = st.tabs([
        "📊 대시보드 개요",
        "🌳 트리맵 드릴다운",
        "⚡ Spike 감지",
        "🏢 기업 상세",
        "🔮 Antigravity 프롬프트",
        "🔥 Firebase 구조",
    ])

    with tabs[0]:
        tab_overview(all_patents, period)
    with tabs[1]:
        tab_treemap(all_patents)
    with tabs[2]:
        tab_spikes(all_patents, threshold, email_cfg)
    with tabs[3]:
        tab_company_detail(all_patents)
    with tabs[4]:
        tab_antigravity(all_patents, period, threshold)
    with tabs[5]:
        tab_firebase(all_patents, period, threshold)


if __name__ == "__main__":
    main()
