const BASE = "/api";

// Função base mantida
async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `HTTP ${res.status}`);
  }
  return res.json();
}

// Interfaces mantidas (O React não vai quebrar)
export interface Attendance {
  id: number;
  category: string;
  sentiment: "positive" | "neutral" | "negative";
  score: number;
  empathy: number;
  clarity: number;
  objectivity: number;
  resolutiveness: number;
  summary: string;
  sla_time_minutes: number;
  created_at: string;
}

export interface AttendanceListResponse {
  data: Attendance[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface DashboardOverview {
  totalAttendances: number;
  averageScore: number;
  averageSlaMinutes: number; // *O backend não tem isso ainda, deixei como 0
  sentimentDistribution: { positive: number; neutral: number; negative: number };
  qualityMetricsTrend: { date: string; empathy: number; clarity: number; objectivity: number; resolutiveness: number }[];
  recentAttendances: Attendance[];
}

export interface AnalysisResult extends Attendance {}

export const api = {
  // 1. TRADUÇÃO DO DASHBOARD (Mapeando do Português para o Inglês)
  getDashboardOverview: async (): Promise<DashboardOverview> => {
    // O backend retorna { sucesso: true, dados: { ... } }
    const response: any = await apiFetch("/dashboard/resumo");
    const dados = response.dados || {};

    // Traduz a lista do banco para o formato de objeto que o React espera
    const sentimentos = { positive: 0, neutral: 0, negative: 0 };
    if (dados.distribuicao_sentimento) {
      dados.distribuicao_sentimento.forEach((item: any) => {
        if (item.sentimento.toLowerCase() === 'positivo') sentimentos.positive = item.total;
        if (item.sentimento.toLowerCase() === 'neutro') sentimentos.neutral = item.total;
        if (item.sentimento.toLowerCase() === 'negativo') sentimentos.negative = item.total;
      });
    }

    // Traduz a evolução de score
    const trend = (dados.evolucao_score_diaria || []).map((item: any) => ({
      date: item.data,
      empathy: item.media_score, // Usando media_score como base provisória
      clarity: item.media_score,
      objectivity: item.media_score,
      resolutiveness: item.media_score
    }));

    return {
      totalAttendances: dados.total_atendimentos || 0,
      averageScore: dados.media_score_final || 0,
      averageSlaMinutes: 0, // Pode ser implementado no backend futuramente
      sentimentDistribution: sentimentos,
      qualityMetricsTrend: trend,
      recentAttendances: [] // Deixado vazio ou pode ser preenchido chamando a rota de listar
    };
  },

  // 2. TRADUÇÃO DA LISTAGEM
  listAttendances: async (params: { page?: number; limit?: number; sentiment?: string }): Promise<AttendanceListResponse> => {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.limit) q.set("per_page", String(params.limit));
    
    const qs = q.toString();
    const response: any = await apiFetch(`/atendimento/listar${qs ? `?${qs}` : ""}`);
    
    // 👇 AQUI ESTÁ A CORREÇÃO: Traduzindo o sentimento antes de desenhar a tela
    const atendimentosTraduzidos = (response.atendimentos || []).map((item: any) => {
      // Tradutor de Sentimento
      let sentimentoTraduzido = "neutral";
      if (item.sentimento) {
        const s = item.sentimento.toLowerCase();
        if (s === "positivo") sentimentoTraduzido = "positive";
        else if (s === "negativo") sentimentoTraduzido = "negative";
      }

      return {
        id: item.idatendimento || item.id,
        category: item.categoria || "N/A",
        sentiment: sentimentoTraduzido, // 👈 Recebe a palavra já traduzida
        score: item.score_final || 0,
        summary: item.resumo || "",
        created_at: item.data_criacao || new Date().toISOString(), 
        empathy: item.empatia || 0,
        clarity: item.clareza || 0,
        objectivity: item.objetividade || 0,
        resolutiveness: item.resolutividade || 0,
        sla_time_minutes: 0
      };
    });

    return {
      data: atendimentosTraduzidos,
      total: response.total || 0,
      page: response.pagina || 1,
      limit: params.limit || 20,
      totalPages: response.paginas || 1
    };
  },

  // 3. TRADUÇÃO DA ANÁLISE (Enviando 'texto_conversa' em vez de 'transcript')
  analyzeAttendance: async (body: { transcript: string; category?: string }): Promise<AnalysisResult> => {
    // 1. Manda a IA avaliar
    const response: any = await apiFetch("/atendimento/avaliar", { 
      method: "POST", 
      body: JSON.stringify({ texto_conversa: body.transcript }) 
    });
    
    // 2. Se salvou no banco, busca os detalhes completos usando o ID retornado
    if (response.sucesso && response.atendimento_id) {
      const detalhe: any = await apiFetch(`/atendimento/${response.atendimento_id}`);
      const dados = detalhe.dados;
      
      const classificacao = dados?.classificacao || {};
      const qualidade = dados?.qualidade || {};

      let sentimentoTraduzido = "neutral";
      if (classificacao.sentimento) {
        const s = classificacao.sentimento.toLowerCase();
        if (s === "positivo") sentimentoTraduzido = "positive";
        else if (s === "negativo") sentimentoTraduzido = "negative";
      }

      // 3. Traduz os dados do banco para a tela do React
      return {
        id: dados?.id || response?.atendimento_id || 0,
        category: classificacao.categoria || "N/A",
        sentiment: sentimentoTraduzido,
        summary: dados?.resumo || "Resumo não disponível.",
        score: qualidade.score_final || response?.score_final || 0,
        empathy: qualidade.empatia || 0,
        clarity: qualidade.clareza || 0,
        objectivity: qualidade.objetividade || 0,
        resolutiveness: qualidade.resolutividade || 0,
        sla_time_minutes: 0,
        created_at: dados?.data_criacao || new Date().toISOString()
      } as AnalysisResult;
    }
    
    return response;
  },
};