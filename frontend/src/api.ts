export type Status = 'matched' | 'forecast_missing' | 'actual_missing' | 'both_missing';

export interface Metrics {
  expected_intervals: number;
  actual_intervals: number;
  forecast_intervals: number;
  matched_intervals: number;
  coverage_pct: number | null;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  wape_pct: number | null;
}

export interface Interval {
  start_time: string;
  forecast_mw: number | null;
  actual_mw: number | null;
  error_mw: number | null;
  abs_error_mw: number | null;
  forecast_publish_time: string | null;
  decision_cutoff: string;
  status: Status;
}

export interface DailyTrend {
  date: string;
  mae_mw: number | null;
  bias_mw: number | null;
  matched_intervals: number;
  forecast_avg_mw: number | null;
  actual_avg_mw: number | null;
}

export interface DashboardData {
  generated_at: string;
  retrieved_at: string;
  evaluation_period: { start: string; end_exclusive: string };
  decision_cutoff: string;
  metrics: Metrics;
  daily_trend: DailyTrend[];
  series: Interval[];
  source_status: {
    status: 'connected' | 'partial' | 'empty';
    actual_records_received: number;
    forecast_records_received: number;
    message: string;
  };
}

export interface DayData {
  date: string;
  decision_cutoff: string;
  retrieved_at: string;
  metrics: Metrics;
  intervals: Interval[];
}

export interface DataStatus {
  status: 'connected' | 'partial' | 'empty' | 'unavailable';
  retrieved_at: string | null;
  actual_records_received: number;
  forecast_records_received: number;
  message: string;
}

async function request<T>(url: string): Promise<T> {
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = typeof body.detail === 'string' ? body.detail : message;
    } catch {
      // Keep the HTTP status when the response does not contain JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  dashboard: (cutoff: string, refresh = false) => request<DashboardData>(`/api/dashboard?cutoff=${encodeURIComponent(cutoff)}&refresh=${refresh}`),
  day: (date: string, cutoff: string) => request<DayData>(`/api/forecast/day?date=${encodeURIComponent(date)}&cutoff=${encodeURIComponent(cutoff)}`),
  accuracy: (cutoff: string) => request<Pick<DashboardData, 'metrics' | 'daily_trend' | 'series'>>(`/api/accuracy?cutoff=${encodeURIComponent(cutoff)}`),
  status: () => request<DataStatus>('/api/data-status'),
};
