"use client";

import { AppShell } from "@/components/AppShell";
import { ChangeFeed } from "@/components/ChangeFeed";
import { useRecentChanges } from "@/hooks/useRecentChanges";

export default function ChangesPage() {
  const recentChanges = useRecentChanges(200);

  return (
    <AppShell>
      <div className="mb-5">
        <h1 className="text-2xl font-bold leading-tight tracking-tight text-ink">최근 매매 내역</h1>
        <p className="mt-2 text-sm leading-snug text-muted">
          추적 중인 ETF 전체에서 주식수 변화로 판정한 신규, 청산, 증가, 감소 내역입니다.
        </p>
      </div>

      <ChangeFeed
        changes={recentChanges.data ?? []}
        isLoading={recentChanges.isLoading}
        errorMessage={recentChanges.isError ? "최근 매매 데이터를 불러오지 못했습니다." : undefined}
        showEtf
      />

      <p className="mt-6 text-xs text-muted">
        ETF 설정/환매로 주식수가 함께 변할 수 있으므로 비중 변화도 함께 확인하세요. 투자자문이 아닙니다.
      </p>
    </AppShell>
  );
}
