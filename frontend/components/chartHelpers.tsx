"use client";

// recharts 차트 공통 비주얼 헬퍼.
// - 마지막 데이터 포인트에만 "글로우 점"을 찍어 현재값 위치를 강조한다(Robinhood/Phantom 패턴).
// - area fill용 linearGradient는 각 차트의 <defs>에서 이 id 규약으로 선언한다.

type EndDotProps = {
  cx?: number;
  cy?: number;
  index?: number;
};

// total 길이를 클로저로 받아 마지막 index에서만 글로우 점을 렌더한다.
// recharts dot prop은 (props) => ReactElement 형태를 허용한다.
export function makeEndDot(total: number, color: string) {
  function EndDot({ cx, cy, index }: EndDotProps) {
    // recharts는 dot을 배열로 렌더하므로 각 항목에 key가 필요하다.
    const key = `end-dot-${index ?? "x"}`;
    if (cx == null || cy == null || index !== total - 1) {
      return <g key={key} />;
    }
    return (
      <g key={key}>
        <circle cx={cx} cy={cy} r={7} fill={color} opacity={0.16} />
        <circle
          cx={cx}
          cy={cy}
          r={3.5}
          fill={color}
          strokeWidth={1.5}
          style={{ stroke: "rgb(var(--surface))" }}
        />
      </g>
    );
  }
  return EndDot;
}

// area fill 그라데이션 id 규약(차트별 충돌 방지).
export function fillId(name: string) {
  return `fill-${name}`;
}

// <defs>에 꽂는 세로 그라데이션(선 색 → 투명). 면적을 옅게 채워 라인에 무게를 준다.
export function AreaGradient({ id, color }: { id: string; color: string }) {
  return (
    <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={color} stopOpacity={0.18} />
      <stop offset="100%" stopColor={color} stopOpacity={0} />
    </linearGradient>
  );
}
