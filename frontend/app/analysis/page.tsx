"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  ChevronRight,
  LineChart,
  Target,
  Users
} from "lucide-react";
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { AppShell } from "@/components/AppShell";
import { CardSkeletonList } from "@/components/Skeleton";
import { useChartPalette } from "@/components/ThemeProvider";
import { useAnalysisPerformance, useSecurityAnalysis } from "@/hooks/useAnalysis";
import { useDailySignals, useSignalSecurityHistory } from "@/hooks/useSignals";
import type {
  HorizonDays,
  PerformanceBucket,
  PerformanceSummary,
  SecurityAnalysisPoint,
  SignalDaily,
  SignalParticipant,
  SignalSecurityHistory
} from "@/lib/types";

const HORIZONS: HorizonDays[] = [1, 5, 20, 60];
const FOCUS_BUCKET: PerformanceBucket = "conviction_2_plus";

const BUCKETS: Array<{ key: PerformanceBucket; label: string; caption: string }> = [
  { key: "all", label: "전체 BUY", caption: "모든 매수 시그널" },
  { key: "conviction_1", label: "1 ETF", caption: "단일 ETF 매수" },
  { key: "conviction_2_plus", label: "2+ ETF", caption: "복수 ETF 동시 매수" },
  { key: "conviction_3_plus", label: "3+ ETF", caption: "강한 군집 매수" }
];

export default function AnalysisPage() {
  const [horizon, setHorizon] = useState<HorizonDays>(20);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const performance = useAnalysisPerformance(horizon);
  const dailySignals = useDailySignals(50);

  const convictionSignals = useMemo(
    () =>
      (dailySignals.data ?? [])
        .filter((signal) => signal.conviction_score > 0)
        .sort((a, b) => {
          if (b.conviction_score !== a.conviction_score) {
            return b.conviction_score - a.conviction_score;
          }
          return (Math.abs(b.net_dollar_flow ?? 0) || b.n_buying) - (Math.abs(a.net_dollar_flow ?? 0) || a.n_buying);
        })
        .slice(0, 12),
    [dailySignals.data]
  );

  useEffect(() => {
    if (selectedKey === null && convictionSignals.length > 0) {
      setSelectedKey(convictionSignals[0].security_key);
    }
  }, [convictionSignals, selectedKey]);

  const selectedSignal =
    convictionSignals.find((signal) => signal.security_key === selectedKey) ?? convictionSignals[0] ?? null;
  const activeSecurityKey = selectedSignal?.security_key ?? selectedKey;
  const signalHistory = useSignalSecurityHistory(activeSecurityKey ?? null, 20);
  const securityAnalysis = useSecurityAnalysis(activeSecurityKey ?? null);

  const summaries = performance.data ?? [];
  const headline =
    summaries.find((summary) => summary.bucket === FOCUS_BUCKET) ??
    summaries.find((summary) => summary.bucket === "all") ??
    null;

  return (
    <AppShell>
      <div className="mb-5">
        <p className="text-xs font-semibold uppercase text-faint">Signal lab</p>
        <h1 className="mt-1 text-2xl font-bold leading-tight text-ink">분석</h1>
        <p className="mt-2 text-sm leading-snug text-muted">
          shares가 늘어난 종목을 T+1 이후 QQQ 대비 초과수익으로 검증합니다.
        </p>
      </div>

      <div className="space-y-5">
        <section className="rounded-xl border border-line bg-surface p-4 shadow-soft" aria-label="시그널 성과 요약">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold text-brand">
                <Target className="h-4 w-4" aria-hidden="true" />
                컨빅션 검증
              </div>
              <h2 className="mt-2 text-lg font-bold leading-snug text-ink">
                {horizon}거래일 뒤, 복수 ETF 매수는 통했나?
              </h2>
            </div>
            <ConfidenceChip sampleSize={headline?.sample_size ?? 0} />
          </div>

          <HorizonToggle value={horizon} onChange={setHorizon} />

          {performance.isError ? (
            <StatusCard tone="error">성과 데이터를 불러오지 못했습니다.</StatusCard>
          ) : performance.isLoading ? (
            <div className="mt-4">
              <CardSkeletonList count={1} metrics={4} />
            </div>
          ) : (
            <HeroMetrics summary={headline} />
          )}
        </section>

        <BucketPerformance
          summaries={summaries}
          isError={performance.isError}
          isLoading={performance.isLoading}
        />

        <section className="space-y-3" aria-label="컨빅션 보드">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold text-brand">
                <Users className="h-4 w-4" aria-hidden="true" />
                오늘의 동시 매수
              </div>
              <h2 className="mt-1 text-lg font-bold text-ink">컨빅션 보드</h2>
            </div>
            {convictionSignals[0]?.as_of_date ? (
              <time className="text-xs font-medium tabular-nums text-faint" dateTime={convictionSignals[0].as_of_date}>
                {convictionSignals[0].as_of_date}
              </time>
            ) : null}
          </div>

          <ConvictionBoard
            signals={convictionSignals}
            selectedKey={activeSecurityKey ?? null}
            isError={dailySignals.isError}
            isLoading={dailySignals.isLoading}
            onSelect={setSelectedKey}
          />
        </section>

        <SecuritySignalPanel
          horizon={horizon}
          selectedSignal={selectedSignal}
          history={signalHistory.data ?? []}
          outcomes={securityAnalysis.data ?? []}
          isLoading={signalHistory.isLoading || securityAnalysis.isLoading}
          isError={signalHistory.isError || securityAnalysis.isError}
        />

        <Disclaimer />
      </div>
    </AppShell>
  );
}

function HeroMetrics({ summary }: { summary: PerformanceSummary | null }) {
  return (
    <div className="mt-4 grid grid-cols-2 gap-2">
      <MetricCard
        label="Hit rate"
        value={formatPercent(summary?.hit_rate ?? null)}
        caption="초과수익 > 0"
        tone={summary?.hit_rate != null && summary.hit_rate >= 0.5 ? "positive" : "neutral"}
      />
      <MetricCard
        label="평균 초과수익"
        value={formatPercent(summary?.average_excess_return ?? null, true)}
        caption="QQQ 대비"
        tone={toneForReturn(summary?.average_excess_return ?? null)}
      />
      <MetricCard label="표본수" value={formatInteger(summary?.sample_size ?? 0)} caption="완료된 forward window" />
      <MetricCard
        label="IC"
        value={formatRatio(summary?.information_coefficient ?? null)}
        caption="시그널 강도와 성과"
        tone={toneForReturn(summary?.information_coefficient ?? null)}
      />
    </div>
  );
}

function HorizonToggle({
  value,
  onChange
}: {
  value: HorizonDays;
  onChange: (value: HorizonDays) => void;
}) {
  return (
    <div className="mt-4 grid grid-cols-4 rounded-lg bg-panel p-1" aria-label="성과 기간 선택">
      {HORIZONS.map((horizon) => (
        <button
          key={horizon}
          type="button"
          onClick={() => onChange(horizon)}
          className={`min-h-10 rounded-md px-2 text-xs font-semibold transition ${
            value === horizon ? "bg-surface text-ink shadow-soft" : "text-muted hover:text-body"
          }`}
          aria-pressed={value === horizon}
        >
          {horizon}D
        </button>
      ))}
    </div>
  );
}

function BucketPerformance({
  summaries,
  isError,
  isLoading
}: {
  summaries: PerformanceSummary[];
  isError: boolean;
  isLoading: boolean;
}) {
  const maxAverage = Math.max(
    0.01,
    ...summaries.map((summary) => Math.abs(summary.average_excess_return ?? 0))
  );

  return (
    <section className="space-y-3" aria-label="버킷별 성과">
      <div className="flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-brand" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-ink">버킷별 검증</h2>
      </div>

      {isError ? (
        <StatusCard tone="error">버킷 성과를 불러오지 못했습니다.</StatusCard>
      ) : isLoading ? (
        <CardSkeletonList count={3} metrics={2} />
      ) : summaries.length === 0 ? (
        <StatusCard>아직 평가된 시그널 표본이 없습니다.</StatusCard>
      ) : (
        <div className="space-y-2">
          {BUCKETS.map((bucket) => {
            const summary = summaries.find((item) => item.bucket === bucket.key) ?? null;
            return (
              <BucketRow
                key={bucket.key}
                bucket={bucket}
                summary={summary}
                maxAverage={maxAverage}
              />
            );
          })}
        </div>
      )}
    </section>
  );
}

function BucketRow({
  bucket,
  summary,
  maxAverage
}: {
  bucket: { key: PerformanceBucket; label: string; caption: string };
  summary: PerformanceSummary | null;
  maxAverage: number;
}) {
  const hitRate = summary?.hit_rate ?? null;
  const average = summary?.average_excess_return ?? null;

  return (
    <article className="rounded-lg border border-line bg-surface p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-semibold text-ink">{bucket.label}</div>
          <p className="mt-0.5 text-xs text-muted">{bucket.caption}</p>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-xs font-semibold tabular-nums text-ink">
            n={formatInteger(summary?.sample_size ?? 0)}
          </div>
          <div className="mt-0.5 text-[11px] text-faint">IC {formatRatio(summary?.information_coefficient ?? null)}</div>
        </div>
      </div>

      <div className="mt-3 grid gap-2">
        <LabeledBar
          label="hit"
          value={formatPercent(hitRate)}
          width={hitRate === null ? 0 : Math.max(2, hitRate * 100)}
          tone="brand"
        />
        <AverageBar value={average} maxAverage={maxAverage} />
      </div>
    </article>
  );
}

function ConvictionBoard({
  signals,
  selectedKey,
  isError,
  isLoading,
  onSelect
}: {
  signals: SignalDaily[];
  selectedKey: string | null;
  isError: boolean;
  isLoading: boolean;
  onSelect: (securityKey: string) => void;
}) {
  if (isError) {
    return <StatusCard tone="error">컨빅션 랭킹을 불러오지 못했습니다.</StatusCard>;
  }
  if (isLoading) {
    return <CardSkeletonList count={4} metrics={2} />;
  }
  if (signals.length === 0) {
    return <StatusCard>오늘 동시 매수 시그널이 없습니다.</StatusCard>;
  }

  return (
    <div className="space-y-2">
      {signals.map((signal, index) => (
        <button
          key={`${signal.security_key}-${signal.as_of_date}`}
          type="button"
          onClick={() => onSelect(signal.security_key)}
          className={`w-full rounded-lg border bg-surface p-3 text-left transition ${
            selectedKey === signal.security_key
              ? "border-brand shadow-soft"
              : "border-line hover:border-line-strong"
          }`}
          aria-pressed={selectedKey === signal.security_key}
        >
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-soft text-xs font-bold text-brand">
              {index + 1}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="truncate text-base font-bold text-ink">{signal.security_ticker}</span>
                <span className="rounded-full bg-rise/10 px-2 py-0.5 text-[11px] font-semibold text-rise">
                  +{formatRatio(signal.conviction_score)}
                </span>
              </div>
              <p className="mt-0.5 truncate text-xs text-muted">{signal.security_name}</p>
            </div>
            <ChevronRight className="h-4 w-4 shrink-0 text-faint" aria-hidden="true" />
          </div>

          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <MiniMetric label="매수 ETF" value={formatInteger(signal.n_buying)} />
            <MiniMetric label="매도 ETF" value={formatInteger(signal.n_selling)} />
            <MiniMetric label="달러흐름" value={formatCompactCurrency(signal.net_dollar_flow)} />
          </div>
        </button>
      ))}
    </div>
  );
}

function SecuritySignalPanel({
  horizon,
  selectedSignal,
  history,
  outcomes,
  isLoading,
  isError
}: {
  horizon: HorizonDays;
  selectedSignal: SignalDaily | null;
  history: SignalSecurityHistory[];
  outcomes: SecurityAnalysisPoint[];
  isLoading: boolean;
  isError: boolean;
}) {
  const latest = history[0] ?? null;
  const participants = latest?.participants ?? [];
  const selectedName = selectedSignal?.security_name ?? latest?.security_name ?? "";
  const selectedTicker = selectedSignal?.security_ticker ?? latest?.security_ticker ?? "";

  return (
    <section className="rounded-xl border border-line bg-surface p-4 shadow-soft" aria-label="종목 시그널 상세">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs font-semibold text-brand">
            <LineChart className="h-4 w-4" aria-hidden="true" />
            종목 상세
          </div>
          <h2 className="mt-2 truncate text-xl font-bold text-ink">
            {selectedTicker || "선택된 종목 없음"}
          </h2>
          <p className="mt-1 truncate text-sm text-muted">{selectedName || "컨빅션 보드에서 종목을 선택하세요."}</p>
        </div>
        {latest ? (
          <time className="shrink-0 text-xs font-medium tabular-nums text-faint" dateTime={latest.as_of_date}>
            {latest.as_of_date}
          </time>
        ) : null}
      </div>

      {isError ? (
        <div className="mt-4">
          <StatusCard tone="error">종목 상세 데이터를 불러오지 못했습니다.</StatusCard>
        </div>
      ) : isLoading ? (
        <div className="mt-4">
          <CardSkeletonList count={1} metrics={3} />
        </div>
      ) : selectedSignal === null ? (
        <div className="mt-4">
          <StatusCard>아직 표시할 종목 시그널이 없습니다.</StatusCard>
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-3 gap-2">
            <MetricCard label="매수 ETF" value={formatInteger(latest?.n_buying ?? selectedSignal.n_buying)} caption="latest" />
            <MetricCard label="매도 ETF" value={formatInteger(latest?.n_selling ?? selectedSignal.n_selling)} caption="latest" />
            <MetricCard
              label="순달러흐름"
              value={formatCompactCurrency(latest?.net_dollar_flow ?? selectedSignal.net_dollar_flow)}
              caption="shares Δ × 가격"
            />
          </div>

          <OutcomeChart points={outcomes} horizon={horizon} />

          <ParticipantList participants={participants} />
        </div>
      )}
    </section>
  );
}

function OutcomeChart({ points, horizon }: { points: SecurityAnalysisPoint[]; horizon: HorizonDays }) {
  const palette = useChartPalette();
  const chartData = useMemo(
    () =>
      points
        .filter((point) => point.horizon_days === horizon)
        .slice()
        .reverse()
        .slice(-12)
        .map((point) => ({
          date: point.as_of_date.slice(5),
          excessReturn: point.excess_return * 100,
          stockReturn: point.stock_return * 100,
          benchmarkReturn: point.benchmark_return * 100,
          signalScore: point.signal_score
        })),
    [horizon, points]
  );

  if (chartData.length === 0) {
    return (
      <StatusCard>
        {horizon}D 평가가 완료된 과거 시그널이 아직 없습니다.
      </StatusCard>
    );
  }

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">시그널 이후 초과수익</h3>
        <span className="text-xs text-faint">막대: QQQ 대비, 선: conviction</span>
      </div>
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 8, right: 0, left: -16, bottom: 0 }}>
            <CartesianGrid stroke={palette.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: palette.tick }} stroke={palette.axis} minTickGap={18} />
            <YAxis
              yAxisId="return"
              tick={{ fontSize: 11, fill: palette.tick }}
              stroke={palette.axis}
              unit="%"
              width={44}
            />
            <YAxis yAxisId="score" orientation="right" hide domain={["auto", "auto"]} />
            <Tooltip
              contentStyle={palette.tooltip}
              formatter={(value, name) => {
                const numeric = Number(value);
                if (name === "signalScore") {
                  return [formatRatio(numeric), "conviction"];
                }
                if (name === "stockReturn") {
                  return [formatPercent(numeric / 100, true), "종목"];
                }
                if (name === "benchmarkReturn") {
                  return [formatPercent(numeric / 100, true), "QQQ"];
                }
                return [formatPercent(numeric / 100, true), "초과수익"];
              }}
            />
            <Bar yAxisId="return" dataKey="excessReturn" name="excessReturn" radius={[4, 4, 0, 0]}>
              {chartData.map((point) => (
                <Cell
                  key={`${point.date}-${point.excessReturn}`}
                  fill={point.excessReturn >= 0 ? "#16a34a" : "#2f6ae0"}
                />
              ))}
            </Bar>
            <Line
              yAxisId="score"
              type="monotone"
              dataKey="signalScore"
              name="signalScore"
              stroke={palette.line}
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ParticipantList({ participants }: { participants: SignalParticipant[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-ink">누가 샀나</h3>
      {participants.length === 0 ? (
        <p className="mt-2 rounded-lg border border-hair bg-panel px-3 py-4 text-sm text-muted">
          최신 참여 ETF 데이터가 없습니다.
        </p>
      ) : (
        <ul className="mt-2 divide-y divide-hair rounded-lg border border-line">
          {participants.slice(0, 6).map((participant) => (
            <li key={`${participant.etf_ticker}-${participant.direction}`} className="flex items-center gap-3 p-3">
              <div
                className={`h-2 w-2 shrink-0 rounded-full ${
                  participant.direction === "BUY" ? "bg-rise" : "bg-fall"
                }`}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <Link href={`/etfs/${participant.etf_ticker}`} className="font-semibold text-ink hover:text-brand">
                  {participant.etf_ticker}
                </Link>
                <p className="truncate text-xs text-muted">{participant.etf_name}</p>
              </div>
              <div className="shrink-0 text-right">
                <div className="text-xs font-semibold tabular-nums text-ink">
                  {formatSignedNumber(participant.shares_delta)}
                </div>
                <div className="text-[11px] text-faint">{participant.change_type}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  caption,
  tone = "neutral"
}: {
  label: string;
  value: string;
  caption: string;
  tone?: "neutral" | "positive" | "negative";
}) {
  const toneClass = tone === "positive" ? "text-gain" : tone === "negative" ? "text-fall" : "text-ink";
  return (
    <div className="rounded-lg border border-line bg-surface p-3">
      <div className="text-[11px] font-medium text-faint">{label}</div>
      <div className={`mt-1 text-lg font-bold leading-none tabular-nums ${toneClass}`}>{value}</div>
      <div className="mt-1.5 truncate text-[11px] text-muted">{caption}</div>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md bg-panel px-2 py-1.5">
      <div className="text-[10px] text-faint">{label}</div>
      <div className="mt-0.5 truncate font-semibold tabular-nums text-ink">{value}</div>
    </div>
  );
}

function ConfidenceChip({ sampleSize }: { sampleSize: number }) {
  const label = sampleSize >= 100 ? "표본 충분" : sampleSize >= 30 ? "관찰 중" : "표본 부족";
  const tone = sampleSize >= 100 ? "bg-gain/10 text-gain" : "bg-brand-soft text-brand";
  return <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold ${tone}`}>{label}</span>;
}

function LabeledBar({
  label,
  value,
  width,
  tone
}: {
  label: string;
  value: string;
  width: number;
  tone: "brand" | "gain" | "fall";
}) {
  const fillClass = tone === "brand" ? "bg-brand" : tone === "gain" ? "bg-gain" : "bg-fall";
  return (
    <div>
      <div className="mb-1 flex justify-between text-[11px] text-muted">
        <span>{label}</span>
        <span className="font-semibold tabular-nums text-ink">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-panel">
        <div className={`h-2 rounded-full ${fillClass}`} style={{ width: `${Math.min(width, 100)}%` }} />
      </div>
    </div>
  );
}

function AverageBar({ value, maxAverage }: { value: number | null; maxAverage: number }) {
  const ratio = value === null ? 0 : Math.min(Math.abs(value) / maxAverage, 1);
  const width = ratio * 50;
  const isPositive = (value ?? 0) >= 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-[11px] text-muted">
        <span>avg excess</span>
        <span className={`font-semibold tabular-nums ${toneClassForReturn(value)}`}>
          {formatPercent(value, true)}
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-panel">
        <div className="absolute left-1/2 top-0 h-2 w-px bg-line-strong" />
        <div
          className={`absolute top-0 h-2 rounded-full ${isPositive ? "bg-gain" : "bg-fall"}`}
          style={{
            left: isPositive ? "50%" : `${50 - width}%`,
            width: `${width}%`
          }}
        />
      </div>
    </div>
  );
}

function StatusCard({
  children,
  tone = "muted"
}: {
  children: React.ReactNode;
  tone?: "muted" | "error";
}) {
  return (
    <div
      className={`rounded-lg border border-line bg-surface px-4 py-8 text-center text-sm ${
        tone === "error" ? "text-rise" : "text-muted"
      }`}
    >
      {children}
    </div>
  );
}

function Disclaimer() {
  return (
    <section className="rounded-lg border border-line bg-panel p-4 text-xs leading-relaxed text-muted">
      <div className="mb-2 flex items-center gap-2 font-semibold text-ink">
        <AlertTriangle className="h-4 w-4 text-brand" aria-hidden="true" />
        해석 주의
      </div>
      백테스트 결과는 투자자문이 아니며 과거 성과가 미래 성과를 보장하지 않습니다. ETF의
      creation/redemption 때문에 shares Δ가 일부 오염될 수 있어 표본수, horizon, 벤치마크 대비
      초과수익을 함께 봐야 합니다.
    </section>
  );
}

function formatPercent(value: number | null, signed = false) {
  if (value === null || !Number.isFinite(value)) {
    return "-";
  }
  const percent = value * 100;
  const digits = Math.abs(percent) >= 10 ? 0 : 1;
  const sign = signed && percent > 0 ? "+" : "";
  return `${sign}${percent.toFixed(digits)}%`;
}

function formatRatio(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return "-";
  }
  return value.toFixed(Math.abs(value) >= 10 ? 0 : 2).replace(/\.00$/, "");
}

function formatInteger(value: number) {
  return Math.round(value).toLocaleString("ko-KR");
}

function formatSignedNumber(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return "-";
  }
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded.toLocaleString("ko-KR")}`;
}

function formatCompactCurrency(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return "-";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1
  }).format(value);
}

function toneForReturn(value: number | null): "neutral" | "positive" | "negative" {
  if (value === null || value === 0) {
    return "neutral";
  }
  return value > 0 ? "positive" : "negative";
}

function toneClassForReturn(value: number | null) {
  if (value === null || value === 0) {
    return "text-ink";
  }
  return value > 0 ? "text-gain" : "text-fall";
}
