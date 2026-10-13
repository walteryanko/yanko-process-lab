# YCS ProcessLab Studio — guia rápido

Versão 0.1.0: base científica funcional, com limites documentados. Não é um
substituto completo do Aspen e não controla instalações físicas.

## Instalação Windows

Execute o Setup publicado junto ao commit verificado. A instalação é por usuário,
sem Python separado. O aplicativo usa o Microsoft Edge WebView2 e .NET do Windows;
esses pré-requisitos precisam estar disponíveis. Abra o atalho “YCS ProcessLab Studio”.
O executável ainda não tem assinatura comercial de código. Desinstalar preserva projetos.

Projetos e resultados: `%APPDATA%\YCS ProcessLab Studio`.
O log de diagnóstico fica em `processlab.log` nessa pasta. Os arquivos de projeto
terminam em `.processlab.json`; a cópia anterior é preservada em `.bak`.

## Primeira simulação

1. Abra **Tanque com PID** no explorador.
2. Clique em **Executar**. Os gráficos vêm do cálculo Python em malha fechada.
3. Clique em **Pausar**. O lote em andamento termina; nenhum novo lote é iniciado.
4. Na aba **Simulação**, observe temperatura, qualidade, entrada e tabela de estados.
5. Clique em **Salvar**, abra outro cenário e reabra seu projeto em **Meus projetos**.
6. **Exportar** grava o experimento completo na pasta `experiments`. O CSV dos
   gráficos também pode ser exportado pela aba Simulação.

Tempo `t` é simulado, em segundos. Tempo de cálculo é o tempo real do computador.
Lote controla quantos passos são calculados por atualização, não a física do modelo.

## Criar e conectar equipamentos

Use o botão de novo projeto; ele inicia um tanque simples executável. Arraste uma
unidade da paleta para posicioná-la ou clique para adicioná-la. As portas à esquerda
recebem material; as da direita enviam material. Portas douradas conectam energia.
Conecte todos os pontos obrigatórios e termine todas as saídas em um produto.
Use um divisor para ramificar, misturador para juntar. Reciclos não são suportados.

Clique numa unidade e edite suas propriedades. **Validar** verifica o modelo.
**Regime permanente** calcula as condições estacionárias e os resíduos de balanço.
Undo/redo restauram edições. Delete remove a unidade ou conexão selecionada.
Após editar, execute/restaure para aplicar a nova definição à simulação.

## PID e sensor virtual

Em **Controle**, selecione PID, configure Kp, Ki e Kd (tempo em segundos), referência
e equipamento controlado. PID mede temperatura; NMPC também pode usar qualidade
estimada. Os sinais químicos não são acessíveis ao controlador sem um observador.
Uma nova referência pode ser aplicada durante a execução e é registrada no manifesto.

Em **Sensores virtuais**, selecione EKF, UKF ou MHE. Configure ruído, atraso, perdas,
viés e frequência. Amostra química com período zero desliga o laboratório. Um período
10 e atraso 3 significa coleta a cada 10 passos e disponibilidade três passos depois.
Compare estados simulados e estimados na tabela; as incertezas são aproximações.

## Projetos científicos

PG usa o modelo original recuperado, não a variante TypeScript calibrada. EB usa
somente o R1 reconstruído: seus resultados não representam uma planta Aspen validada.
NMPC + UKF do tanque é um experimento novo, sem alegação de integração AIRE.
Consulte a aba Pesquisa e `RECOVERY.md` para as discrepâncias e o estado dos ativos.

## Execução pelo código

```sh
python -m pip install -r studio/requirements-core.lock
npm ci --prefix studio/ui
npm run build --prefix studio/ui
python studio/desktop.py --browser
```

Abra exatamente a URL impressa; o fragmento contém uma chave local temporária.
No Windows, instale `requirements-windows.lock` e execute `python studio/desktop.py`.
Para um experimento sem interface: `python studio/desktop.py --run projeto.json --output resultado.json`.
Para repetir também as mudanças de referência feitas durante uma sessão exportada:
`python studio/desktop.py --replay resultado.json --output replay.json`.
Os testes ficam em `studio/tests`; no shell defina `PYTHONPATH=studio` antes de rodá-los.
