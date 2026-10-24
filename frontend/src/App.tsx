import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Activity, AlertCircle, ArrowDownRight, ArrowUpRight, BarChart3, CalendarDays,
  CheckCircle2, ChevronDown, CircleHelp, Clock3, Database, Download, FileChartColumnIncreasing,
  Gauge, LayoutDashboard, RefreshCw, ShieldCheck, Wind, Zap,
} from 'lucide-react';
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { api, type DashboardData, type DataStatus, type DayData } from './api';
import { dayLabel, number, percent, timeLabel, timestampLabel } from './format';

type Page = 'overview' | 'explorer' | 'accuracy' | 'methodology';

const navigation: { id: Page; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'explorer', label: 'Forecast explorer', icon: Wind },
  { id: 'accuracy', label: 'Accuracy analysis', icon: FileChartColumnIncreasing },
  { id: 'methodology', label: 'Data & methodology', icon: Database },
];

function MetricCard({
  label, value, unit, icon: Icon, detail, tone = 'default',
}: {
  label: string; value: string; unit: string; icon: typeof Activity; detail: string; tone?: 'default' | 'positive' | 'negative';
}) {
  return (
    <article className="metric-card">
      <div className="metric-topline">
        <span className="metric-label">{label}</span>
        <span className={`metric-icon ${tone}`}><Icon size={17} strokeWidth={1.8} /></span>
      </div>
      <div className="metric-value-row">
        <span className="metric-value">{value}</span>
        <span className="metric-unit">{unit}</span>
      </div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}

function Panel({ title, subtitle, action, children, className = '' }: {
  title: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function SourcePill({ status }: { status: DataStatus['status'] | 'loading' }) {
  const content = status === 'connected'
    ? { label: 'Elexon connected', icon: CheckCircle2, className: 'status-good' }
    : status === 'loading'
      ? { label: 'Checking source', icon: RefreshCw, className: 'status-loading' }
      : status === 'empty'
        ? { label: 'No source records', icon: AlertCircle, className: 'status-warn' }
        : status === 'partial'
          ? { label: 'Partial source data', icon: AlertCircle, className: 'status-warn' }
          : { label: 'Source unavailable', icon: AlertCircle, className: 'status-bad' };
  const Icon = content.icon;
  return <span className={`source-pill ${content.className}`}><Icon size={14} />{content.label}</span>;
}

function EmptyChart({ message }: { message: string }) {
  return <div className="chart-empty"><div className="empty-mark"><Wind size={23} /></div><strong>No chartable observations</strong><span>{message}</span></div>;
}

function EmptyState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="error-state">
      <div className="error-mark"><AlertCircle size={25} /></div>
      <h2>We couldn’t load the January dataset</h2>
      <p>{error}</p>
      <p className="muted">The portal does not substitute example values for actual Elexon observations. Check API connectivity and try again.</p>
      <button className="button button-primary" onClick={onRetry}><RefreshCw size={15} /> Retry connection</button>
      <a href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream" target="_blank" rel="noreferrer">Open Elexon dataset documentation ↗</a>
    </div>
  );
}

function Overview({ data }: { data: DashboardData }) {
  const metrics = data.metrics;
  const hasMatches = metrics.matched_intervals > 0;
  const chartData = useMemo(() => data.series.map((row) => ({ ...row, day: row.start_time.slice(8, 10) })), [data.series]);
  const meanActual = useMemo(() => {
    const values = data.series.map((row) => row.actual_mw).filter((value): value is number => value !== null);
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  }, [data.series]);
  const interpretation = metrics.bias_mw === null
    ? 'Once a forecast and an actual are both available for the same interval, the portal will summarize the direction and size of forecast errors.'
    : Math.abs(metrics.bias_mw) < 1
      ? 'Average forecast bias is close to zero for the matched intervals. Review MAE and RMSE as well: positive and negative errors can cancel out in the average.'
      : metrics.bias_mw > 0
        ? `Wind generation was overforecast by ${number(metrics.bias_mw)} MW on average across matched intervals. Actual errors vary by interval, so use the distribution and daily trend as context.`
        : `Wind generation was underforecast by ${number(Math.abs(metrics.bias_mw))} MW on average across matched intervals. Actual errors vary by interval, so use the distribution and daily trend as context.`;

  return (
    <>
      <div className="metric-grid">
        <MetricCard label="Mean absolute error" value={number(metrics.mae_mw)} unit="MW" icon={Activity} detail="Average absolute difference" />
        <MetricCard label="Root mean squared error" value={number(metrics.rmse_mw)} unit="MW" icon={Gauge} detail="Penalizes larger misses" />
        <MetricCard label="Forecast bias" value={number(metrics.bias_mw)} unit="MW" icon={metrics.bias_mw !== null && metrics.bias_mw < 0 ? ArrowDownRight : ArrowUpRight} tone={metrics.bias_mw !== null && metrics.bias_mw < 0 ? 'negative' : 'positive'} detail="Forecast minus actual" />
        <MetricCard label="Weighted absolute error" value={number(metrics.wape_pct, 1)} unit="%" icon={BarChart3} detail="Scaled by matched actuals" />
        <MetricCard label="Matched coverage" value={percent(metrics.coverage_pct)} unit="" icon={ShieldCheck} detail={`${number(metrics.matched_intervals)} of ${number(metrics.expected_intervals)} intervals`} />
      </div>

      <div className="content-grid overview-grid">
        <Panel title="Wind generation · forecast vs actual" subtitle="National half-hourly average power · January 2026" className="chart-panel">
          {hasMatches ? (
            <div className="chart-wrap chart-tall">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 18, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8eef0" />
                  <XAxis dataKey="start_time" tickFormatter={(value) => dayLabel(value)} interval={47} tick={{ fill: '#7d8d94', fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={12} />
                  <YAxis tickFormatter={(value) => number(value / 1000, 1) + 'k'} tick={{ fill: '#7d8d94', fontSize: 11 }} axisLine={false} tickLine={false} width={52} />
                  <Tooltip labelFormatter={(value) => timestampLabel(String(value))} formatter={(value, name) => [`${number(Number(value))} MW`, name === 'forecast_mw' ? 'Decision-time forecast' : 'Actual generation']} contentStyle={{ border: '1px solid #e3eaed', borderRadius: 12, fontSize: 12, boxShadow: '0 8px 24px rgba(13, 42, 53, .08)' }} />
                  <Legend verticalAlign="top" height={34} iconType="circle" wrapperStyle={{ fontSize: 12, color: '#52666e' }} formatter={(value) => value === 'forecast_mw' ? 'Decision-time forecast' : 'Actual generation'} />
                  <Line type="monotone" dataKey="forecast_mw" name="forecast_mw" stroke="#177e89" strokeWidth={2} dot={false} connectNulls={false} activeDot={{ r: 4 }} />
                  <Line type="monotone" dataKey="actual_mw" name="actual_mw" stroke="#e5a14c" strokeWidth={1.9} dot={false} connectNulls={false} activeDot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyChart message="Forecast and actual pairs are required to draw the comparison." />}
          <div className="chart-footnote"><span><span className="legend-dot teal" /> Forecast vintage selected at {data.decision_cutoff} UK time on D−1</span><span><span className="legend-dot amber" /> Actual generation</span></div>
        </Panel>

        <Panel title="Data coverage" subtitle="Completeness of the evaluation window" className="coverage-panel">
          <div className="coverage-score"><span>{percent(metrics.coverage_pct)}</span><span className="coverage-caption">matched pairs</span></div>
          <div className="coverage-bar"><span style={{ width: `${Math.min(100, Math.max(0, metrics.coverage_pct ?? 0))}%` }} /></div>
          <div className="coverage-rows">
            <div><span>Expected intervals</span><strong>{number(metrics.expected_intervals)}</strong></div>
            <div><span>Intervals with actuals</span><strong>{number(metrics.actual_intervals)}</strong></div>
            <div><span>Eligible forecasts</span><strong>{number(metrics.forecast_intervals)}</strong></div>
            <div><span>Matched pairs</span><strong>{number(metrics.matched_intervals)}</strong></div>
          </div>
          <div className="insight-note"><div className="insight-icon"><CircleHelp size={16} /></div><p>{interpretation}</p></div>
          <div className="source-mini"><span className="source-mini-icon"><Database size={16} /></span><div><strong>Source records</strong><span>{number(data.source_status.actual_records_received)} actual · {number(data.source_status.forecast_records_received)} forecast</span></div></div>
        </Panel>
      </div>

      <Panel title="Daily forecast accuracy" subtitle="MAE by delivery date · lower is better" action={<span className="panel-badge">31-day period</span>}>
        {data.daily_trend.some((item) => item.mae_mw !== null) ? (
          <div className="chart-wrap chart-short">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.daily_trend} margin={{ top: 8, right: 18, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8eef0" />
                <XAxis dataKey="date" tickFormatter={(value) => new Date(`${value}T12:00:00Z`).getUTCDate().toString()} tick={{ fill: '#7d8d94', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={(value) => number(value)} tick={{ fill: '#7d8d94', fontSize: 11 }} axisLine={false} tickLine={false} width={50} />
                <Tooltip labelFormatter={(value) => dayLabel(String(value))} formatter={(value) => [`${number(Number(value))} MW`, 'MAE']} contentStyle={{ border: '1px solid #e3eaed', borderRadius: 12, fontSize: 12 }} />
                <Bar dataKey="mae_mw" fill="#177e89" radius={[4, 4, 0, 0]} maxBarSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <EmptyChart message="Daily accuracy will appear when matched observations are available." />}
      </Panel>

      <div className="closing-note"><Zap size={16} /><span>Forecast error helps frame renewable uncertainty. This portal does not calculate total residual demand or exact energy purchases because customer demand and existing market positions are outside the data scope.</span></div>
      {meanActual !== null && <span className="sr-only">Average actual generation {number(meanActual)} MW</span>}
    </>
  );
}

function Explorer({ data, selectedDate, setSelectedDate, error }: { data: DayData | null; selectedDate: string; setSelectedDate: (value: string) => void; error: string }) {
  const matched = data?.metrics.matched_intervals ?? 0;
  return (
    <>
      <div className="page-intro-row"><div><h2>Decision-time forecast explorer</h2><p>Inspect the forecast vintage that was available before the decision deadline for each half-hour.</p></div>
        <label className="date-field"><CalendarDays size={16} /><span>Delivery date</span><input aria-label="Delivery date" type="date" min="2026-01-01" max="2026-01-31" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} /></label>
      </div>
      {error ? <div className="table-notice"><AlertCircle size={16} />{error}</div> : !data ? <div className="inline-loading"><RefreshCw size={17} className="spin" /> Loading interval data…</div> : (
        <>
          <div className="metric-grid compact-metrics">
            <MetricCard label="Day MAE" value={number(data.metrics.mae_mw)} unit="MW" icon={Activity} detail="Average absolute error" />
            <MetricCard label="Day bias" value={number(data.metrics.bias_mw)} unit="MW" icon={Gauge} detail="Forecast minus actual" />
            <MetricCard label="Matched intervals" value={number(data.metrics.matched_intervals)} unit="/ 48" icon={ShieldCheck} detail={`${percent(data.metrics.coverage_pct)} coverage`} />
          </div>
          <Panel title={`${dayLabel(`${selectedDate}T12:00:00Z`)} delivery intervals`} subtitle={`Forecast cutoff: ${data.decision_cutoff} UK time on the preceding day`} className="table-panel">
            {matched === 0 && <div className="table-notice"><AlertCircle size={16} /> No matched forecast/actual pairs are available for this date. Missing source values remain blank.</div>}
            <div className="table-scroll"><table><thead><tr><th>Delivery time</th><th>Forecast (MW)</th><th>Actual (MW)</th><th>Error (MW)</th><th>Published at (UK)</th><th>Status</th></tr></thead><tbody>
              {data.intervals.map((row) => <tr key={row.start_time}>
                <td className="time-cell">{timeLabel(row.start_time)}</td>
                <td>{number(row.forecast_mw)}</td><td>{number(row.actual_mw)}</td>
                <td className={row.error_mw === null ? '' : row.error_mw > 0 ? 'error-positive' : row.error_mw < 0 ? 'error-negative' : ''}>{row.error_mw === null ? '—' : `${row.error_mw > 0 ? '+' : ''}${number(row.error_mw)}`}</td>
                <td className="publish-cell">{row.forecast_publish_time ? timestampLabel(row.forecast_publish_time) : '—'}</td>
                <td><span className={`row-status ${row.status}`}>{row.status === 'matched' ? 'Matched' : row.status === 'forecast_missing' ? 'No forecast' : row.status === 'actual_missing' ? 'No actual' : 'No data'}</span></td>
              </tr>)}
            </tbody></table></div>
          </Panel>
          <p className="table-help">All timestamps are shown in UK local time. Forecasts published after the deadline are excluded even if later revisions exist.</p>
        </>
      )}
    </>
  );
}

function Accuracy({ data }: { data: DashboardData }) {
  const errors = data.series.filter((row) => row.error_mw !== null).map((row) => row.error_mw as number);
  const distribution = useMemo(() => {
    if (!errors.length) return [];
    const extent = Math.max(...errors.map(Math.abs), 1);
    const step = (2 * extent) / 8;
    const bins = Array.from({ length: 8 }, (_, index) => {
      const low = -extent + step * index;
      const high = low + step;
      return { range: `${number(low / 1000, 1)}–${number(high / 1000, 1)}k`, low, high, count: 0 };
    });
    errors.forEach((error) => {
      let index = Math.floor((error + extent) / step);
      index = Math.min(7, Math.max(0, index));
      bins[index].count += 1;
    });
    return bins;
  }, [errors.join('|')]);
  const positivePct = errors.length ? 100 * errors.filter((value) => value > 0).length / errors.length : null;
  const negativePct = errors.length ? 100 * errors.filter((value) => value < 0).length / errors.length : null;
  return (
    <>
      <div className="page-intro-row"><div><h2>Forecast accuracy analysis</h2><p>Understand the scale, direction and distribution of forecast errors across January 2026.</p></div><span className="panel-badge">Cutoff · {data.decision_cutoff} D−1</span></div>
      <div className="metric-grid compact-metrics">
        <MetricCard label="Mean absolute error" value={number(data.metrics.mae_mw)} unit="MW" icon={Activity} detail="Typical absolute miss" />
        <MetricCard label="Root mean squared error" value={number(data.metrics.rmse_mw)} unit="MW" icon={Gauge} detail="More sensitive to large errors" />
        <MetricCard label="Mean bias" value={number(data.metrics.bias_mw)} unit="MW" icon={data.metrics.bias_mw !== null && data.metrics.bias_mw < 0 ? ArrowDownRight : ArrowUpRight} detail="Sign indicates forecast direction" />
        <MetricCard label="WAPE" value={number(data.metrics.wape_pct, 1)} unit="%" icon={BarChart3} detail="Absolute error relative to actuals" />
      </div>
      <div className="content-grid two-col">
        <Panel title="Daily error profile" subtitle="Absolute error and directional bias, in MW">
          {data.daily_trend.some((row) => row.mae_mw !== null) ? <div className="chart-wrap chart-tall"><ResponsiveContainer width="100%" height="100%"><LineChart data={data.daily_trend} margin={{ top: 8, right: 16, left: -12, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8eef0" /><XAxis dataKey="date" tickFormatter={(value) => new Date(`${value}T12:00:00Z`).getUTCDate().toString()} tick={{ fill: '#7d8d94', fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: '#7d8d94', fontSize: 11 }} axisLine={false} tickLine={false} width={50} /><ReferenceLine y={0} stroke="#b8c6cb" /><Tooltip labelFormatter={(value) => dayLabel(String(value))} formatter={(value, name) => [`${number(Number(value))} MW`, name === 'mae_mw' ? 'MAE' : 'Bias']} contentStyle={{ border: '1px solid #e3eaed', borderRadius: 12, fontSize: 12 }} /><Legend verticalAlign="top" height={32} formatter={(value) => value === 'mae_mw' ? 'MAE' : 'Bias'} /><Line type="monotone" dataKey="mae_mw" stroke="#177e89" strokeWidth={2} dot={false} connectNulls={false} /><Line type="monotone" dataKey="bias_mw" stroke="#df9d45" strokeWidth={1.8} dot={false} connectNulls={false} /></LineChart></ResponsiveContainer></div> : <EmptyChart message="No matched intervals are available for analysis." />}
        </Panel>
        <Panel title="Error distribution" subtitle="Forecast minus actual · positive means overforecast">
          {distribution.length ? <div className="chart-wrap chart-tall"><ResponsiveContainer width="100%" height="100%"><BarChart data={distribution} margin={{ top: 8, right: 12, left: -15, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8eef0" /><XAxis dataKey="range" tick={{ fill: '#7d8d94', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: '#7d8d94', fontSize: 11 }} axisLine={false} tickLine={false} width={38} /><Tooltip formatter={(value) => [number(Number(value)), 'Intervals']} contentStyle={{ border: '1px solid #e3eaed', borderRadius: 12, fontSize: 12 }} /><Bar dataKey="count" fill="#177e89" radius={[4, 4, 0, 0]} maxBarSize={34} /></BarChart></ResponsiveContainer></div> : <EmptyChart message="Error distribution will appear when matched pairs are available." />}
        </Panel>
      </div>
      <Panel title="Direction of errors" subtitle="Share of matched intervals by error sign">
        <div className="direction-grid"><div className="direction-card"><span className="direction-dot over" /><div><span>Overforecast intervals</span><strong>{percent(positivePct)}</strong><small>Forecast greater than actual</small></div></div><div className="direction-card"><span className="direction-dot under" /><div><span>Underforecast intervals</span><strong>{percent(negativePct)}</strong><small>Forecast less than actual</small></div></div><div className="direction-card"><span className="direction-dot exact" /><div><span>Exact matches</span><strong>{percent(errors.length ? 100 * errors.filter((value) => value === 0).length / errors.length : null)}</strong><small>Forecast equals actual</small></div></div></div>
      </Panel>
      <div className="closing-note"><CircleHelp size={16} /><span>Bias is a signed average and can be close to zero even when individual forecast errors are large. Read it alongside MAE, RMSE, coverage and the error distribution.</span></div>
    </>
  );
}

function Methodology({ status }: { status: DataStatus | null }) {
  return (
    <>
      <div className="page-intro-row"><div><h2>Data & methodology</h2><p>How source observations become a decision-time forecast comparison.</p></div><SourcePill status={status?.status ?? 'loading'} /></div>
      <div className="content-grid two-col method-grid">
        <Panel title="Source datasets" subtitle="Only the two datasets in the assignment are used">
          <div className="dataset-item"><div className="dataset-symbol actual-symbol"><Database size={18} /></div><div><strong>FUELHH · Actual generation</strong><p>Half-hourly generation outturn. The application filters to the WIND fuel type and aligns observations by delivery timestamp.</p><a href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream" target="_blank" rel="noreferrer">FUELHH API documentation ↗</a></div></div>
          <div className="dataset-item"><div className="dataset-symbol forecast-symbol"><Wind size={18} /></div><div><strong>WINDFOR · Forecast vintages</strong><p>Historical wind forecast records with both a delivery timestamp and a publication timestamp, allowing a time-correct comparison.</p><a href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream" target="_blank" rel="noreferrer">WINDFOR API documentation ↗</a></div></div>
          <div className="method-note"><ShieldCheck size={17} /><p>Data is fetched from the official Elexon API. When the source is unavailable, this portal reports the issue rather than fabricating observations.</p></div>
        </Panel>
        <Panel title="Decision-time selection" subtitle="No look-ahead in forecast evaluation">
          <ol className="method-steps"><li><span>01</span><div><strong>Choose a delivery interval</strong><p>Each target interval is normalized to a UTC timestamp.</p></div></li><li><span>02</span><div><strong>Set the D−1 decision deadline</strong><p>The default is 09:00 UK local time on the previous calendar day. An alternative cutoff can be selected.</p></div></li><li><span>03</span><div><strong>Select the latest eligible vintage</strong><p>Among forecasts for the target interval, select the latest publication at or before the deadline.</p></div></li><li><span>04</span><div><strong>Join to actual outturn</strong><p>Match by delivery timestamp. Missing actuals or forecasts remain missing and lower the coverage score.</p></div></li></ol>
        </Panel>
        <Panel title="Metrics and units" subtitle="Calculated on matched forecast / actual pairs" className="full-span">
          <div className="formula-grid"><div><strong>MAE</strong><code>mean(|forecast − actual|)</code><span>Typical absolute forecast error · MW</span></div><div><strong>RMSE</strong><code>sqrt(mean((forecast − actual)²))</code><span>Penalizes larger errors · MW</span></div><div><strong>Bias</strong><code>mean(forecast − actual)</code><span>Positive = overforecast · MW</span></div><div><strong>WAPE</strong><code>sum(|error|) / sum(actual) × 100</code><span>Unavailable when the actual denominator is zero · %</span></div></div>
        </Panel>
        <Panel title="Scope and assumptions" subtitle="Important context for interpreting the analysis" className="full-span">
          <div className="limits-list"><div><CheckCircle2 size={16} /><span>Delivery interval scope: 1–31 January 2026, half-hourly.</span></div><div><CheckCircle2 size={16} /><span>All decision deadlines are interpreted in the Europe/London timezone; API timestamps are normalized to UTC.</span></div><div><CheckCircle2 size={16} /><span>January is on GMT. The timezone-aware cutoff logic also handles UK daylight-saving transitions in other periods.</span></div><div><AlertCircle size={16} /><span>09:00 D−1 is an explicit product assumption, not a confirmed client trading deadline.</span></div><div><AlertCircle size={16} /><span>This application does not calculate residual customer demand, exact procurement volume, energy prices or savings.</span></div><div><AlertCircle size={16} /><span>Only Elexon's FUELHH and WINDFOR datasets are used for observations and forecasts; no weather, demand or market-price datasets are added.</span></div></div>
        </Panel>
      </div>
      <div className="footer-attribution">Data source: Elexon Insights Solution / BMRS. Use is subject to Elexon's applicable data licence and API terms.</div>
    </>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>('overview');
  const [cutoff, setCutoff] = useState('09:00');
  const [selectedDate, setSelectedDate] = useState('2026-01-15');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [dayData, setDayData] = useState<DayData | null>(null);
  const [status, setStatus] = useState<DataStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [dayLoading, setDayLoading] = useState(false);
  const [dayError, setDayError] = useState('');
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api.dashboard(cutoff, refreshKey > 0).then((result) => {
      if (!active) return;
      setDashboard(result);
      setStatus({
        status: result.source_status.status,
        retrieved_at: result.retrieved_at,
        actual_records_received: result.source_status.actual_records_received,
        forecast_records_received: result.source_status.forecast_records_received,
        message: result.source_status.message,
      });
    }).catch((reason: unknown) => {
      if (!active) return;
      setDashboard(null);
      setStatus({ status: 'unavailable', retrieved_at: null, actual_records_received: 0, forecast_records_received: 0, message: 'Elexon data could not be retrieved from the current runtime.' });
      setError(reason instanceof Error ? reason.message : 'The source request failed.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [cutoff, refreshKey]);

  useEffect(() => {
    if (page !== 'explorer' || !dashboard) return;
    let active = true;
    setDayLoading(true);
    setDayData(null);
    setDayError('');
    api.day(selectedDate, cutoff).then((result) => {
      if (active) setDayData(result);
    }).catch((reason: unknown) => {
      if (active) setDayError(reason instanceof Error ? reason.message : 'Could not load delivery-day data.');
    }).finally(() => { if (active) setDayLoading(false); });
    return () => { active = false; };
  }, [page, selectedDate, cutoff, refreshKey, dashboard]);

  const activeNav = navigation.find((item) => item.id === page);
  const title = activeNav?.label ?? 'Overview';
  const subtitle = page === 'overview'
    ? 'A clearer view of wind forecast uncertainty before the day-ahead decision.'
    : page === 'explorer'
      ? 'Review the exact forecast vintage eligible at a chosen decision deadline.'
      : page === 'accuracy'
        ? 'Quantify forecast error, direction and day-to-day variability.'
        : 'Trace the source data, selection logic and analysis assumptions.';

  function retry() {
    setError('');
    setDashboard(null);
    setRefreshKey((value) => value + 1);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup"><div className="brand-mark"><Wind size={22} strokeWidth={2.1} /></div><div><strong>WIND / SIGNAL</strong><span>Forecast intelligence</span></div></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          {navigation.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => { setPage(id); setError(''); }}><Icon size={18} strokeWidth={1.8} /><span>{label}</span>{id === 'explorer' && <ChevronDown size={14} className="nav-chevron" />}</button>)}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-period"><span className="period-marker" /><div><span>Evaluation period</span><strong>January 2026</strong><small>Great Britain · National</small></div></div>
        <div className="sidebar-footer"><span className="avatar">WF</span><div><strong>Energy analytics</strong><span>Pilot workspace</span></div><button className="icon-button subtle" aria-label="Help"><CircleHelp size={17} /></button></div>
      </aside>

      <main className="main-area">
        <header className="topbar"><div className="breadcrumbs"><span>Workspace</span><span className="crumb-sep">/</span><strong>{title}</strong></div><div className="topbar-actions"><span className="period-chip"><CalendarDays size={14} /> 01–31 Jan 2026</span><SourcePill status={loading ? 'loading' : (status?.status ?? 'unavailable')} /><a className="button button-quiet export-button" href={`/api/export.csv?cutoff=${encodeURIComponent(cutoff)}`}><Download size={15} /> Export CSV</a></div></header>
        <div className="page-content">
          <div className="page-heading"><div><div className="eyebrow">ENERGY MARKET INTELLIGENCE <span /> PILOT</div><h1>{title}</h1><p>{subtitle}</p></div><div className="cutoff-control"><label htmlFor="cutoff-select"><Clock3 size={15} /> Decision cutoff</label><select id="cutoff-select" value={cutoff} onChange={(event) => setCutoff(event.target.value)}><option value="09:00">09:00 · Morning</option><option value="15:00">15:00 · Afternoon</option></select><span>D−1 · UK local time</span></div></div>

          {status && status.status !== 'connected' && !loading && <div className="source-alert"><AlertCircle size={17} /><div><strong>{status.status === 'unavailable' ? 'Live Elexon data is unavailable' : status.status === 'partial' ? 'Only one Elexon dataset returned records' : 'No January source records were returned'}</strong><span>{status.message}</span></div><button onClick={retry}>Retry</button></div>}
          {loading && <div className="loading-state"><div className="loading-spinner" /><strong>Retrieving January wind data</strong><span>Loading actual generation and historical forecast publications from Elexon.</span><div className="loading-line" /></div>}
          {!loading && !dashboard && page !== 'methodology' && <EmptyState error={error || 'Elexon data is not available from the current runtime.'} onRetry={retry} />}
          {!loading && dashboard && page === 'overview' && <Overview data={dashboard} />}
          {!loading && dashboard && page === 'explorer' && (dayLoading ? <div className="inline-loading"><RefreshCw size={17} className="spin" /> Loading interval data…</div> : <Explorer data={dayData} selectedDate={selectedDate} setSelectedDate={setSelectedDate} error={dayError} />)}
          {!loading && dashboard && page === 'accuracy' && <Accuracy data={dashboard} />}
          {!loading && page === 'methodology' && <Methodology status={status} />}
          <footer className="app-footer"><span>WIND / SIGNAL <span className="footer-sep">·</span> Forecast intelligence</span><span>Source: Elexon BMRS <span className="footer-sep">·</span> Units: average MW unless stated</span></footer>
        </div>
      </main>
    </div>
  );
}
