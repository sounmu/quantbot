import type { Config } from "tailwindcss";

// 토큰은 CSS 변수(RGB 채널)로 정의해 라이트/다크를 .dark 클래스로 스왑한다.
// rgb(var(--x) / <alpha-value>) 형태라 기존 /opacity 유틸리티(bg-rise/10 등)가 그대로 동작한다.
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '"Pretendard Variable"',
          "Pretendard",
          "-apple-system",
          "BlinkMacSystemFont",
          "system-ui",
          '"Apple SD Gothic Neo"',
          '"Noto Sans KR"',
          "sans-serif"
        ]
      },
      colors: {
        // 텍스트 위계: ink(제목/수치) → body(본문) → muted(보조 라벨) → faint(가장 옅음)
        ink: token("ink"),
        body: token("body"),
        muted: token("muted"),
        faint: token("faint"),
        // 표면은 2단계: canvas(앱 배경) / surface(카드), panel은 인셋 칩
        canvas: token("canvas"),
        surface: token("surface"),
        panel: token("panel"),
        // 헤어라인 구획
        line: token("line"),
        "line-strong": token("line-strong"),
        hair: token("hair"),
        // 브랜드는 절제된 인디고 1색(인터랙티브/링크 전용)
        accent: token("brand"),
        cobalt: token("brand"),
        brand: token("brand"),
        "brand-soft": token("brand-soft"),
        berry: token("berry"),
        // 등락은 의미색만: 상승=빨강 / 하락=파랑, 신규=그린
        rise: token("rise"),
        fall: token("fall"),
        gain: token("gain"),
        lime: token("lime")
      },
      boxShadow: {
        // 데이터 콘솔: 그림자 대신 헤어라인. soft는 거의 보이지 않는 1px 단계
        soft: "0 1px 2px rgba(20, 22, 28, 0.05)",
        frame: "0 1px 40px rgba(20, 22, 28, 0.08)",
        pop: "0 6px 20px rgba(20, 22, 28, 0.10)"
      },
      keyframes: {
        // 스켈레톤 로딩: 좌→우 광택 스윕
        shimmer: {
          "100%": { transform: "translateX(100%)" }
        }
      },
      animation: {
        shimmer: "shimmer 1.6s ease-in-out infinite"
      }
    }
  },
  plugins: []
};

export default config;

