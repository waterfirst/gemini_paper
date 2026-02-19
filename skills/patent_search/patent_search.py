"""
KIPRIS 공개특허 검색 스킬
- 출원인명 + 공개일 기준 검색
- IPC 코드 기반 기술 분류
- Spike 감지 결과 JSON 출력
"""

import sys
import json
import os
import time
import re
import requests
import xmltodict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

KIPRIS_API_KEY  = os.getenv("KIPRIS_API_KEY", "qIq7ZsqpirwelaLXJZmwe=yjRgV0AbM=Oapp9CI=f6g=")
KIPRIS_BASE_URL = "http://plus.kipris.or.kr/kipo-api/kipi"

TECH_KEYWORDS = {
    "HBM/고대역폭메모리": ["HBM", "High Bandwidth Memory", "고대역폭"],
    "Hybrid Bonding":     ["Hybrid Bonding", "하이브리드 본딩", "직접접합"],
    "GAA 트랜지스터":     ["GAA", "Gate-All-Around", "나노시트", "Nanosheet"],
    "EUV 리소그래피":     ["EUV", "극자외선", "High-NA"],
    "TSV/3D 패키징":      ["TSV", "실리콘관통전극", "Through Silicon Via", "3D 패키징"],
    "Advanced Packaging": ["칩렛", "Chiplet", "UCIe", "CoWoS", "팬아웃"],
    "OLED/마이크로LED":   ["OLED", "유기발광", "MicroLED", "마이크로LED"],
    "AI 가속기":          ["NPU", "AI 가속", "뉴로모픽", "neuromorphic", "PIM"],
}

IPC_LEVEL2_MAP = {
    "H01L21": "반도체 제조공정(전공정)",
    "H01L25": "패키징/어셈블리(후공정)",
    "H01L27": "집적회로 설계",
    "H01L29": "트랜지스터 구조",
    "H01L33": "LED/마이크로LED",
    "H01L51": "OLED 소자",
    "G03F":   "포토리소그래피",
    "G09G":   "디스플레이 구동",
    "H04N":   "이미지센서",
}


def search_kipris_patents(
    query: str,
    start_date: str,
    end_date: str,
    max_pages: int = 5,
    api_key: str = KIPRIS_API_KEY,
) -> List[Dict]:
    """
    KIPRIS에서 공개(Publication) 특허를 검색합니다.
    openStartDate ~ openEndDate 기간 내 공개된 특허만 반환합니다.
    """
    endpoint = "/patUtiModInfoSearchSevice/getWordSearch"
    session  = requests.Session()
    results: List[Dict] = []

    for page in range(1, max_pages + 1):
        params = {
            "word":          query,
            "ServiceKey":    api_key,
            "numOfRows":     "100",
            "pageNo":        str(page),
            "patent":        "Y",
            "utility":       "N",
            "openStartDate": start_date,
            "openEndDate":   end_date,
        }
        try:
            resp = session.get(KIPRIS_BASE_URL + endpoint, params=params, timeout=15)
            if resp.status_code != 200:
                print(f"[WARN] HTTP {resp.status_code} (페이지 {page})", file=sys.stderr)
                break

            d     = xmltodict.parse(resp.content)
            body  = d.get("response", {}).get("body", {})
            total = int(body.get("totalCount", 0))
            if total == 0:
                break

            raw = body.get("items", {}).get("patentUtilityInfo", [])
            if isinstance(raw, dict):
                raw = [raw]

            page_items = []
            for item in raw:
                open_date = item.get("openDate", "") or ""
                if not open_date:     # 공개일 없는 항목 제외 (출원/등록 상태)
                    continue
                page_items.append({
                    "applicationNumber": item.get("applicationNumber", ""),
                    "inventionTitle":    item.get("inventionTitle", ""),
                    "applicantName":     item.get("applicantName", ""),
                    "openDate":          open_date,
                    "applicationDate":   item.get("applicationDate", ""),
                    "ipcNumber":         item.get("ipcNumber", "") or "",
                    "registerStatus":    item.get("registerStatus", ""),
                    "abstract":          item.get("abstractContent", "") or "",
                })

            results.extend(page_items)
            print(f"[INFO] '{query}' 페이지 {page}: {len(page_items)}건", file=sys.stderr)

            if len(page_items) < 100:
                break
            time.sleep(0.3)

        except Exception as exc:
            print(f"[ERROR] 페이지 {page}: {exc}", file=sys.stderr)
            break

    return results


def classify_tech(title: str, abstract: str) -> str:
    """제목/초록 키워드 기반 기술 카테고리 분류"""
    text = (title + " " + abstract).lower()
    for cat, keywords in TECH_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                return cat
    return "기타"


def classify_ipc(ipc_str: str) -> Dict[str, str]:
    """IPC 코드 → level1(서브클래스) / level2(기술영역) 반환"""
    ipc = (ipc_str or "").strip().upper().split(";")[0].strip()
    level2 = "기타"
    for code, label in IPC_LEVEL2_MAP.items():
        if ipc.startswith(code):
            level2 = label
            break
    m      = re.match(r"([A-Z]\d+[A-Z]+)", ipc)
    level1 = m.group(1) if m else "기타"
    return {"ipc_code": ipc, "level1": level1, "level2": level2}


def detect_spikes(patents: List[Dict], threshold_pct: float = 200.0) -> List[Dict]:
    """
    최근 1개월 공개 건수 vs 이전 11개월 월평균 비교.
    threshold_pct 초과 → 'Strategic Spike' (Green Light #00FF00)
    150% 이상         → 'Emerging Signal'
    """
    now        = datetime.now()
    cutoff_1m  = now - relativedelta(months=1)
    cutoff_12m = now - relativedelta(months=12)

    tech_dates: Dict[str, list] = {k: [] for k in TECH_KEYWORDS}

    for p in patents:
        try:
            od = datetime.strptime(str(p["openDate"])[:8], "%Y%m%d")
        except Exception:
            continue
        if od < cutoff_12m:
            continue
        cat = classify_tech(p["inventionTitle"], p["abstract"])
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
            signal = "Strategic Spike"
            color  = "#00FF00"
            blink  = True
        elif ratio >= 150:
            signal = "Emerging Signal"
            color  = "#FFA500"
            blink  = False
        else:
            signal = "Normal"
            color  = "#AAAAAA"
            blink  = False

        alerts.append({
            "tech_category":   tech,
            "count_1m":        count_1m,
            "avg_11m":         round(avg_11m, 1),
            "spike_ratio_pct": round(ratio, 1),
            "signal":          signal,
            "signal_color":    color,
            "blink":           blink,
        })

    alerts.sort(key=lambda x: x["spike_ratio_pct"], reverse=True)
    return alerts


def run_analysis(
    companies: List[Dict],
    period_months: int = 12,
    spike_threshold: float = 200.0,
) -> Dict:
    """기업 목록에 대해 KIPRIS 검색 + Spike 분석 수행 후 결과 반환"""
    end_dt    = datetime.now()
    start_dt  = end_dt - relativedelta(months=period_months)
    start_str = start_dt.strftime("%Y%m%d")
    end_str   = end_dt.strftime("%Y%m%d")

    output: Dict = {
        "generated_at":    datetime.now().isoformat(),
        "period_months":   period_months,
        "spike_threshold": spike_threshold,
        "companies":       {},
    }

    for co in companies:
        name  = co["name"]
        query = co.get("query", name)
        print(f"\n[INFO] {name} 수집 시작...", file=sys.stderr)

        patents = search_kipris_patents(query, start_str, end_str)
        spikes  = detect_spikes(patents, spike_threshold)

        ipc_dist:  Dict[str, int] = {}
        tech_dist: Dict[str, int] = {}
        for p in patents:
            l2  = classify_ipc(p["ipcNumber"])["level2"]
            ipc_dist[l2] = ipc_dist.get(l2, 0) + 1
            cat = classify_tech(p["inventionTitle"], p["abstract"])
            tech_dist[cat] = tech_dist.get(cat, 0) + 1

        output["companies"][name] = {
            "total_patents":     len(patents),
            "ipc_distribution":  ipc_dist,
            "tech_distribution": tech_dist,
            "spikes":            spikes,
            "sample_patents":    patents[:5],
        }
        spike_cnt = sum(1 for s in spikes if s["signal"] == "Strategic Spike")
        print(f"[INFO] {name}: {len(patents)}건, Spike {spike_cnt}개", file=sys.stderr)

    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="KIPRIS 공개특허 분석 스킬")
    parser.add_argument("--companies", nargs="+", default=["삼성전자", "SK하이닉스"],
                        help="분석할 기업명 목록")
    parser.add_argument("--period",    type=int,   default=12,   help="분석 기간(개월)")
    parser.add_argument("--threshold", type=float, default=200.0, help="Spike 임계값(%)")
    parser.add_argument("--output",    type=str,   default="-",   help="결과 파일 (- = stdout)")
    args = parser.parse_args()

    companies = [{"name": c, "query": c} for c in args.companies]
    result    = run_analysis(companies, args.period, args.threshold)

    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output == "-":
        print(json_str)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"[INFO] 저장 완료: {args.output}", file=sys.stderr)
