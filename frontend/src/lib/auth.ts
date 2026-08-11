import type { BYOKConfig } from '../types';

const STORAGE_KEY = 'gris_byok_config_v2';

export const DEFAULT_BYOK_CONFIG: BYOKConfig = {
  provider: 'openai',
  apiKey: 'sk-proj-byok-keyring-saved',
  modelName: 'gpt-4o',
  baseUrl: 'https://api.openai.com/v1',
  isKeyringSaved: true,
  exportDirectory: 'C:\\Users\\Chethan\\Desktop\\GitReverse_Exports',
  enableSdgAttribution: true,
  theme: 'dark',
};

export class AuthKeyring {
  static getConfig(): BYOKConfig {
    if (typeof window === 'undefined') return DEFAULT_BYOK_CONFIG;
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // Fallback
    }
    return DEFAULT_BYOK_CONFIG;
  }

  static saveConfig(config: Partial<BYOKConfig>): BYOKConfig {
    const current = this.getConfig();
    const updated = { ...current, ...config, isKeyringSaved: true };
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      } catch {
        // Storage error handle
      }
    }
    return updated;
  }

  static getAuthHeaders(): Record<string, string> {
    const config = this.getConfig();
    return {
      'X-GRIS-Provider': config.provider,
      'X-GRIS-Model': config.modelName,
      'Authorization': config.apiKey ? `Bearer ${config.apiKey}` : '',
    };
  }
}
