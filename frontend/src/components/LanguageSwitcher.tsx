import { useState, useRef, useEffect } from 'react';
import { Globe, ChevronDown } from 'lucide-react';
import { useTranslation } from '../i18n/LanguageContext';
import type { Locale } from '../i18n/translations';

const languages: { value: Locale; label: string; flag: string }[] = [
  { value: 'it', label: 'Italiano', flag: '🇮🇹' },
  { value: 'en', label: 'English', flag: '🇬🇧' },
];

export default function LanguageSwitcher() {
  const { locale, setLocale } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = languages.find(l => l.value === locale) ?? languages[0];

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg
                   bg-zinc-200 dark:bg-zinc-800 hover:bg-zinc-300 dark:hover:bg-zinc-700
                   text-zinc-700 dark:text-zinc-300 transition-colors"
        aria-label="Cambia lingua"
      >
        <span className="text-sm">{current.flag}</span>
        <span className="text-xs font-medium hidden sm:inline">{current.value.toUpperCase()}</span>
        <ChevronDown size={10} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-36 py-1 rounded-xl
                        bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700
                        shadow-lg dark:shadow-black/40 z-50">
          {languages.map(({ value, label, flag }) => (
            <button
              key={value}
              onClick={() => { setLocale(value); setOpen(false); }}
              className={`
                w-full flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors
                ${locale === value
                  ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10'
                  : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'}
              `}
            >
              <span className="text-base">{flag}</span>
              {label}
              {locale === value && <span className="ml-auto text-[10px]">●</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
