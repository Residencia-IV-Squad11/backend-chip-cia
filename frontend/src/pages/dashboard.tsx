import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageLayout } from "@/components/layout/page-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Activity, Clock, Target, TrendingUp } from "lucide-react";
import { motion } from "framer-motion";
import { cn, formatScore, getSentimentColor, getSentimentLabel } from "@/lib/utils";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};
const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};
export default function Dashboard() {
  const { data: overview, isLoading, error } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: api.getDashboardOverview,
  });
  if (isLoading) {
    return (
      <PageLayout>
        <div className="flex h-[60vh] items-center justify-center">
          <div className="w-12 h-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
        </div>
      </PageLayout>
    );
  }
  if (error || !overview) {
    return (
      <PageLayout>
        <div className="flex h-[60vh] items-center justify-center flex-col text-center space-y-4">
          <div className="w-16 h-16 bg-destructive/10 text-destructive rounded-2xl flex items-center justify-center">
            <Activity className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold">Erro ao carregar dashboard</h2>
          <p className="text-muted-foreground max-w-md">Não foi possível conectar com a API. Verifique se o backend está rodando.</p>
        </div>
      </PageLayout>
    );
  }
  const pieData = [
    { name: "Positivo", value: overview.sentimentDistribution.positive, color: "hsl(142, 71%, 45%)" },
    { name: "Neutro", value: overview.sentimentDistribution.neutral, color: "hsl(0, 0%, 50%)" },
    { name: "Negativo", value: overview.sentimentDistribution.negative, color: "hsl(357, 93%, 47%)" },
  ];
  return (
    <PageLayout>
      <div className="space-y-8 pb-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Visão Geral</h1>
          <p className="text-muted-foreground">Acompanhe a qualidade dos atendimentos da Chip & Cia em tempo real.</p>
        </div>
        <motion.div variants={containerVariants} initial="hidden" animate="show" className="grid gap-6 md:grid-cols-3">
          <motion.div variants={itemVariants}>
            <Card className="relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <CardContent className="p-6">
                <div className="flex items-center justify-between pb-2">
                  <p className="text-sm font-medium text-muted-foreground">Total de Atendimentos</p>
                  <Activity className="h-4 w-4 text-primary" />
                </div>
                <h2 className="text-4xl font-bold text-white">{overview.totalAttendances}</h2>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div variants={itemVariants}>
            <Card className="relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <CardContent className="p-6">
                <div className="flex items-center justify-between pb-2">
                  <p className="text-sm font-medium text-muted-foreground">Score Médio Geral</p>
                  <Target className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="flex items-baseline space-x-2">
                  <h2 className="text-4xl font-bold text-white">{formatScore(overview.averageScore)}</h2>
                  <span className="text-sm text-muted-foreground">/ 10</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div variants={itemVariants}>
            <Card className="relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <CardContent className="p-6">
                <div className="flex items-center justify-between pb-2">
                  <p className="text-sm font-medium text-muted-foreground">Tempo Médio SLA</p>
                  <Clock className="h-4 w-4 text-blue-400" />
                </div>
                <div className="flex items-baseline space-x-2">
                  <h2 className="text-4xl font-bold text-white">{overview.averageSlaMinutes}</h2>
                  <span className="text-sm text-muted-foreground">minutos</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
        <div className="grid gap-6 md:grid-cols-7">
          <Card className="md:col-span-4 flex flex-col">
            <CardHeader>
              <CardTitle>Evolução de Qualidade</CardTitle>
              <CardDescription>Métricas ao longo do tempo</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 min-h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={overview.qualityMetricsTrend} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false}
                    tickFormatter={(val) => { try { return format(parseISO(val), "dd MMM", { locale: ptBR }) } catch { return val } }}
                  />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} domain={[0, 10]} />
                  <RechartsTooltip
                    contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", borderRadius: "12px", color: "#fff" }}
                    itemStyle={{ color: "#fff" }}
                    labelFormatter={(val) => { try { return format(parseISO(val as string), "dd 'de' MMMM", { locale: ptBR }) } catch { return val } }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: "12px" }} />
                  <Line type="monotone" name="Resolutividade" dataKey="resolutiveness" stroke="hsl(var(--primary))" strokeWidth={3} dot={{ r: 4, fill: "hsl(var(--primary))", strokeWidth: 0 }} activeDot={{ r: 6 }} />
                  <Line type="monotone" name="Empatia" dataKey="empathy" stroke="hsl(142, 71%, 45%)" strokeWidth={2} dot={false} />
                  <Line type="monotone" name="Clareza" dataKey="clarity" stroke="hsl(217, 91%, 60%)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card className="md:col-span-3 flex flex-col">
            <CardHeader>
              <CardTitle>Sentimento do Cliente</CardTitle>
              <CardDescription>Distribuição geral das interações</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 min-h-[300px] flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={70} outerRadius={100} paddingAngle={5} dataKey="value" stroke="none">
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", borderRadius: "12px", color: "#fff" }} itemStyle={{ color: "#fff" }} />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Últimas Análises</CardTitle>
              <CardDescription>Atendimentos processados recentemente</CardDescription>
            </div>
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {overview.recentAttendances.map((item) => (
                <div key={item.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl border border-white/5 bg-background/30 hover:bg-white/5 transition-colors gap-4">
                  <div className="flex flex-col space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white truncate">Ticket #{item.id}</span>
                      <span className="text-xs text-muted-foreground px-2 py-0.5 rounded bg-white/10">{item.category}</span>
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-1">{item.summary}</p>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <div className="flex flex-col items-end">
                      <div className="text-sm font-medium">Score: <span className="text-white">{formatScore(item.score)}</span></div>
                      <span className={cn("text-xs font-medium px-2 py-1 rounded-md border mt-1", getSentimentColor(item.sentiment))}>
                        {getSentimentLabel(item.sentiment)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
              {overview.recentAttendances.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">Nenhuma análise recente encontrada.</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}