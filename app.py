import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai

# .env 환경변수 로드
load_dotenv()

# 로깅 설정 (민감 정보는 출력하지 않음)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Flask 앱 초기화
app = Flask(__name__)

# Gemini API 클라이언트 초기화
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
else:
    logger.info("GEMINI_API_KEY가 성공적으로 로드되었습니다.")


@app.route("/")
def index():
    """메인 여행플래너 페이지 렌더링"""
    return render_template("index.html")


@app.route("/sw.js")
def service_worker():
    return app.send_static_file("sw.js")
@app.route("/generate", methods=["POST"])
def generate():
    """사용자 입력을 바탕으로 Gemini AI 여행 일정 생성"""
    try:
        data = request.get_json()
        if not data:
            logger.warning("요청 본문(JSON) 데이터가 없습니다.")
            return jsonify({"error": "여행 정보가 올바르게 전달되지 않았습니다."}), 400

        # 입력 데이터 추출
        destination = data.get("destination", "").strip()
        start_date = data.get("start_date", "").strip()
        end_date = data.get("end_date", "").strip()
        budget = data.get("budget", "").strip()
        interests = data.get("interests", [])
        companions = data.get("companions", "").strip()
        transportation = data.get("transportation", "").strip()
        accommodation = data.get("accommodation", "").strip()

        # 입력값 검증 (Validation)
        if not destination:
            logger.warning("입력 검증 실패: 여행지 미입력")
            return jsonify({"error": "여행지를 입력해주세요."}), 400

        if not start_date or not end_date:
            logger.warning("입력 검증 실패: 여행 기간 미입력")
            return jsonify({"error": "여행 시작일과 종료일을 모두 입력해주세요."}), 400

        try:
            d_start = datetime.strptime(start_date, "%Y-%m-%d")
            d_end = datetime.strptime(end_date, "%Y-%m-%d")
            if d_start > d_end:
                logger.warning(f"입력 검증 실패: 시작일({start_date})이 종료일({end_date})보다 늦음")
                return jsonify({"error": "여행 종료일은 시작일보다 빠를 수 없습니다. 날짜를 확인해주세요."}), 400
            trip_days = (d_end - d_start).days + 1
        except ValueError:
            logger.warning("입력 검증 실패: 날짜 형식 오류")
            return jsonify({"error": "날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)"}), 400

        # 리스트 형식의 관심사 정리
        if isinstance(interests, list):
            interests_str = ", ".join(interests) if interests else "특별한 선호 없음"
        else:
            interests_str = str(interests) if str(interests).strip() else "특별한 선호 없음"

        # 백엔드 요청 로그 기록 (민감정보 제외)
        logger.info(
            f"새로운 여행 일정 생성 요청: 목적지='{destination}', 기간={start_date}~{end_date}({trip_days}일간), "
            f"예산='{budget or '미지정'}', 이동수단='{transportation or '미지정'}'"
        )

        # API Key 존재 확인
        if not GEMINI_API_KEY:
            logger.error("Gemini API 호출 불가: GEMINI_API_KEY 누락")
            return jsonify({"error": "서버에 Gemini API 키가 설정되지 않았습니다. 관리자에게 문의하세요."}), 500

        # Gemini 프롬프트 구성 (정보 정확성 원칙 철저 반영)
        prompt = f"""
당신은 최고의 여행 일정 플래너 AI 전문가입니다.
사용자가 제공한 아래의 여행 조건을 바탕으로, 체계적이고 실용적인 여행 일정을 마크다운(Markdown) 형식으로 작성해주세요.

---
### [사용자 여행 조건]
- 여행지: {destination}
- 여행 기간: {start_date} ~ {end_date} (총 {trip_days}일간)
- 예상 예산: {budget if budget else "적정 수준 권장"}
- 주요 관심사: {interests_str}
- 동행자: {companions if companions else "혼자 여행"}
- 선호 이동수단: {transportation if transportation else "대중교통 또는 추천 이동수단"}
- 숙소 선호 유형: {accommodation if accommodation else "적정 수준 숙소"}

---
### [중요한 정보 정확성 원칙 (반드시 준수)]
1. 실시간으로 변동될 수 있는 정보(현재 운영시간, 현재 휴무일, 현재 입장료, 현재 메뉴 가격, 현재 숙박 요금, 현재 교통 요금, 실시간 교통 상황, 실시간 예약 가능 여부, 현재 영업 여부 등)는 절대 임의로 지어내거나 확정적으로 작성하지 마세요.
2. 실시간 확인이 필요한 항목은 반드시 문구 뒤에 **"확인 필요"**라고 명시하세요.
   (예: 운영시간: 확인 필요, 입장료: 확인 필요, 숙박비: 확인 필요)
3. 금액을 안내할 때는 확정 가격이 아닌 일반적인 참고치임을 나타내도록 반드시 **"예상 비용"**임을 명확히 밝히세요.

---
### [응답에 반드시 포함해야 할 구성 항목]

# 1. 여행 요약
- 여행지의 매력과 이번 일정의 전체적인 테마 요약 (2~3문장)

# 2. 전체 일정
- 일자별 핵심 동선 요약 (예: 1일차 - 도착 및 시내 탐방, 2일차 - 자연 명소 투어 등)

# 3. 날짜별 일정
- 1일차부터 {trip_days}일차까지 각각 상세하게 구분
- 각 일자별로 시간대(오전/오후/저녁), 방문 장소, 추천 활동, 추천 식사(메뉴), 이동 방법을 명확히 분리하여 기술
- 운영시간이나 입장료는 "확인 필요" 명시

# 4. 예상 비용
- 항목별 구분 (모든 금액은 대략적인 예상치임을 명시):
  - 교통비 (예상 비용)
  - 식비 (예상 비용)
  - 숙박비 (예상 비용 / 확인 필요)
  - 입장료/체험비 (예상 비용 / 확인 필요)
  - 기타/비상금 (예상 비용)
  - 총 예상 비용 (예상 비용)
- 실시간 가격 확인이 필요한 부분은 "확인 필요" 병기

# 5. 이동 계획
- 사용자가 선택한 이동수단({transportation if transportation else '권장 이동수단'})을 중심으로 장소 간 이동 방법 안내
- 소요 시간이나 교통 상황은 확정이 아니므로 "예상 소요시간" 또는 "교통상황 확인 필요"로 안내

# 6. 준비물
- 해당 여행지, 계절, 활동에 꼭 필요한 필수 준비물 및 유용한 아이템 목록

# 7. 주의사항
- 안전, 문화/에티켓, 현지 결제 수단, 사전 예약 권장 항목 등 여행자가 반드시 챙겨야 할 주의사항

가독성 높고 친절한 어투로 깔끔한 마크다운 형식으로 작성해주세요.
"""

        # Gemini API 호출 (모델 일시 혼잡(503) 대비 대체 모델 순차 호출)
        logger.info("Gemini API 호출 시작...")
        client = genai.Client(api_key=GEMINI_API_KEY)
        candidate_models = ["gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-3.8-flash"]

        response = None
        last_error = None
        for model_name in candidate_models:
            try:
                logger.info(f"모델 시도: {model_name}")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and response.text:
                    logger.info(f"모델 호출 성공: {model_name}")
                    break
            except Exception as model_err:
                logger.warning(f"모델 '{model_name}' 일시 호출 실패 ({str(model_err)}), 다음 모델로 재시도합니다.")
                last_error = model_err

        if not response or not response.text:
            logger.error(f"모든 Gemini 모델 호출 실패: {str(last_error)}")
            return jsonify({"error": "AI가 여행 일정을 생성하지 못했습니다. 잠시 후 다시 시도해주세요."}), 500

        logger.info("Gemini API 호출 성공 및 여행 일정 생성 완료")
        return jsonify({"plan": response.text})

    except Exception as e:
        logger.error(f"여행 일정 생성 중 예외 발생: {str(e)}", exc_info=True)
        return jsonify({"error": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 500


if __name__ == "__main__":
    # 개발 서버 실행 (포트 5000)
    app.run(host="127.0.0.1", port=5000, debug=True)
