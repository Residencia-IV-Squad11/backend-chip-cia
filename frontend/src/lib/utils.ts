import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score: number): string {
  return Number(score).toFixed(1);
}

// 1. Vacina na Cor: Se vier vazio, retorna cinza (neutro)
export function getSentimentColor(sentiment?: string): string {
  if (!sentiment) return 'text-muted-foreground bg-muted/50 border-muted';

  switch (sentiment.toLowerCase()) {
    case 'positive':
      return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
    case 'negative':
      return 'text-primary bg-primary/10 border-primary/20';
    default:
      return 'text-muted-foreground bg-muted/50 border-muted';
  }
}

// 2. Vacina no Texto: Se vier vazio, retorna "Analisando..." ou "Neutro"
export function getSentimentLabel(sentiment?: string): string {
  if (!sentiment) return 'Neutro'; // Valor padrão seguro para não quebrar a tela

  switch (sentiment.toLowerCase()) {
    case 'positive': return 'Positivo';
    case 'negative': return 'Negativo';
    case 'neutral': return 'Neutro';
    default: return sentiment;
  }
}