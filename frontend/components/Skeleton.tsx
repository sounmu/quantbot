"use client";

// 로딩 스켈레톤: 헤어라인 톤 블록 + 좌→우 광택 스윕(shimmer).
// 데이터 콘솔의 절제된 인상을 유지하면서 "텍스트만 뜨던" 로딩을 형태로 교체한다.

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`relative overflow-hidden rounded bg-hair ${className}`}
      aria-hidden="true"
    >
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/70 to-transparent dark:via-white/[0.06]" />
    </div>
  );
}

// 카드형 리스트(ETF 목록/피드/시그널) 로딩 placeholder.
// 티커·이름 라인 + 하단 메트릭 그리드 구조를 그대로 흉내 낸다.
export function CardSkeleton({ metrics = 3 }: { metrics?: number }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="mt-2.5 h-4 w-3/4" />
          <Skeleton className="mt-2 h-3 w-2/5" />
        </div>
        <Skeleton className="h-4 w-14 shrink-0" />
      </div>
      <div
        className="mt-4 grid gap-2 border-t border-hair pt-3"
        style={{ gridTemplateColumns: `repeat(${metrics}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: metrics }).map((_, index) => (
          <div key={index}>
            <Skeleton className="h-2.5 w-10" />
            <Skeleton className="mt-1.5 h-4 w-14" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function CardSkeletonList({ count = 4, metrics = 3 }: { count?: number; metrics?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, index) => (
        <CardSkeleton key={index} metrics={metrics} />
      ))}
    </div>
  );
}

// 차트 영역 로딩 placeholder. 높이를 호출부에서 맞춰 레이아웃 점프를 막는다.
export function ChartSkeleton({ height = 260 }: { height?: number }) {
  return (
    <div className="flex flex-col justify-end" style={{ height }} aria-hidden="true">
      <Skeleton className="h-full w-full" />
    </div>
  );
}
