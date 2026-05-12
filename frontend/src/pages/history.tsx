import { useState, Fragment } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageLayout } from "@/components/layout/page-layout";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { formatScore, getSentimentColor, getSentimentLabel, cn } from "@/lib/utils";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { ChevronDown, ChevronUp, Search, Filter } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
export default function History() {
  const [page, setPage] = useState(1);
  const [sentimentFilter, setSentimentFilter] = useState("");
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const { data, isLoading } = useQuery({
    queryKey: ["attendances", page, sentimentFilter],
    queryFn: () => api.listAttendances({ page, limit: 10, sentiment: sentimentFilter || undefined }),
  });
  const toggleRow = (id: number) => {
    const next = new Set(expandedRows);
    if (next.has(id)) next.delete(id); else next.add(id);
    setExpandedRows(next);
  };
  return (
    <PageLayout>
      <div className="space-y-6 pb-12">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Histórico</h1>
            <p className="text-muted-foreground">Acesse todas as análises realizadas e filtre por sentimento.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <select
                className="h-10 pl-9 pr-8 rounded-lg border border-white/10 bg-card text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                value={sentimentFilter}
                onChange={(e) => { setSentimentFilter(e.target.value); setPage(1); }}
              >
                <option value="">Todos Sentimentos</option>
                <option value="positive">Positivo</option>
                <option value="neutral">Neutro</option>
                <option value="negative">Negativo</option>
              </select>
            </div>
          </div>
        </div>
        <Card className="overflow-hidden">
          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="w-8 h-8 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
            </div>
          ) : !data || data.data.length === 0 ? (
            <div className="flex flex-col h-64 items-center justify-center text-muted-foreground space-y-3">
              <Search className="w-10 h-10 opacity-20" />
              <p>Nenhum atendimento encontrado.</p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader className="bg-black/40">
                  <TableRow>
                    <TableHead className="w-[80px]">ID</TableHead>
                    <TableHead>Data</TableHead>
                    <TableHead>Categoria</TableHead>
                    <TableHead>Sentimento</TableHead>
                    <TableHead className="text-right">Score</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.data.map((item) => (
                    <Fragment key={item.id}>
                      <TableRow
                        className={cn("cursor-pointer transition-colors group", expandedRows.has(item.id) && "bg-white/5")}
                        onClick={() => toggleRow(item.id)}
                      >
                        <TableCell className="font-mono text-muted-foreground">#{item.id}</TableCell>
                        <TableCell className="text-white">
                          {format(parseISO(item.created_at), "dd MMM yyyy, HH:mm", { locale: ptBR })}
                        </TableCell>
                        <TableCell>
                          <span className="bg-white/10 text-white/80 px-2.5 py-1 rounded-md text-xs font-medium border border-white/5">
                            {item.category}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className={cn("px-2.5 py-1 rounded-md text-xs font-medium border", getSentimentColor(item.sentiment))}>
                            {getSentimentLabel(item.sentiment)}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <span className="font-bold text-white bg-black/40 px-3 py-1 rounded-lg border border-white/5">
                            {formatScore(item.score)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground group-hover:text-white">
                            {expandedRows.has(item.id) ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </Button>
                        </TableCell>
                      </TableRow>
                      <AnimatePresence>
                        {expandedRows.has(item.id) && (
                          <TableRow className="bg-black/20 hover:bg-black/20 border-b border-white/5">
                            <TableCell colSpan={6} className="p-0">
                              <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: "auto", opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.2 }}
                                className="overflow-hidden"
                              >
                                <div className="p-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
                                  <div className="lg:col-span-1 space-y-3 border-r border-white/5 pr-6">
                                    <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Métricas</h4>
                                    {[
                                      { label: "Empatia", value: item.empathy },
                                      { label: "Clareza", value: item.clarity },
                                      { label: "Objetividade", value: item.objectivity },
                                      { label: "Resolutividade", value: item.resolutiveness },
                                    ].map((m) => (
                                      <div key={m.label} className="flex items-center justify-between text-sm">
                                        <span className="text-muted-foreground">{m.label}</span>
                                        <span className="text-white font-medium">{formatScore(m.value)}</span>
                                      </div>
                                    ))}
                                    <div className="pt-3 border-t border-white/5 flex items-center justify-between text-sm">
                                      <span className="text-muted-foreground">Tempo SLA</span>
                                      <span className="text-white font-medium">{item.sla_time_minutes}m</span>
                                    </div>
                                  </div>
                                  <div className="lg:col-span-3">
                                    <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">Resumo</h4>
                                    <p className="text-sm text-white/80 leading-relaxed bg-white/5 p-4 rounded-xl border border-white/5">
                                      {item.summary}
                                    </p>
                                  </div>
                                </div>
                              </motion.div>
                            </TableCell>
                          </TableRow>
                        )}
                      </AnimatePresence>
                    </Fragment>
                  ))}
                </TableBody>
              </Table>
              <div className="p-4 border-t border-white/5 flex items-center justify-between bg-black/20">
                <p className="text-sm text-muted-foreground">
                  Página <span className="font-medium text-white">{data.page}</span> de <span className="font-medium text-white">{data.totalPages}</span>
                  {" "}• Total: {data.total}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button>
                  <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)} disabled={page >= data.totalPages}>Próxima</Button>
                </div>
              </div>
            </>
          )}
        </Card>
      </div>
    </PageLayout>
  );
}