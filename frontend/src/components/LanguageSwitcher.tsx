import { Languages } from 'lucide-react';
import { LANGUAGES } from '../i18n/translations';
import { useLanguage } from '../i18n/LanguageContext';

export default function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage();

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <Languages size={14} style={{ color: 'var(--text-muted)' }} />
      <select
        className="select"
        value={language}
        onChange={(e) => setLanguage(e.target.value as typeof language)}
        style={{ fontSize: 12.5, padding: '4px 8px' }}
        aria-label="Language"
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>{l.nativeLabel}</option>
        ))}
      </select>
    </div>
  );
}
