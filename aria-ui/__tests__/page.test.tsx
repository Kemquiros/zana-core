import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import CockpitPage from '../app/page';

// Mock components
jest.mock('../components/AeonCard', () => ({
  __esModule: true,
  default: function MockAeonCard() { return <div data-testid="mock-aeon-card" />; },
  AEONS: [{ id: 'test-aeon' }]
}));
jest.mock('../components/ResonanceRitual', () => function MockResonanceRitual() { return <div data-testid="mock-ritual" />; });
jest.mock('../components/AeonAvatar', () => function MockAeonAvatar() { return <div data-testid="mock-avatar" />; });
jest.mock('../components/OnboardingWizard', () => function MockOnboardingWizard() { return <div data-testid="mock-onboarding" />; });
jest.mock('../components/ChatInterface', () => function MockChatInterface() { return <div data-testid="mock-chat" />; });
jest.mock('../components/SettingsModal', () => function MockSettingsModal() { return <div data-testid="mock-settings" />; });

// Mock fetch
global.fetch = jest.fn();

// Mock Tauri API
jest.mock('@tauri-apps/api/core', () => ({
  invoke: jest.fn().mockResolvedValue(true),
}));

describe('CockpitPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('renders loading state initially', async () => {
    // Setup fetch to hang
    (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    
    render(<CockpitPage />);
    
    // Check if the black screen is rendered (loading state)
    const loadingDiv = document.querySelector('.min-h-screen.bg-black');
    expect(loadingDiv).toBeInTheDocument();
  });

  it('enters shadow mode and exits on click', async () => {
    // Mock fetch based on URL
    (global.fetch as jest.Mock).mockImplementation(async (url: string) => {
      if (url.includes('51111/resonance/profile')) {
        return {
          ok: true,
          json: async () => ({ personality_archetype: 'Test Archetype', name: 'ZANA Test' })
        };
      }
      if (url.includes('51112/ai/forge/genome')) {
        return { ok: true };
      }
      return { ok: false };
    });

    // Enable shadow mode in local storage
    localStorage.setItem('shadow_mode', 'true');

    await act(async () => {
      render(<CockpitPage />);
    });

    await waitFor(() => {
      // Should show the shadow mode overlay text
      expect(screen.getByText(/Click para despertar/i)).toBeInTheDocument();
    });

    // Main UI should have opacity-0 pointer-events-none class because it's behind shadow mode
    // Wait, the main UI has these classes applied based on shadowMode state
    const mainSection = screen.getByText(/Tu Flota de Aeons/i).closest('.max-w-7xl');
    expect(mainSection).toHaveClass('opacity-0');
    expect(mainSection).toHaveClass('pointer-events-none');

    // Click the overlay to exit shadow mode
    const overlay = screen.getByText(/Click para despertar/i).closest('div');
    act(() => {
      fireEvent.click(overlay!);
    });

    // Should remove shadow mode overlay
    expect(screen.queryByText(/Click para despertar/i)).not.toBeInTheDocument();
    
    // Main UI should become visible
    expect(mainSection).toHaveClass('opacity-100');
    expect(mainSection).not.toHaveClass('opacity-0');
    expect(localStorage.getItem('shadow_mode')).toBe('false');
  });
});
