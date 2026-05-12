import { PageLayout } from "@/components/layout/page-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Save } from "lucide-react";

export default function Settings() {
  return (
    <PageLayout>
      <div className="max-w-2xl mx-auto space-y-8 pb-12">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight text-white mb-2">Configurações</h1>
          <p className="text-muted-foreground">Gerencie preferências de análise e da sua conta.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Parâmetros de IA</CardTitle>
            <CardDescription>Ajuste como a inteligência artificial avalia os atendimentos</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label className="text-white">Prompt Base do Sistema</Label>
              <Input value="Você é um auditor de qualidade de atendimento focado em telecomunicações..." disabled className="opacity-50" />
              <p className="text-xs text-muted-foreground">Apenas administradores podem alterar o prompt base.</p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-white">SLA Padrão (Minutos)</Label>
                <Input type="number" defaultValue={15} />
              </div>
              <div className="space-y-2">
                <Label className="text-white">Idioma Principal</Label>
                <select className="flex h-12 w-full rounded-xl border border-white/10 bg-background/50 px-4 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:border-primary/50">
                  <option value="pt-br">Português (BR)</option>
                  <option value="en">Inglês</option>
                  <option value="es">Espanhol</option>
                </select>
              </div>
            </div>

            <Button className="w-full sm:w-auto" variant="default">
              <Save className="w-4 h-4 mr-2" /> Salvar Alterações
            </Button>
          </CardContent>
        </Card>

        <Card className="border-destructive/20">
          <CardHeader>
            <CardTitle className="text-destructive">Zona de Perigo</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">Ações destrutivas que não podem ser desfeitas.</p>
            <Button variant="destructive" disabled>Limpar Histórico de Análises</Button>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}
