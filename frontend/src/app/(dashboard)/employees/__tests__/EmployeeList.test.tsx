/**
 * Employee list page — unit / integration tests.
 * Uses MSW for API mocking and React Testing Library.
 */

import { describe, it, expect, vi, beforeAll, afterEach, afterAll } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { http, HttpResponse }                 from 'msw';
import { setupServer }                        from 'msw/node';
import { QueryClient, QueryClientProvider }  from '@tanstack/react-query';

// ── Mock next/navigation ─────────────────────────────────────────────────────

const mockPush = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, back: vi.fn() }),
  useParams:  () => ({}),
}));

// ── Mock auth store ──────────────────────────────────────────────────────────

vi.mock('@/stores/authStore', () => ({
  useAuthStore: (selector: (s: unknown) => unknown) => {
    const fakeStore = {
      hasPermission: (_mod: string, _action: string) => true,
      user: { id: 'user-1', is_superadmin: true },
    };
    return selector(fakeStore);
  },
}));

// ── MSW server ───────────────────────────────────────────────────────────────

const MOCK_EMPLOYEES = {
  count: 2,
  next:  null,
  previous: null,
  results: [
    {
      id:                 'emp-1',
      employee_code:      'EMP-0001',
      full_name:          'Alice Smith',
      first_name:         'Alice',
      last_name:          'Smith',
      work_email:         'alice@example.com',
      personal_email:     null,
      phone_number:       null,
      photo_url:          null,
      employment_status:  'active',
      contract_type:      'permanent',
      department_name:    'Engineering',
      designation_title:  'Software Engineer',
      date_of_joining:    '2022-01-15',
      is_manager:         false,
    },
    {
      id:                 'emp-2',
      employee_code:      'EMP-0002',
      full_name:          'Bob Jones',
      first_name:         'Bob',
      last_name:          'Jones',
      work_email:         'bob@example.com',
      personal_email:     null,
      phone_number:       null,
      photo_url:          null,
      employment_status:  'on_leave',
      contract_type:      'contract',
      department_name:    'HR',
      designation_title:  'HR Manager',
      date_of_joining:    '2021-06-01',
      is_manager:         true,
    },
  ],
};

const server = setupServer(
  http.get('*/api/v1/employees', () => HttpResponse.json(MOCK_EMPLOYEES)),
  http.get('*/api/v1/departments', () => HttpResponse.json([])),
);

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Test wrapper ─────────────────────────────────────────────────────────────

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// Lazy import the page so mocks are set up first
async function renderPage() {
  const { default: EmployeesPage } = await import('../page');
  return render(<EmployeesPage />, { wrapper: Wrapper });
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('EmployeesPage', () => {
  it('renders page heading', async () => {
    await renderPage();
    expect(screen.getByText('Employees')).toBeInTheDocument();
  });

  it('shows employee rows after loading', async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText('Alice Smith')).toBeInTheDocument();
      expect(screen.getByText('Bob Jones')).toBeInTheDocument();
    });
  });

  it('shows employee codes', async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText('EMP-0001')).toBeInTheDocument();
      expect(screen.getByText('EMP-0002')).toBeInTheDocument();
    });
  });

  it('shows department names', async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText('Engineering')).toBeInTheDocument();
      expect(screen.getByText('HR')).toBeInTheDocument();
    });
  });

  it('shows Add employee button when user has create permission', async () => {
    await renderPage();
    expect(screen.getByText(/add employee/i)).toBeInTheDocument();
  });

  it('navigates to employee profile on row click', async () => {
    await renderPage();
    await waitFor(() => screen.getByText('Alice Smith'));
    fireEvent.click(screen.getByText('Alice Smith'));
    expect(mockPush).toHaveBeenCalledWith('/employees/emp-1');
  });

  it('navigates to new employee page on Add button click', async () => {
    await renderPage();
    fireEvent.click(screen.getByText(/add employee/i));
    expect(mockPush).toHaveBeenCalledWith('/employees/new');
  });

  it('shows empty state when no employees returned', async () => {
    server.use(
      http.get('*/api/v1/employees', () =>
        HttpResponse.json({ count: 0, next: null, previous: null, results: [] }),
      ),
    );
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText(/no employees found/i)).toBeInTheDocument();
    });
  });

  it('shows total count badge', async () => {
    await renderPage();
    await waitFor(() => {
      // Badge shows total count (2)
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  it('clears filters when Clear button is clicked', async () => {
    await renderPage();

    // Simulate a search being active (trigger re-render with filter text)
    // We test that the clear button appears when a search is typed
    const searchInput = screen.getByPlaceholderText(/search name/i);
    fireEvent.change(searchInput, { target: { value: 'test' } });
    fireEvent.keyDown(searchInput, { key: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText(/clear/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/clear/i));
    expect(searchInput).toHaveValue('');
  });
});

describe('EmployeesPage — status badges', () => {
  it('renders active badge for active employee', async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText('Active')).toBeInTheDocument();
    });
  });

  it('renders on_leave badge for employee on leave', async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText('On Leave')).toBeInTheDocument();
    });
  });
});
