import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type AnalysisResult } from "@/lib/api";
import { PageLayout } from "@/components/layout/page-layout";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, Sparkles, AlertCircle, ArrowRight, CheckCircle2 } from "lucide-react";
import { formatScore, getSentimentColor, getSentimentLabel, cn } from "@/lib/utils";
export default function NewAnalysis() {
  const [transcript, setTranscript] = useState("");
  const [category, setCategory] = useState("");
  const mutation = useMutation<AnalysisResult, Error, { transcript: string; category?: string }>({
    mutationFn: api.analyzeAttendance,
  });
  const handleAnalyze = () => {
    if (!transcript.trim()) return;
    mutation.mutate({ transcript, category: category || "Geral" });
  };
  const handleReset = () => {
    setTranscript("");
    setCategory("");
    mutation.reset();
  };
  const result = mutation.data;
  const isPending = mutation.isPending;
  return (
    <PageLayout>
      <div className="max-w-4xl mx-auto space-y-8 pb-12">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
            Nova Análise IA <Sparkles className="w-6 h-6 text-primary" />
          </h1>
          <p className="text-muted-foreground">Cole o transcrito do atendimento para avaliar empatia, clareza e resolutividade.</p>
        </div>
        <AnimatePresence mode="wait">
          {!result && !isPending && (
            <motion.div key="input-form" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="space-y-6">
              <Card className="border-primary/20 shadow-[0_0_30px_-10px_rgba(229,9,20,0.1)]">
                <CardHeader><CardTitle>Dados do Atendimento</CardTitle></CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="category" className="text-muted-foreground">Categoria (Opcional)</Label>
                    <Input id="category" placeholder="Ex: Suporte Técnico, Vendas, Retenção" value={category} onChange={(e) => setCategory(e.target.value)} className="bg-black/50" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="transcript" className="text-muted-foreground">Transcrito Completo <span className="text-primary">*</span></Label>
                    <Textarea id="transcript" placeholder={"[Operador]: Olá, bom dia. Em que posso ajudar?\n[Cliente]: Minha internet está caindo muito..."} className="min-h-[300px] font-mono text-sm bg-black/50 leading-relaxed" value={transcript} onChange={(e) => setTranscript(e.target.value)} />
                  </div>
                </CardContent>
                <CardFooter className="bg-white/5 border-t border-white/5 px-6 py-4 flex justify-end">
                  <Button size="lg" onClick={handleAnalyze} disabled={!transcript.trim()} className="font-bold tracking-wide">
                    Analisar com IA <ArrowRight className="ml-2 w-5 h-5" />
                  </Button>
                </CardFooter>
              </Card>
            </motion.div>
          )}
          {isPending && (
            <motion.div key="loading" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 1.1 }} className="flex flex-col items-center justify-center py-32 space-y-8">
              <div className="relative w-32 h-32 flex items-center justify-center">
                <div className="absolute inset-0 rounded-full border-t-2 border-primary/80 animate-[spin_2s_linear_infinite]" />
                <div className="absolute inset-2 rounded-full border-r-2 border-primary/50 animate-[spin_3s_linear_infinite_reverse]" />
                <div className="absolute inset-4 rounded-full border-b-2 border-primary/30 animate-[spin_1.5s_linear_infinite]" />
                <div className="absolute inset-0 rounded-full bg-primary/10 animate-pulse blur-xl" />
                <Bot className="w-10 h-10 text-primary animate-pulse relative z-10" />
              </div>
              <div className="text-center space-y-2">
                <p className="text-primary tracking-[0.2em] uppercase text-sm animate-pulse font-bold">Processando IA</p>
                <p className="text-muted-foreground text-sm max-w-xs mx-auto">Analisando sentimento, extraindo métricas e gerando resumo...</p>
              </div>
            </motion.div>
          )}
          {result && (
            <motion.div key="result" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
              <div className="flex items-center justify-between bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-xl text-emerald-400">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-6 h-6" />
                  <span className="font-medium">Análise concluída com sucesso!</span>
                </div>
                <Button variant="outline" size="sm" onClick={handleReset} className="text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10">Nova Análise</Button>
              </div>
              <div className="grid gap-6 md:grid-cols-3">
                <Card className="md:col-span-1 bg-gradient-to-b from-card to-background border-t-4 border-t-primary">
                  <CardContent className="pt-6 flex flex-col items-center text-center space-y-4">
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground uppercase tracking-wider font-semibold">Score Geral</p>
                      <div className="text-6xl font-bold text-white">{formatScore(result.score)}</div>
                    </div>
                    <div className="w-full pt-4 border-t border-white/10 space-y-3">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">Sentimento</span>
                        <span className={cn("px-2.5 py-1 rounded-md font-medium border", getSentimentColor(result.sentiment))}>
                          {getSentimentLabel(result.sentiment)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">Categoria</span>
                        <span className="text-white font-medium">{result.category}</span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">SLA</span>
                        <span className="text-white font-medium">{result.sla_time_minutes} min</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="md:col-span-2">
                  <CardHeader><CardTitle className="text-lg">Métricas Detalhadas</CardTitle></CardHeader>
                  <CardContent className="space-y-6">
                    {[
                      { label: "Empatia", value: result.empathy, color: "bg-blue-500" },
                      { label: "Clareza", value: result.clarity, color: "bg-purple-500" },
                      { label: "Objetividade", value: result.objectivity, color: "bg-amber-500" },
                      { label: "Resolutividade", value: result.resolutiveness, color: "bg-primary" },
                    ].map((metric) => (
                      <div key={metric.label} className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="font-medium text-white">{metric.label}</span>
                          <span className="text-muted-foreground">{formatScore(metric.value)}/10</span>
                        </div>
                        <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${(metric.value / 10) * 100}%` }} transition={{ duration: 1, delay: 0.2 }} className={cn("h-full rounded-full", metric.color)} />
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
              <Card>
                <CardHeader><CardTitle className="text-lg">Resumo Executivo</CardTitle></CardHeader>
                <CardContent>
                  <p className="text-muted-foreground leading-relaxed">{result.summary}</p>
                </CardContent>
              </Card>
            </motion.div>
          )}
          {mutation.isError && (
            <div className="bg-destructive/10 border border-destructive/20 p-6 rounded-xl flex items-start gap-4 text-destructive">
              <AlertCircle className="w-6 h-6 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-bold text-lg mb-1">Falha na Análise</h3>
                <p className="opacity-90">{mutation.error?.message || "Erro desconhecido."}</p>
                <Button variant="outline" className="mt-4 border-destructive/30 text-destructive hover:bg-destructive/10" onClick={handleReset}>Tentar Novamente</Button>
              </div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </PageLayout>
  );
}