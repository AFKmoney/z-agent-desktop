import { Languages } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Lang } from "@/lib/i18n";

interface LanguageSelectorProps {
  currentLang: Lang;
  onLanguageChange: (lang: Lang) => void;
}

const LANGUAGES: Record<Lang, string> = {
  en: "English",
  fr: "Français",
  es: "Español",
  de: "Deutsch",
  pt: "Português",
};

export function LanguageSelector({ currentLang, onLanguageChange }: LanguageSelectorProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5 font-mono text-xs" title="Switch language">
          <Languages className="w-4 h-4" />
          {currentLang.toUpperCase()}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {(Object.entries(LANGUAGES) as [Lang, string][]).map(([code, name]) => (
          <DropdownMenuItem
            key={code}
            onClick={() => onLanguageChange(code)}
            className={currentLang === code ? "bg-accent" : ""}
          >
            <span className="font-mono text-xs w-6">{code.toUpperCase()}</span>
            <span>{name}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}