"""
이메일 알림 발송 스킬
- Strategic Spike 감지 시 HTML 형식 이메일 발송
- SMTP(Gmail 등) 지원
- CLI 및 Python 모듈 양방향 사용 가능
"""

import sys
import json
import os
import smtplib
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, List, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 환경변수에서 기본값 로드
DEFAULT_SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
DEFAULT_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
DEFAULT_EMAIL     = os.getenv("ALERT_EMAIL", "")
DEFAULT_PASSWORD  = os.getenv("ALERT_EMAIL_PASSWORD", "")

SPIKE_COLORS = {
    "Strategic Spike": "#00FF00",
    "Emerging Signal":  "#FFA500",
    "Normal":           "#AAAAAA",
}


def build_html_report(
    company: str,
    period: str,
    total_count: int,
    spikes: List[Dict],
    ipc_summary: Dict[str, int] = None,
) -> str:
    """
    Spike 분석 결과를 HTML 이메일 본문으로 변환합니다.

    Parameters
    ----------
    company     : 분석 기업명
    period      : 분석 기간 문자열 (예: '최근 6개월')
    total_count : 총 공개 특허 수
    spikes      : detect_spikes() 반환 리스트
    ipc_summary : IPC 분류별 건수 딕셔너리 (선택)
    """
    spike_only = [s for s in spikes if s.get("signal") in ("Strategic Spike", "Emerging Signal")]

    # Spike 테이블 행
    spike_rows = ""
    for s in spikes:
        sig    = s.get("signal", "Normal")
        color  = SPIKE_COLORS.get(sig, "#AAAAAA")
        blink  = " ★" if s.get("blink") else ""
        spike_rows += f"""
        <tr>
          <td style="padding:7px 14px;">{s.get('tech_category','')}</td>
          <td style="padding:7px 14px;text-align:center;">{s.get('count_1m',0)}건</td>
          <td style="padding:7px 14px;text-align:center;">{s.get('avg_11m',0)}건</td>
          <td style="padding:7px 14px;text-align:center;font-weight:bold;">
            {s.get('spike_ratio_pct',0):.0f}%
          </td>
          <td style="padding:7px 14px;text-align:center;">
            <span style="background:{color};color:{'#000' if sig=='Strategic Spike' else '#fff'};
                         padding:3px 10px;border-radius:6px;font-weight:bold;">
              {sig}{blink}
            </span>
          </td>
        </tr>"""

    # IPC 분포 요약
    ipc_section = ""
    if ipc_summary:
        ipc_rows = "".join(
            f"<tr><td style='padding:4px 12px;'>{k}</td>"
            f"<td style='padding:4px 12px;text-align:right;'>{v}건</td></tr>"
            for k, v in sorted(ipc_summary.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        ipc_section = f"""
        <h3 style="color:#555;margin-top:24px;">📊 IPC 기술 분류 (상위 10개)</h3>
        <table border="1" cellspacing="0"
               style="border-collapse:collapse;width:60%;font-size:13px;">
          <thead style="background:#E3F2FD;">
            <tr>
              <th style="padding:6px 12px;text-align:left;">기술 분류</th>
              <th style="padding:6px 12px;text-align:right;">건수</th>
            </tr>
          </thead>
          <tbody>{ipc_rows}</tbody>
        </table>"""

    # 요약 배너 색상
    has_spike = any(s.get("signal") == "Strategic Spike" for s in spikes)
    banner_color = "#00C853" if has_spike else "#FF8F00"
    banner_text  = "Strategic Spike 감지됨 — 즉시 검토 필요" if has_spike else "Emerging Signal 감지"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8">
<style>
  body {{ font-family: 'Apple SD Gothic Neo', Arial, sans-serif; color: #333; margin: 0; padding: 0; }}
  h2   {{ color: #1565C0; }}
  table {{ font-size: 14px; }}
</style>
</head>
<body style="padding:24px;">
  <div style="max-width:780px;margin:auto;">

    <!-- 헤더 -->
    <div style="background:#1565C0;color:white;padding:18px 24px;border-radius:8px 8px 0 0;">
      <h2 style="color:white;margin:0;">🔬 반도체 특허 인텔리전스 알림</h2>
      <p style="margin:6px 0 0 0;font-size:13px;opacity:.85;">
        KIPRIS 공개특허 데이터 기반 자동 분석 · {datetime.now().strftime("%Y-%m-%d %H:%M")} 생성
      </p>
    </div>

    <!-- 요약 배너 -->
    <div style="background:{banner_color};color:white;padding:12px 24px;font-weight:bold;">
      ⚡ {banner_text}
    </div>

    <!-- 기본 정보 -->
    <div style="background:#F5F5F5;padding:16px 24px;border:1px solid #ddd;">
      <table style="width:100%;border:none;">
        <tr>
          <td><strong>분석 기업</strong></td><td>{company}</td>
          <td><strong>분석 기간</strong></td><td>{period}</td>
          <td><strong>총 공개 특허</strong></td><td><strong>{total_count:,}건</strong></td>
          <td><strong>Spike 감지</strong></td>
          <td><strong style="color:{banner_color};">{len(spike_only)}개</strong></td>
        </tr>
      </table>
    </div>

    <!-- Spike 테이블 -->
    <h3 style="color:#1565C0;margin-top:20px;">⚡ 기술별 Spike 분석</h3>
    <table border="1" cellspacing="0"
           style="border-collapse:collapse;width:100%;font-size:14px;">
      <thead style="background:#1565C0;color:white;">
        <tr>
          <th style="padding:9px 14px;text-align:left;">기술 카테고리</th>
          <th style="padding:9px 14px;">최근 1개월</th>
          <th style="padding:9px 14px;">월평균(11개월)</th>
          <th style="padding:9px 14px;">급증률</th>
          <th style="padding:9px 14px;">신호</th>
        </tr>
      </thead>
      <tbody>{spike_rows}</tbody>
    </table>

    {ipc_section}

    <!-- 안내 -->
    <p style="margin-top:28px;font-size:12px;color:#888;border-top:1px solid #eee;padding-top:12px;">
      본 메일은 KIPRIS 공개특허 데이터를 기반으로 자동 생성되었습니다.<br>
      Strategic Spike 신호(🟢 Green Light)는 최근 1개월 공개 건수가
      이전 11개월 월평균 대비 200% 이상 급증한 기술을 의미합니다.<br>
      <em>Powered by IP_Strategist · Antigravity Agent</em>
    </p>
  </div>
</body>
</html>"""


def send_email(
    recipients: List[str],
    subject: str,
    html_body: str,
    smtp_host: str = DEFAULT_SMTP_HOST,
    smtp_port: int = DEFAULT_SMTP_PORT,
    sender_email: str = DEFAULT_EMAIL,
    sender_password: str = DEFAULT_PASSWORD,
) -> Tuple[bool, str]:
    """
    HTML 이메일을 SMTP로 발송합니다.

    Returns
    -------
    (성공여부: bool, 메시지: str)
    """
    if not sender_email or not sender_password:
        return False, "발신 이메일 또는 비밀번호가 설정되지 않았습니다."
    if not recipients:
        return False, "수신자 목록이 비어 있습니다."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = sender_email
        msg["To"]      = ", ".join(recipients)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())

        return True, f"이메일 전송 성공 ({len(recipients)}명)"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP 인증 실패: 이메일/앱 비밀번호를 확인하세요."
    except smtplib.SMTPConnectError:
        return False, f"SMTP 연결 실패: {smtp_host}:{smtp_port}"
    except Exception as exc:
        return False, str(exc)


def send_spike_alert(
    analysis_result: Dict,
    recipients: List[str],
    smtp_host: str = DEFAULT_SMTP_HOST,
    smtp_port: int = DEFAULT_SMTP_PORT,
    sender_email: str = DEFAULT_EMAIL,
    sender_password: str = DEFAULT_PASSWORD,
) -> Dict[str, Tuple[bool, str]]:
    """
    run_analysis() 결과에서 Spike가 있는 기업에 알림 이메일을 발송합니다.

    Parameters
    ----------
    analysis_result : patent_search.run_analysis() 반환값
    recipients      : 수신자 이메일 목록

    Returns
    -------
    {기업명: (성공여부, 메시지)} 딕셔너리
    """
    results: Dict[str, Tuple[bool, str]] = {}
    period = f"최근 {analysis_result.get('period_months', '?')}개월"

    for company, data in analysis_result.get("companies", {}).items():
        spikes = data.get("spikes", [])
        has_signal = any(
            s.get("signal") in ("Strategic Spike", "Emerging Signal")
            for s in spikes
        )
        if not has_signal:
            results[company] = (False, "Spike 없음 — 발송 생략")
            continue

        html = build_html_report(
            company=company,
            period=period,
            total_count=data.get("total_patents", 0),
            spikes=spikes,
            ipc_summary=data.get("ipc_distribution"),
        )
        subject = (
            f"[특허 인텔리전스] {company} — "
            f"Strategic Spike {sum(1 for s in spikes if s.get('signal')=='Strategic Spike')}개 감지"
        )
        ok, msg = send_email(
            recipients, subject, html,
            smtp_host, smtp_port, sender_email, sender_password,
        )
        results[company] = (ok, msg)
        print(f"[INFO] {company} 이메일: {'성공' if ok else '실패'} — {msg}", file=sys.stderr)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="특허 Spike 알림 이메일 발송 스킬")
    parser.add_argument("--analysis",   required=True,      help="patent_search 결과 JSON 파일 경로")
    parser.add_argument("--recipients", required=True, nargs="+", help="수신자 이메일 목록")
    parser.add_argument("--smtp-host",  default=DEFAULT_SMTP_HOST)
    parser.add_argument("--smtp-port",  default=DEFAULT_SMTP_PORT, type=int)
    parser.add_argument("--sender",     default=DEFAULT_EMAIL,     help="발신 이메일")
    parser.add_argument("--password",   default=DEFAULT_PASSWORD,  help="SMTP 앱 비밀번호")
    args = parser.parse_args()

    try:
        with open(args.analysis, "r", encoding="utf-8") as f:
            analysis = json.load(f)
    except Exception as e:
        print(f"[ERROR] 분석 파일 로드 실패: {e}", file=sys.stderr)
        sys.exit(1)

    results = send_spike_alert(
        analysis_result  = analysis,
        recipients       = args.recipients,
        smtp_host        = args.smtp_host,
        smtp_port        = args.smtp_port,
        sender_email     = args.sender,
        sender_password  = args.password,
    )

    for company, (ok, msg) in results.items():
        status = "✅" if ok else "❌"
        print(f"  {status} {company}: {msg}")
