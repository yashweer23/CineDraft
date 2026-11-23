import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { allocation, design } from './design';

afterEach(() => vi.unstubAllGlobals());

describe('studio health', () => {
  it('renders the backend and database success responses', async () => {
    const request = vi.fn(async (url: string) => new Response(JSON.stringify(
      url.endsWith('/ready') ? { status: 'ready', database: 'connected' }
        : { status: 'ok', service: 'cinedraft-api', version: '0.2.0' },
    ), { status: 200 }));
    vi.stubGlobal('fetch', request);
    render(<App />);
    expect(await screen.findByText(/Both services are connected/)).toBeInTheDocument();
    expect(request).toHaveBeenCalledWith('/api/health', expect.any(Object));
    expect(request).toHaveBeenCalledWith('/api/health/ready', expect.any(Object));
    expect(screen.getAllByText('Connected')).toHaveLength(2);
  });

  it('reports database failure and recovers after a user retry', async () => {
    let available = false;
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.endsWith('/ready')) return new Response(JSON.stringify(available
        ? { status: 'ready', database: 'connected' }
        : { error: { code: 'database_unavailable', message: 'Unavailable' }, request_id: 'fixture' }),
      { status: available ? 200 : 503 });
      return new Response(JSON.stringify({ status: 'ok', service: 'cinedraft-api' }));
    }));
    render(<App />);
    expect(await screen.findByText(/Check that PostgreSQL is running/)).toBeInTheDocument();
    expect(screen.getAllByText('Connected')).toHaveLength(1);
    available = true;
    await userEvent.click(screen.getByRole('button', { name: 'Check connection' }));
    expect(await screen.findByText(/Both services are connected/)).toBeInTheDocument();
  });

  it('does not mistake an HTML proxy response or missing API for healthy services', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<html>not the API</html>')));
    render(<App />);
    await waitFor(() => expect(screen.getAllByText('Unavailable')).toHaveLength(2));
    expect(screen.getByRole('button', { name: 'Check connection' })).toBeEnabled();
  });
});

describe('future design preview', () => {
  it('keeps integer-dollar allocations and labels future gameplay honestly', () => {
    expect(design.implementationStatus).toBe('planned');
    expect(design.tiers.map(t => allocation(t.totalBudgetUsd).hiringUsd)).toEqual([6500000, 32500000, 130000000]);
    expect(() => allocation(10.5)).toThrow();
    expect(design.slotOrder).toHaveLength(8);
    expect(design.offerRerolls).toBe(2);
    expect(design.finalRecasts).toBe(1);
  });
});
