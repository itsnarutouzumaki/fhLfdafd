export function number(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return new Intl.NumberFormat('en-GB', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);
}

export function percent(value: number | null | undefined): string {
  return value === null || value === undefined || !Number.isFinite(value) ? '—' : `${number(value, 1)}%`;
}

export function dayLabel(value: string): string {
  return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', timeZone: 'Europe/London' }).format(new Date(value));
}

export function timestampLabel(value: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London',
  }).format(new Date(value));
}

export function timeLabel(value: string): string {
  return new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London' }).format(new Date(value));
}
