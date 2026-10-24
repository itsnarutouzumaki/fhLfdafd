import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

afterEach(() => vi.unstubAllGlobals());

describe('Wind Forecast Intelligence Portal', () => {
  it('renders the portal shell and decision-cutoff control', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => undefined)));
    render(<App />);
    expect(screen.getByText('WIND / SIGNAL')).toBeInTheDocument();
    expect(screen.getByLabelText(/Decision cutoff/i)).toBeInTheDocument();
    expect(screen.getByText('January 2026')).toBeInTheDocument();
  });
});
