// AI 맞춤 여행 플래너 프론트엔드 로직
document.addEventListener("DOMContentLoaded", () => {
    const tripForm = document.getElementById("trip-form");
    const destinationInput = document.getElementById("destination");
    const startDateInput = document.getElementById("start_date");
    const endDateInput = document.getElementById("end_date");
    const budgetSelect = document.getElementById("budget");
    const companionsSelect = document.getElementById("companions");
    const transportationSelect = document.getElementById("transportation");
    const accommodationSelect = document.getElementById("accommodation");

    const submitBtn = document.getElementById("submit-btn");
    const errorBox = document.getElementById("error-box");
    const loadingCard = document.getElementById("loading-card");
    const resultCard = document.getElementById("result-card");
    const planOutput = document.getElementById("plan-output");
    const copyBtn = document.getElementById("copy-btn");
    const downloadBtn = document.getElementById("download-btn");
    const copyToast = document.getElementById("copy-toast");

    // 생성된 원본 마크다운 텍스트를 보관하는 변수
    let currentRawPlan = "";

    // 1. 에러 메시지 표시 함수
    function showError(message) {
        errorBox.textContent = message;
        errorBox.classList.remove("hidden");
        errorBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // 2. 에러 메시지 숨김 함수
    function hideError() {
        errorBox.textContent = "";
        errorBox.classList.add("hidden");
    }

    // 3. 간단하고 안전한 마크다운 HTML 변환 함수
    function parseMarkdownToHtml(markdown) {
        if (!markdown) return "";

        // HTML 태그 이스케이프 (보안 강화)
        let html = markdown
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // 제목 변환 (#, ##, ###)
        html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
        html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
        html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");

        // 굵은 글씨 (Bold)
        html = html.replace(/\*\*(.*?)\*\*/gim, "<strong>$1</strong>");

        // 인용구 (Blockquote)
        html = html.replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>");

        // 구분선 (---)
        html = html.replace(/^---$/gim, "<hr>");

        // 리스트 항목 (- 또는 *)
        html = html.replace(/^\s*[-*]\s+(.*$)/gim, "<li>$1</li>");

        // 줄바꿈 처리
        html = html.replace(/\n\n+/g, "<br><br>");
        html = html.replace(/\n/g, "<br>");

        return html;
    }

    // 4. 폼 제출 이벤트 처리
    tripForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideError();

        const destination = destinationInput.value.trim();
        const startDate = startDateInput.value.trim();
        const endDate = endDateInput.value.trim();
        const budget = budgetSelect.value;
        const companions = companionsSelect.value;
        const transportation = transportationSelect.value;
        const accommodation = accommodationSelect.value;

        // 선택된 관심사들 수집
        const checkedInterests = Array.from(
            document.querySelectorAll('input[name="interests"]:checked')
        ).map((cb) => cb.value);

        // 프론트엔드 입력값 검증 (Validation)
        if (!destination) {
            showError("여행지를 입력해주세요.");
            destinationInput.focus();
            return;
        }

        if (!startDate || !endDate) {
            showError("여행 시작일과 종료일을 모두 선택해주세요.");
            return;
        }

        const start = new Date(startDate);
        const end = new Date(endDate);
        if (start > end) {
            showError("여행 종료일은 시작일보다 빠를 수 없습니다. 날짜를 확인해주세요.");
            endDateInput.focus();
            return;
        }

        // UI 상태: 로딩 표시 활성화 및 버튼 비활성화
        submitBtn.disabled = true;
        submitBtn.innerHTML = "<span>⏳ 일정을 생성하고 있습니다...</span>";
        loadingCard.classList.remove("hidden");
        resultCard.classList.add("hidden");
        loadingCard.scrollIntoView({ behavior: "smooth" });

        try {
            // 백엔드 /generate 엔드포인트로 비동기 POST 요청
            const response = await fetch("/generate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    destination,
                    start_date: startDate,
                    end_date: endDate,
                    budget,
                    interests: checkedInterests,
                    companions,
                    transportation,
                    accommodation
                })
            });

            const result = await response.json();

            if (!response.ok) {
                // 백엔드에서 반환된 친절한 에러 문구 표시
                throw new Error(result.error || "서버 통신 중 오류가 발생했습니다.");
            }

            // 결과 보관 및 HTML 렌더링
            currentRawPlan = result.plan;
            planOutput.innerHTML = parseMarkdownToHtml(currentRawPlan);

            // 결과 화면 보이기
            resultCard.classList.remove("hidden");
            resultCard.scrollIntoView({ behavior: "smooth" });

        } catch (err) {
            console.error("일정 생성 오류:", err);
            showError(err.message || "여행 일정을 생성하는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.");
        } finally {
            // 로딩 종료 및 버튼 복구
            loadingCard.classList.add("hidden");
            submitBtn.disabled = false;
            submitBtn.innerHTML = "<span>✨ AI 여행 일정 생성하기</span>";
        }
    });

    // 5. 전체 일정 클립보드 복사 기능
    copyBtn.addEventListener("click", async () => {
        if (!currentRawPlan) return;

        try {
            await navigator.clipboard.writeText(currentRawPlan);

            // 복사 성공 토스트 표시 (3초 후 사라짐)
            copyToast.classList.remove("hidden");
            setTimeout(() => {
                copyToast.classList.add("hidden");
            }, 3000);
        } catch (err) {
            // 복사 API 실패 시 대체 처리
            console.error("클립보드 복사 실패:", err);
            showError("클립보드 복사에 실패했습니다. 수동으로 드래그하여 복사해주세요.");
        }
    });

    // 6. Markdown 다운로드 기능 (travel-plan.md)
    downloadBtn.addEventListener("click", () => {
        if (!currentRawPlan) return;

        const blob = new Blob([currentRawPlan], { type: "text/markdown;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "travel-plan.md";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
});
