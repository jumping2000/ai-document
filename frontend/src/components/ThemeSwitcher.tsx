import { useState, useRef, useEffect } from 'react';
import { Sun, Moon, Monitor, ChevronDown } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import type { Theme } from '../contexts/ThemeContext';

const options: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Chiaro', icon: Sun },
  { value: 'dark', label: 'Scuro', icon: Moon },
  { value: 'system', label: 'Sistema', icon: Monitor },
];

export default function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = options.find(o => o.value === theme) ?? options[2];
  const Icon = current.icon;

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
        aria-label="Cambia tema"
      >
        <Icon size={14} />
        <ChevronDown size={10} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-36 py-1 rounded-xl
                        bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700
                        shadow-lg dark:shadow-black/40 z-50">
          {options.map(({ value, label, icon: OptionIcon }) => (
            <button
              key={value}
              onClick={() => { setTheme(value); setOpen(false); }}
              className={`
                w-full flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors
                ${theme === value
                  ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10'
                  : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'}
              `}
            >
              <OptionIcon size={13} />
              {label}
              {theme === value && <span className="ml-auto text-[10px]">●</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}