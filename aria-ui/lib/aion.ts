/**
 * AION: Artificial Intelligence Ontological Notation (Frontend Implementation)
 * Standardizes communication between Aeons and ZANA Mother.
 */

export interface AionMessage {
  aeonId: string;
  timestamp: number;
  latentState: number[];    // 384d embedding
  innovationScore: number;  // Mahalanobis distance from Kalman
  emlRecipe?: string;       // Exact math formula
  intent: 'SENSE' | 'EVOLVE' | 'ACT';
}

export const generateResonancePulse = (aeonId: string, state: number[]): AionMessage => {
  return {
    aeonId,
    timestamp: Date.now(),
    latentState: state,
    innovationScore: Math.random() * 2, // Mock innovation for visual pulse
    intent: 'SENSE'
  };
};

export const parseAionResonance = (msg: AionMessage): string => {
  if (msg.innovationScore > 1.5) {
    return `🚨 INNOVATION DETECTED: Aeon ${msg.aeonId} is expanding context.`;
  }
  return `✅ RESONANCE STABLE: Aeon ${msg.aeonId} is in synchrony.`;
};
