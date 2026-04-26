/**
 * Koru Genome: The digital blueprint of an Aeon.
 */
export interface AeonGenome {
  id: string;
  name: string;
  resonance_profile: {
    enneagram: string;
    big_five: Record<string, number>;
    kegan_stage: number;
    interpretation: string; // The human-readable meaning of the test
  };
  traits: string[];
  stats: {
    focus: number;    // Focus/Energy (0-1)
    resonance: number; // Bond level (0-1)
    evolution: number; // Progress level (0-100)
    hunger: number;    // Data hunger / needing new input (0-1)
  };
  visual_dna: AeonVisualDNA;
  virtual_space: VirtualSpace;
}

/**
 * Generative Visual DNA for the Aeon Avatar
 */
export interface AeonVisualDNA {
  base_model_index: number; // 0-999
  mutation_factor: number;  // 0-1
  chroma_spectrum: string[]; // Hex colors
  vibration_frequency: number; // 0.1 - 5.0
  particle_density: number; // 100 - 10000
  scale: number;
  geometry_type: 'fluid' | 'geometric' | 'crystal' | 'ethereal' | 'organic';
}

/**
 * Virtual Space for the Aeon
 */
export interface VirtualSpace {
  id: string;
  theme: 'zen' | 'cyber' | 'void' | 'nebula' | 'crystal' | 'forest' | 'forge' | 'shrine' | 'oasis' | 'abyss';
  accents: string[];
  ambient_audio_url?: string;
}

/**
 * Common communication protocols
 */
export type InteractionType = 'thought' | 'action' | 'observation' | 'reflection' | 'message';

export interface SovereignPacket {
  id: string;
  aeon_id: string;
  type: InteractionType;
  content: unknown;
  timestamp: string;
}
