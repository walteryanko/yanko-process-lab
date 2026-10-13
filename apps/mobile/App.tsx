import React, {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  useWindowDimensions,
  KeyboardAvoidingView,
  Platform,
  Linking,
} from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import * as DocumentPicker from "expo-document-picker";
import * as Sharing from "expo-sharing";
import { File, Paths } from "expo-file-system";
import { captureRef } from "react-native-view-shot";
import { session } from "./src/session";
import { C, T, Icon, Action, Note, NumberField, number } from "./src/ui";
import { FlowCanvas } from "./src/FlowCanvas";
import { Chart } from "./src/Chart";
import { listProjects, loadProject, removeProject } from "./src/storage";
import {
  newProject,
  importProject,
  exportProject,
  setNodeParameter,
} from "../../packages/scientific-core/project";
import {
  CATALOG,
  PARAM_UNITS,
  PARAM_LABELS,
} from "../../packages/scientific-core/flowsheet";
import { Engine, csv, metrics } from "../../packages/scientific-core/engine";
import {
  type ModelId,
  type Settings,
  type Project,
  type NodeKind,
  copy,
} from "../../packages/scientific-core/types";
import { runDeviceVerification } from "./src/verification";
const tabs = [
  ["plant", "vector-polyline", "Planta"],
  ["simulate", "play-circle-outline", "Simular"],
  ["control", "tune-variant", "Controle"],
  ["sensors", "radar", "Sensores"],
  ["experiments", "chart-box-outline", "Ensaios"],
];
const modelNames: Record<ModelId, string> = {
  "pg-original": "PG · original",
  "pg-calibrated": "PG · calibrado",
  "pg-table": "PG · tabela",
  "eb-reduced": "Etilbenzeno R1",
  flowsheet: "Planta livre",
};
const fail = (e: unknown) =>
  Alert.alert("ProcessLab", e instanceof Error ? e.message : String(e));
async function shareFile(name: string, data: string, mime: string) {
  const file = new File(Paths.cache, name);
  file.write(data);
  await Sharing.shareAsync(file.uri, { mimeType: mime, dialogTitle: name });
}
function Screen() {
  useSyncExternalStore(session.subscribe, session.snapshot);
  const { width, height } = useWindowDimensions(),
    landscape = width > height && width >= 600;
  const [sheet, setSheet] = useState<string | null>(null),
    [form, setForm] = useState<Settings>(
      copy(session.project.science.settings),
    ),
    [variable, setVariable] = useState(4),
    [rows, setRows] = useState<any[]>([]),
    [compare, setCompare] = useState<Engine | null>(null),
    [name, setName] = useState(""),
    [tutorial, setTutorial] = useState(-1),
    [showChart, setShowChart] = useState(true),
    [qa, setQa] = useState("");
  const root = useRef<View>(null),
    e = session.engine,
    m = e?.model,
    s = e?.last,
    p = session.project;
  const i = m ? Math.min(variable, m.names.length - 1) : 0;
  useEffect(() => {
    void session.initialize();
  }, []);
  useEffect(() => {
    const handle = (url: string | null) => {
      if (url?.includes("verify")) {
        setQa("Verificação no dispositivo…");
        void runDeviceVerification()
          .then((result) => {
            setQa(result.ok ? "VERIFIED_DEVICE_OK" : "VERIFICATION_FAILED");
            console.info("PROCESSLAB_QA_RESULT " + JSON.stringify(result));
          })
          .catch((err) => {
            setQa("VERIFICATION_FAILED");
            console.error(
              "PROCESSLAB_QA_RESULT " +
                JSON.stringify({ ok: false, error: String(err) }),
            );
          });
      }
    };
    void Linking.getInitialURL().then(handle);
    const sub = Linking.addEventListener("url", (event) => handle(event.url));
    return () => sub.remove();
  }, []);
  useEffect(() => {
    if (m && variable >= m.names.length) setVariable(m.ti);
  }, [p.id]);
  function open(which: string) {
    session.pause();
    setForm(copy(p.science.settings));
    setName(p.name);
    setSheet(which);
    if (which === "projects" || which === "compare")
      void listProjects().then(setRows).catch(fail);
  }
  async function create(id: ModelId, mode?: string) {
    try {
      await session.save();
      const np = newProject(id);
      if (mode === "pid") {
        np.science.settings.controller = "pid";
        np.science.settings.setpoint += 1;
      }
      if (mode === "ukf") np.science.settings.observer = "ukf";
      await session.replace(np);
      setVariable(4);
      setCompare(null);
      setSheet(null);
      if (tutorial === 0) setTutorial(1);
    } catch (err) {
      fail(err);
    }
  }
  function apply() {
    try {
      const restart =
        JSON.stringify(form.measurementIndices) !==
          JSON.stringify(p.science.settings.measurementIndices) ||
        form.initialOffset !== p.science.settings.initialOffset;
      const run = () => {
        session.configure(form);
        if (restart) session.reset();
        setSheet(null);
      };
      if (restart)
        Alert.alert(
          "Reiniciar observador?",
          "A mudança das medições ou do erro inicial reinicia o experimento.",
          [
            { text: "Cancelar" },
            {
              text: "Aplicar e reiniciar",
              onPress: () => {
                try {
                  run();
                } catch (err) {
                  fail(err);
                }
              },
            },
          ],
        );
      else run();
    } catch (err) {
      fail(err);
    }
  }
  const confirmReset = () =>
    Alert.alert(
      "Reiniciar experimento?",
      "O histórico atual será substituído. Salve uma cópia para comparar.",
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Reiniciar",
          style: "destructive",
          onPress: () => session.reset(),
        },
      ],
    );
  const card = (
    icon: string,
    title: string,
    sub: string,
    onPress: () => void,
    color = C.cyan,
  ) => (
    <Pressable
      key={title}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={title}
      style={({ pressed }) => [styles.homeCard, { opacity: pressed ? 0.7 : 1 }]}
    >
      <View style={[styles.iconTile, { backgroundColor: `${color}18` }]}>
        <Icon name={icon} size={29} color={color} />
      </View>
      <Text
        style={{
          color: C.text,
          fontSize: 16,
          fontWeight: "600",
          marginTop: 13,
        }}
      >
        {title}
      </Text>
      <Text style={{ color: C.muted, fontSize: 11, marginTop: 5 }}>{sub}</Text>
      <View style={{ position: "absolute", top: 18, right: 12 }}>
        <Icon name="arrow-top-right" size={17} color={C.muted} />
      </View>
    </Pressable>
  );
  const metricCards = () =>
    m && s ? (
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: 9, paddingVertical: 2 }}
      >
        {[m.ti, m.qi].map((j, k) => (
          <Pressable
            key={j}
            accessibilityRole="button"
            accessibilityLabel={`Variável ${m.names[j]}`}
            onPress={() => setVariable(j)}
            onLongPress={() =>
              Alert.alert(
                m.names[j],
                `Referência simulada: ${modelNames[p.model]}. Unidade ${m.units[j]}.\n${m.warning}`,
              )
            }
            style={[styles.metric, { borderColor: i === j ? C.cyan : C.line }]}
          >
            <View style={T.row}>
              <Icon
                name={k ? "flask-outline" : "thermometer"}
                color={k ? C.purple : C.cyan}
                size={18}
              />
              <Text style={T.label}>{m.names[j]}</Text>
              <Text style={{ marginLeft: "auto", color: C.muted }}>↗</Text>
            </View>
            <View style={[T.row, { alignItems: "baseline", marginTop: 6 }]}>
              <Text style={T.value}>{number(s.x[j], k ? 3 : 1)}</Text>
              <Text style={{ color: C.muted, fontSize: 11 }}>{m.units[j]}</Text>
            </View>
            <Text style={{ fontSize: 9, color: C.muted, marginTop: 4 }}>
              REFERÊNCIA SIMULADA
            </Text>
          </Pressable>
        ))}
        <View style={styles.metric}>
          <View style={T.row}>
            <Icon name="valve" color={C.green} size={18} />
            <Text style={T.label}>MV</Text>
          </View>
          <View style={[T.row, { alignItems: "baseline", marginTop: 6 }]}>
            <Text style={T.value}>{number(s.u, 1)}</Text>
          </View>
          <Text style={{ color: C.muted, fontSize: 11 }}>{m.inputUnit}</Text>
        </View>
      </ScrollView>
    ) : null;
  const chart = () =>
    m && e ? (
      <>
        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Text style={T.label}>TENDÊNCIAS</Text>
          <View style={T.row}>
            <Action
              compact
              icon="chevron-left"
              label="Variável anterior"
              onPress={() =>
                setVariable((i - 1 + m.names.length) % m.names.length)
              }
            />
            <Action
              compact
              icon="chevron-right"
              label="Próxima variável"
              onPress={() => setVariable((i + 1) % m.names.length)}
            />
            <Action
              compact
              icon="image-outline"
              label="Exportar imagem"
              onPress={() => {
                if (root.current)
                  void captureRef(root, { format: "png", quality: 1 })
                    .then((uri) =>
                      Sharing.shareAsync(uri, { mimeType: "image/png" }),
                    )
                    .catch(fail);
              }}
            />
          </View>
        </View>
        <Chart
          samples={e.history}
          model={m}
          index={i}
          height={landscape ? 135 : 170}
          showSetpoint={e.settings.controller !== "cascade"}
          showEstimate={e.settings.observer !== "off"}
          measurementIndices={e.settings.measurementIndices}
          compare={compare?.model.id === m.id ? compare.history : undefined}
        />
      </>
    ) : null;
  const properties = () => (
    <View style={{ gap: 12 }}>
      <View
        style={{
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Text style={T.section}>{session.selected || "Planta"}</Text>
        <Action
          compact
          icon="tune"
          label="Propriedades"
          onPress={() => open("properties")}
        />
      </View>
      <View style={T.row}>
        <Icon name="flask-outline" color={C.green} />
        <Text style={{ color: C.text, flex: 1, fontSize: 13 }}>
          {modelNames[p.model]}
        </Text>
      </View>
      <Text style={T.label}>
        {e?.settings.controller.toUpperCase() ?? "CONFIGURAR"} ·{" "}
        {e?.settings.observer.toUpperCase() ?? "—"}
      </Text>
      {m && s && (
        <>
          <Text style={T.value}>
            {number(s.x[m.ti], 2)}{" "}
            <Text style={{ fontSize: 12, color: C.muted }}>
              {m.units[m.ti]}
            </Text>
          </Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Ajustar setpoint"
            onPress={() => open("control")}
            style={[T.card, { padding: 12 }]}
          >
            <Text style={T.label}>SETPOINT</Text>
            <Text
              style={{
                fontSize: 20,
                color: C.green,
                fontVariant: ["tabular-nums"],
                marginTop: 6,
              }}
            >
              {number(e!.settings.setpoint, 3)}{" "}
              <Text style={{ fontSize: 11 }}>
                {e!.settings.controller === "cascade"
                  ? m.units[m.qi]
                  : m.units[m.ti]}
              </Text>
            </Text>
          </Pressable>
          <Text style={{ fontSize: 11, color: C.muted }}>{s.solver}</Text>
        </>
      )}
      <Action
        icon="content-save-outline"
        label="Salvar projeto"
        onPress={() =>
          void session
            .save()
            .then(() => {
              session.message = "Projeto salvo";
              session.publish();
            })
            .catch(fail)
        }
      />
    </View>
  );
  const transport = () => (
    <View style={styles.transport}>
      <View style={{ minWidth: 68 }}>
        <Text
          style={{
            color: C.green,
            fontSize: 17,
            fontVariant: ["tabular-nums"],
            fontWeight: "600",
          }}
          testID="simulation-time"
        >
          {number((s?.t ?? 0) / 60, 1)}
        </Text>
        <Text style={{ fontSize: 9, color: C.muted }}>min simulados</Text>
      </View>
      <Action compact icon="restart" label="Reiniciar" onPress={confirmReset} />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={
          session.running ? "Pausar simulação" : "Iniciar simulação"
        }
        testID="simulation-toggle"
        onPress={() => {
          if (session.running) session.pause();
          else session.start();
          if (tutorial === 1) setTutorial(2);
        }}
        style={{
          backgroundColor: C.cyan,
          width: 56,
          height: 48,
          borderRadius: 15,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Icon
          name={session.running ? "pause" : "play"}
          color={C.bg}
          size={30}
        />
      </Pressable>
      <Action
        compact
        icon="stop"
        label="Parar e salvar"
        onPress={() => {
          session.pause();
          void session.save();
        }}
      />
      <Action
        compact
        icon="lightning-bolt-outline"
        label="Perturbação"
        onPress={() => open("disturbance")}
        color={C.amber}
      />
      <Pressable
        onPress={() => {
          session.speed =
            session.speed === 1 ? 4 : session.speed === 4 ? 16 : 1;
          session.publish();
        }}
        accessibilityRole="button"
        accessibilityLabel="Velocidade da simulação"
        style={{
          minWidth: 48,
          minHeight: 48,
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Text style={{ color: C.muted, fontSize: 13 }}>{session.speed}×</Text>
      </Pressable>
    </View>
  );
  const home = (
    <ScrollView
      contentContainerStyle={{ padding: 20, paddingTop: 12, gap: 18 }}
    >
      <View style={{ paddingVertical: 20 }}>
        <Text style={[T.label, { color: C.cyan, marginBottom: 10 }]}>
          ENGENHARIA EM MOVIMENTO
        </Text>
        <Text
          style={{
            color: C.text,
            fontSize: 36,
            fontWeight: "700",
            letterSpacing: -1.5,
            lineHeight: 40,
          }}
        >
          Sua planta.{`\n`}Seu laboratório.
        </Text>
        <Text style={{ color: C.muted, fontSize: 13, marginTop: 12 }}>
          Simule. Observe. Controle.
        </Text>
      </View>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
        {card(
          "vector-polyline",
          "Nova planta",
          "Equipamentos conectados",
          () => void create("flowsheet"),
        )}
        {card(
          "flask-outline",
          "CSTR",
          "Propilenoglicol · 6 estados",
          () => void create("pg-original"),
          C.green,
        )}
        {card(
          "tune-variant",
          "Controle",
          "PID · cascata · NMPC",
          () => void create("pg-original", "pid"),
          C.amber,
        )}
        {card(
          "radar",
          "Sensor virtual",
          "EKF · UKF · incerteza",
          () => void create("pg-original", "ukf"),
          C.purple,
        )}
        {card(
          "chart-box-outline",
          "Experimentos",
          "PG · etilbenzeno · comparação",
          () => {
            session.tab = "experiments";
            session.publish();
          },
          C.cyan,
        )}
        {card(
          "folder-outline",
          "Projetos",
          "Salvos neste dispositivo",
          () => open("projects"),
          C.muted,
        )}
      </View>
      <Pressable
        onPress={() => {
          setTutorial(0);
          void create("pg-original");
        }}
        style={[T.card, T.row]}
        accessibilityRole="button"
        accessibilityLabel="Tutorial interativo"
      >
        <Icon name="gesture-tap" color={C.cyan} />
        <Text style={{ color: C.text, flex: 1 }}>
          Primeiro experimento · 3 toques
        </Text>
        <Icon name="arrow-right" color={C.muted} />
      </Pressable>
      <Text style={{ fontSize: 11, color: C.muted, textAlign: "center" }}>
        CPU local · sem cadastro · modo offline
      </Text>
    </ScrollView>
  );
  const controls = (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 15 }}>
      <Text style={T.title}>Control Studio</Text>
      <Text style={T.label}>
        ATUADOR · {m?.inputLabel} ({m?.inputUnit})
      </Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
        {(["manual", "pid", "cascade", "nmpc"] as const).map((c) => (
          <Action
            key={c}
            icon={
              c === "manual"
                ? "hand-back-right-outline"
                : c === "nmpc"
                  ? "chart-bell-curve-cumulative"
                  : "tune-variant"
            }
            label={c === "cascade" ? "Cascata" : c.toUpperCase()}
            active={p.science.settings.controller === c}
            disabled={
              c === "cascade" && ["eb-reduced", "flowsheet"].includes(p.model)
            }
            onPress={() => {
              try {
                session.pause();
                session.configure({
                  controller: c,
                  setpoint: c === "cascade" ? m!.x0[m!.qi] : m!.x0[m!.ti],
                });
              } catch (err) {
                fail(err);
              }
            }}
          />
        ))}
      </View>
      {properties()}
      <Action
        icon="tune"
        label="Ajustar parâmetros"
        onPress={() => open("control")}
      />
      {p.science.settings.controller === "nmpc" && (
        <Note>
          Busca preditiva limitada, com restrição térmica e retenção da última
          entrada em falha. Não há garantia de robustez.
        </Note>
      )}
      <Note color={C.muted}>
        MPC linear e MHE indisponíveis nesta build. Cascata: concentração
        estimada → temperatura medida.
      </Note>
      {metricCards()}
      {chart()}
    </ScrollView>
  );
  const sensors = (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 15 }}>
      <Text style={T.title}>Sensor virtual</Text>
      <Text style={T.label}>MEDIÇÕES → ESTIMADOR → CONCENTRAÇÃO</Text>
      <View style={[T.card, T.row, { justifyContent: "space-around" }]}>
        <Icon name="thermometer" color={C.amber} size={34} />
        <Icon name="arrow-right" size={18} color={C.muted} />
        <Icon name="radar" color={C.purple} size={40} />
        <Icon name="arrow-right" size={18} color={C.muted} />
        <Icon name="flask-outline" color={C.cyan} size={34} />
      </View>
      <View style={T.row}>
        {(["off", "ekf", "ukf"] as const).map((o) => (
          <Action
            key={o}
            label={o === "off" ? "Desligado" : o.toUpperCase()}
            icon={o === "off" ? "power" : "radar"}
            active={p.science.settings.observer === o}
            onPress={() => {
              try {
                session.pause();
                session.configure({ observer: o });
                setVariable(m!.qi);
              } catch (err) {
                fail(err);
              }
            }}
          />
        ))}
      </View>
      {m && s && (
        <View style={T.card}>
          <Text style={T.label}>{m.names[m.qi]} · ESTIMATIVA</Text>
          <Text style={[T.value, { color: C.purple, marginTop: 8 }]}>
            {p.science.settings.observer === "off"
              ? "Desligado"
              : number(s.estimate[m.qi], 4)}{" "}
            <Text style={{ fontSize: 12 }}>{m.units[m.qi]}</Text>
          </Text>
          <Text style={T.body}>
            ±2σ: {number(2 * s.sigma[m.qi], 4)} · covariância do filtro
          </Text>
        </View>
      )}
      <Action
        icon="tune"
        label="Ruído e medições"
        onPress={() => open("sensors")}
      />
      {chart()}
      <Note color={C.muted}>
        A referência simulada serve à avaliação. O filtro recebe apenas as
        medições e as entradas aplicadas. ±2σ não é garantia de cobertura.
      </Note>
    </ScrollView>
  );
  const experiments = (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
      <Text style={T.title}>Experiment Lab</Text>
      <View style={{ flexDirection: "row", gap: 10, flexWrap: "wrap" }}>
        {(Object.keys(modelNames) as ModelId[]).map((id) => (
          <Pressable
            key={id}
            accessibilityRole="button"
            onPress={() => void create(id)}
            style={[T.card, { minWidth: 140, flexGrow: 1, minHeight: 75 }]}
          >
            <Icon
              name={id === "eb-reduced" ? "molecule" : "flask-outline"}
              color={id === "eb-reduced" ? C.amber : C.green}
            />
            <Text style={{ color: C.text, marginTop: 7, fontSize: 12 }}>
              {modelNames[id]}
            </Text>
          </Pressable>
        ))}
      </View>
      {e && (
        <>
          <Text style={T.label}>EXECUÇÃO ATUAL · SEED {e.settings.seed}</Text>
          <View
            style={[
              T.card,
              { flexDirection: "row", flexWrap: "wrap", gap: 20 },
            ]}
          >
            {Object.entries(session.tab === "experiments" ? metrics(e) : {})
              .filter(([k, v]) =>
                [
                  "rmse",
                  "iae",
                  "itae",
                  "overshoot",
                  "settling",
                  "violations",
                  "computeMs",
                  "peakStepMs",
                ].includes(k),
              )
              .map(([key, v]) => (
                <View key={key} style={{ minWidth: 120 }}>
                  <Text style={T.label}>
                    {
                      (
                        {
                          rmse: "RMSE estimador",
                          iae: "IAE térmico",
                          itae: "ITAE térmico",
                          overshoot: "Sobressinal",
                          settling: "Acomodação (s)",
                          violations: "Violações",
                          computeMs: "Cálculo (ms)",
                          peakStepMs: "Pico/passo (ms)",
                        } as any
                      )[key]
                    }
                  </Text>
                  <Text
                    style={{
                      color: C.text,
                      fontSize: 19,
                      fontVariant: ["tabular-nums"],
                      marginTop: 6,
                    }}
                  >
                    {typeof v === "number" ? number(v, 3) : "—"}
                  </Text>
                </View>
              ))}
          </View>
          <View style={{ flexDirection: "row", flexWrap: "wrap" }}>
            <Action
              icon="content-copy"
              label="Salvar cópia"
              onPress={() => {
                const pp = copy(p);
                pp.id = `p-${Date.now()}`;
                pp.name = `${p.name} · cópia`;
                const ck = e.checkpoint();
                ck.project = pp;
                void session.replace(pp, ck).catch(fail);
              }}
            />
            <Action
              icon="chart-multiple"
              label="Comparar"
              onPress={() => open("compare")}
            />
            <Action
              icon="file-delimited-outline"
              label="CSV completo"
              onPress={() =>
                void shareFile(
                  "processlab-resultados.csv",
                  csv(e),
                  "text/csv",
                ).catch(fail)
              }
            />
            <Action
              icon="file-export-outline"
              label="Manifesto"
              onPress={() =>
                void shareFile(
                  "processlab-experimento.json",
                  JSON.stringify(
                    {
                      project: p,
                      checkpoint: e.checkpoint(),
                      metrics: metrics(e),
                    },
                    null,
                    2,
                  ),
                  "application/json",
                ).catch(fail)
              }
            />
          </View>
          {compare && (
            <Text style={T.body}>
              Comparação: {compare.project.name} · curva verde
            </Text>
          )}
          {chart()}
        </>
      )}
      <Note>{m?.warning ?? "Conecte e configure uma planta."}</Note>
      <Note color={C.muted}>
        AIRE: fonte auditada; não integrado. RSI: código ausente na branch
        inspecionada. Nenhum ganho recursivo alegado.
      </Note>
    </ScrollView>
  );
  const plant = (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Text style={T.section}>{modelNames[p.model]}</Text>
        <View style={T.row}>
          <Action
            compact
            icon="undo"
            label="Desfazer"
            onPress={() => session.undo()}
          />
          <Action
            compact
            icon="redo"
            label="Refazer"
            onPress={() => session.redo()}
          />
          {p.model === "flowsheet" && (
            <Action
              compact
              icon="plus"
              label="Adicionar equipamento"
              onPress={() => open("add")}
            />
          )}
        </View>
      </View>
      <FlowCanvas
        project={p}
        height={landscape ? Math.max(210, height - 165) : 235}
        onDetails={() => open("properties")}
      />
      {metricCards()}
      {session.tab === "simulate" && (
        <Action
          icon="timer-cog-outline"
          label="Duração e seed"
          onPress={() => open("simulation")}
        />
      )}
      <View
        style={{
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Text style={T.label}>SINAIS DO PROCESSO</Text>
        <Action
          compact
          icon={showChart ? "chevron-up" : "chevron-down"}
          label="Mostrar ou recolher gráfico"
          onPress={() => setShowChart(!showChart)}
        />
      </View>
      {showChart && chart()}
    </ScrollView>
  );
  const renderTab = () =>
    session.tab === "home"
      ? home
      : session.tab === "control"
        ? controls
        : session.tab === "sensors"
          ? sensors
          : session.tab === "experiments"
            ? experiments
            : plant;
  const sheetTitle: Record<string, string> = {
    control: "Controle",
    sensors: "Sensor virtual",
    simulation: "Experimento",
    disturbance: "Perturbação",
    properties: session.selected,
    projects: "Projetos locais",
    add: "Biblioteca de equipamentos",
    compare: "Comparar execuções",
  };
  const field = (key: keyof Settings, label: string, unit = "") => (
    <NumberField
      key={key}
      label={label}
      value={form[key] as number}
      unit={unit}
      onChange={(v) => setForm((x) => ({ ...x, [key]: v }))}
    />
  );
  const node = p.graph.nodes.find((n) => n.id === session.selected);
  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: C.bg }}
      edges={["top", "bottom", "left", "right"]}
    >
      <StatusBar style="light" />
      <View ref={root} collapsable={false} style={{ flex: 1 }}>
        <View style={styles.header}>
          <Pressable
            onPress={() => {
              session.tab = "home";
              session.publish();
            }}
            accessibilityRole="button"
            accessibilityLabel="Início"
            style={T.row}
          >
            <View style={styles.brand}>
              <Icon name="flask-outline" color={C.cyan} size={24} />
            </View>
            <View>
              <Text
                style={{
                  color: C.text,
                  fontSize: 17,
                  fontWeight: "700",
                  letterSpacing: 0.5,
                }}
              >
                YCS <Text style={{ fontWeight: "400" }}>PROCESSLAB</Text>
              </Text>
              <Text
                style={{
                  color: C.muted,
                  fontSize: 9,
                  letterSpacing: 1.5,
                  marginTop: 3,
                }}
              >
                LABORATÓRIO DE BOLSO
              </Text>
            </View>
          </Pressable>
          <View style={T.row}>
            <View
              style={{
                width: 6,
                height: 6,
                borderRadius: 3,
                backgroundColor: C.green,
              }}
            />
            <Text style={{ color: C.green, fontSize: 9 }}>LOCAL</Text>
            <Action
              compact
              icon="folder-outline"
              label="Abrir projetos"
              onPress={() => open("projects")}
            />
          </View>
        </View>
        {!!qa && (
          <Text accessibilityLabel={qa} style={{ color: C.cyan, padding: 8 }}>
            {qa}
          </Text>
        )}
        {!session.ready ? (
          <View style={{ padding: 24 }}>
            <Text style={T.body}>Abrindo laboratório…</Text>
          </View>
        ) : (
          <View
            style={{ flex: 1, flexDirection: landscape ? "row" : "column" }}
          >
            {landscape && session.tab !== "home" && (
              <View style={styles.rail}>
                {tabs.map(([id, icon, label]) => (
                  <Action
                    key={id}
                    icon={icon}
                    label={label}
                    active={session.tab === id}
                    onPress={() => {
                      session.tab = id;
                      session.publish();
                    }}
                  />
                ))}
              </View>
            )}
            <View style={{ flex: 1 }}>{renderTab()}</View>
            {landscape && ["plant", "simulate"].includes(session.tab) && (
              <ScrollView
                style={{
                  width: 235,
                  flexGrow: 0,
                  borderLeftWidth: 1,
                  borderColor: C.line,
                }}
                contentContainerStyle={{ padding: 15 }}
              >
                {properties()}
              </ScrollView>
            )}
          </View>
        )}
        {!!session.message && session.tab !== "home" && (
          <Pressable onPress={() => Alert.alert("Estado", session.message)}>
            <Text
              numberOfLines={1}
              style={{
                color: session.engine?.error ? C.red : C.amber,
                fontSize: 11,
                paddingHorizontal: 18,
                paddingVertical: 5,
              }}
            >
              {session.message}
            </Text>
          </Pressable>
        )}
        {tutorial >= 0 && (
          <View style={[T.card, T.row, { margin: 8, padding: 12 }]}>
            <Icon name="gesture-tap" color={C.cyan} />
            <Text style={{ color: C.text, flex: 1, fontSize: 12 }}>
              {tutorial === 0
                ? "1 · Abra o CSTR."
                : tutorial === 1
                  ? "1 · Toque em ▶ para calcular."
                  : tutorial === 2
                    ? "2 · Toque em ⚡ e aplique +2 K."
                    : "3 · Abra Sensores para ver a concentração estimada."}
            </Text>
            <Action
              compact
              icon="check"
              label="Concluir tutorial"
              onPress={() => setTutorial(-1)}
            />
          </View>
        )}
        {session.tab !== "home" && transport()}
        {!landscape && session.tab !== "home" && (
          <View style={styles.tabs}>
            {tabs.map(([id, icon, label]) => (
              <Action
                key={id}
                style={{ flex: 1, paddingHorizontal: 0 }}
                icon={icon}
                label={label}
                active={session.tab === id}
                onPress={() => {
                  session.tab = id;
                  if (id === "sensors" && m) setVariable(m.qi);
                  session.publish();
                }}
              />
            ))}
          </View>
        )}
      </View>
      <Modal
        visible={sheet !== null}
        transparent
        animationType="slide"
        onRequestClose={() => setSheet(null)}
        supportedOrientations={["portrait", "landscape"]}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={{
            flex: 1,
            justifyContent: "flex-end",
            backgroundColor: "#00000088",
          }}
        >
          <Pressable
            style={{ flex: 1, minHeight: 16 }}
            onPress={() => setSheet(null)}
            accessibilityLabel="Fechar painel"
          />
          <View
            style={[
              styles.sheet,
              {
                maxHeight: height * 0.9,
                width: landscape ? Math.min(640, width * 0.85) : "100%",
                alignSelf: "center",
              },
            ]}
          >
            <View
              style={{
                width: 36,
                height: 4,
                borderRadius: 2,
                backgroundColor: C.line,
                alignSelf: "center",
                marginTop: 10,
              }}
            />
            <View
              style={{
                flexDirection: "row",
                alignItems: "center",
                padding: 16,
                paddingBottom: 2,
              }}
            >
              <Text style={[T.title, { fontSize: 21, flex: 1 }]}>
                {sheetTitle[sheet ?? ""] ?? ""}
              </Text>
              <Action
                compact
                icon="close"
                label="Fechar"
                onPress={() => setSheet(null)}
              />
            </View>
            <ScrollView
              keyboardShouldPersistTaps="handled"
              contentContainerStyle={{
                padding: 18,
                gap: 15,
                paddingBottom: 34,
              }}
            >
              {sheet === "control" && (
                <>
                  <View style={styles.fields}>
                    {field(
                      "setpoint",
                      "Setpoint",
                      form.controller === "cascade"
                        ? m?.units[m.qi]
                        : m?.units[m?.ti ?? 0],
                    )}
                    {field("manual", "Manual", m?.inputUnit)}
                    {field("kp", "Kp", `${m?.inputUnit}/K`)}
                    {field("ki", "Ki", `${m?.inputUnit}/(K·s)`)}
                    {field("kd", "Kd", `${m?.inputUnit}·s/K`)}
                    {field("horizon", "Horizonte", "passos")}
                  </View>
                  <Note color={C.muted}>
                    PID: temperatura medida. Cascata: ganho externo 25
                    K/(kmol/m³), com PID interno. NMPC: 7 candidatos por passo.
                  </Note>
                  <Action icon="check" label="Aplicar" active onPress={apply} />
                </>
              )}
              {sheet === "sensors" && (
                <>
                  <Text style={T.label}>MEDIÇÕES DISPONÍVEIS</Text>
                  <View style={T.row}>
                    {m?.measured.map((j) => (
                      <Action
                        key={j}
                        icon="thermometer"
                        label={`${m.names[j]} (${m.units[j]})`}
                        active={form.measurementIndices.includes(j)}
                        onPress={() =>
                          setForm((v) => ({
                            ...v,
                            measurementIndices: v.measurementIndices.includes(j)
                              ? v.measurementIndices.filter((k) => k !== j)
                              : [...v.measurementIndices, j].sort(
                                  (a, b) => a - b,
                                ),
                          }))
                        }
                      />
                    ))}
                  </View>
                  <View style={styles.fields}>
                    {field("noise", "σ sensor", "K ou °C")}
                    {field("qScale", "Escala Q")}
                    {field("rScale", "Escala R")}
                    {field("initialOffset", "Erro inicial", "escala relativa")}
                  </View>
                  <Note color={C.muted}>
                    Ruído e Q/R podem mudar durante a execução. A alteração do
                    erro inicial exige reinício.
                  </Note>
                  <Action icon="check" label="Aplicar" active onPress={apply} />
                </>
              )}
              {sheet === "simulation" && (
                <>
                  <View style={styles.fields}>
                    {field("dt", "Amostragem", "s")}
                    {field("duration", "Duração", "s")}
                    {field("seed", "Seed")}
                  </View>
                  <Note>
                    Alterar passo ou seed reinicia a execução. RK4 com subpassos
                    limitados pelo modelo.
                  </Note>
                  <Action
                    icon="check"
                    label="Aplicar e reiniciar"
                    active
                    onPress={() => {
                      try {
                        session.configure(form);
                        session.reset();
                        setSheet(null);
                      } catch (err) {
                        fail(err);
                      }
                    }}
                  />
                </>
              )}
              {sheet === "disturbance" && (
                <>
                  <View style={styles.fields}>
                    {field("disturbance", "ΔT alimentação", "K")}
                  </View>
                  <View style={T.row}>
                    {[-2, 0, 2, 5].map((d) => (
                      <Pressable
                        key={d}
                        accessibilityRole="button"
                        accessibilityLabel={`Perturbação ${d} K`}
                        onPress={() =>
                          setForm((x) => ({ ...x, disturbance: d }))
                        }
                        style={[
                          T.card,
                          {
                            minWidth: 64,
                            alignItems: "center",
                            borderColor:
                              form.disturbance === d ? C.amber : C.line,
                          },
                        ]}
                      >
                        <Text style={{ color: C.amber, fontSize: 18 }}>
                          {d > 0 ? "+" : ""}
                          {d} K
                        </Text>
                      </Pressable>
                    ))}
                  </View>
                  <Action
                    icon="lightning-bolt"
                    label="Aplicar perturbação"
                    active
                    onPress={() => {
                      try {
                        session.configure({ disturbance: form.disturbance });
                        setSheet(null);
                        if (tutorial === 2) setTutorial(3);
                      } catch (err) {
                        fail(err);
                      }
                    }}
                  />
                </>
              )}
              {sheet === "properties" && (
                <>
                  {p.model === "flowsheet" && node ? (
                    <>
                      <Text style={T.label}>{CATALOG[node.kind]?.label}</Text>
                      <View style={styles.fields}>
                        {Object.entries(node.parameters).map(([key, v]) => (
                          <NumberField
                            key={key}
                            label={PARAM_LABELS[key] ?? key}
                            value={v}
                            unit={PARAM_UNITS[key]}
                            onChange={(value) => {
                              try {
                                session.edit(
                                  setNodeParameter(
                                    session.project,
                                    node.id,
                                    key,
                                    value,
                                  ),
                                );
                              } catch (err) {
                                fail(err);
                              }
                            }}
                          />
                        ))}
                      </View>
                      <Text style={T.label}>CONEXÕES</Text>
                      {p.graph.edges
                        .filter(
                          (x) => x.source === node.id || x.target === node.id,
                        )
                        .map((edge) => (
                          <View key={edge.id} style={T.row}>
                            <Text style={[T.body, { flex: 1 }]}>
                              {edge.source} → {edge.target}
                            </Text>
                            <Action
                              compact
                              icon="link-off"
                              label="Desconectar corrente"
                              onPress={() =>
                                Alert.alert("Desconectar corrente?", edge.id, [
                                  { text: "Cancelar" },
                                  {
                                    text: "Desconectar",
                                    style: "destructive",
                                    onPress: () => {
                                      const pp = copy(p);
                                      pp.graph.edges = pp.graph.edges.filter(
                                        (x) => x.id !== edge.id,
                                      );
                                      session.edit(pp);
                                    },
                                  },
                                ])
                              }
                            />
                          </View>
                        ))}
                      <Action
                        icon="delete-outline"
                        label="Excluir equipamento"
                        color={C.red}
                        onPress={() =>
                          Alert.alert("Excluir equipamento?", node.id, [
                            { text: "Cancelar" },
                            {
                              text: "Excluir",
                              style: "destructive",
                              onPress: () => {
                                const pp = copy(p);
                                pp.graph.nodes = pp.graph.nodes.filter(
                                  (x) => x.id !== node.id,
                                );
                                pp.graph.edges = pp.graph.edges.filter(
                                  (x) =>
                                    x.source !== node.id &&
                                    x.target !== node.id,
                                );
                                session.edit(pp);
                                setSheet(null);
                              },
                            },
                          ])
                        }
                      />
                    </>
                  ) : (
                    <>
                      <Text style={T.body}>
                        {m?.provenance ?? p.readOnlyReason}
                      </Text>
                      <Note>{m?.warning ?? p.readOnlyReason}</Note>
                      <Text style={T.label}>ESTADOS E UNIDADES</Text>
                      {m?.names.map((label, j) => (
                        <Text key={label} style={T.body}>
                          {label} · {number(s?.x[j], 6)} {m.units[j]}
                        </Text>
                      ))}
                      <Action
                        icon="tune"
                        label="Configurar experimento"
                        onPress={() => open("simulation")}
                      />
                    </>
                  )}
                </>
              )}
              {sheet === "add" && (
                <View
                  style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}
                >
                  {(Object.keys(CATALOG) as NodeKind[]).map((kind) => (
                    <Action
                      key={kind}
                      style={{
                        width: "47%",
                        backgroundColor: C.bg,
                        minHeight: 72,
                      }}
                      icon={
                        kind === "source"
                          ? "arrow-right-bold-outline"
                          : kind === "sink"
                            ? "arrow-right-bold-box-outline"
                            : kind === "tank" || kind === "cstr"
                              ? "flask-outline"
                              : kind === "pump"
                                ? "pump"
                                : kind === "valve"
                                  ? "valve"
                                  : "vector-polyline"
                      }
                      label={CATALOG[kind].label}
                      onPress={() => {
                        const pp = copy(p),
                          id = `${kind.toUpperCase().slice(0, 2)}-${Date.now().toString().slice(-4)}`;
                        pp.graph.nodes.push({
                          id,
                          kind,
                          parameters: { ...CATALOG[kind].defaults },
                        });
                        pp.layout.nodes[id] = {
                          x: 40 + (pp.graph.nodes.length % 4) * 150,
                          y: 210 + Math.floor(pp.graph.nodes.length / 4) * 140,
                        };
                        session.edit(pp);
                        session.selected = id;
                        setSheet(null);
                      }}
                    />
                  ))}
                </View>
              )}
              {(sheet === "projects" || sheet === "compare") && (
                <>
                  {sheet === "projects" && (
                    <>
                      <View style={T.row}>
                        <TextInput
                          style={[T.input, { flex: 1 }]}
                          value={name}
                          maxLength={120}
                          onChangeText={setName}
                          accessibilityLabel="Nome do projeto"
                        />
                        <Action
                          compact
                          icon="check"
                          label="Renomear e salvar"
                          onPress={() => {
                            p.name = name.trim() || p.name;
                            if (e) e.project.name = p.name;
                            void session
                              .save()
                              .then(() => listProjects())
                              .then(setRows)
                              .catch(fail);
                            session.publish();
                          }}
                        />
                      </View>
                      <View style={{ flexDirection: "row", flexWrap: "wrap" }}>
                        <Action
                          icon="file-import-outline"
                          label="Importar"
                          onPress={() =>
                            void DocumentPicker.getDocumentAsync({
                              type: [
                                "application/json",
                                "text/plain",
                                "application/octet-stream",
                              ],
                              copyToCacheDirectory: true,
                            })
                              .then(async (r) => {
                                if (!r.canceled) {
                                  const data = await new File(
                                    r.assets[0].uri,
                                  ).text();
                                  await session.replace(importProject(data));
                                  setSheet(null);
                                }
                              })
                              .catch(fail)
                          }
                        />
                        <Action
                          icon="file-export-outline"
                          label="Exportar projeto"
                          onPress={() =>
                            void shareFile(
                              "meu-projeto.processlab.json",
                              exportProject(p),
                              "application/json",
                            ).catch(fail)
                          }
                        />
                      </View>
                    </>
                  )}
                  {rows.length === 0 && (
                    <Text style={T.body}>Nenhum projeto salvo.</Text>
                  )}
                  {rows.map((row) => (
                    <View style={[T.card, T.row]} key={row.id}>
                      <Pressable
                        style={{
                          flex: 1,
                          minHeight: 48,
                          justifyContent: "center",
                        }}
                        accessibilityRole="button"
                        accessibilityLabel={`Abrir ${row.name}`}
                        onPress={() => {
                          if (sheet === "compare") {
                            void loadProject(row.id)
                              .then((v) => {
                                if (!v?.checkpoint)
                                  throw Error("Projeto sem resultados");
                                if (v.project.model !== p.model)
                                  throw Error(
                                    "Compare execuções do mesmo modelo",
                                  );
                                setCompare(Engine.restore(v.checkpoint));
                                setSheet(null);
                              })
                              .catch(fail);
                          } else
                            void session
                              .open(row.id)
                              .then(() => setSheet(null))
                              .catch(fail);
                        }}
                      >
                        <Text style={{ color: C.text, fontSize: 15 }}>
                          {row.name}
                        </Text>
                        <Text
                          style={{ color: C.muted, fontSize: 11, marginTop: 6 }}
                        >
                          {modelNames[row.model as ModelId] ?? row.model}
                        </Text>
                      </Pressable>
                      {sheet === "projects" && (
                        <Action
                          compact
                          icon="delete-outline"
                          label={`Excluir ${row.name}`}
                          color={C.red}
                          onPress={() =>
                            Alert.alert("Excluir projeto salvo?", row.name, [
                              { text: "Cancelar" },
                              {
                                text: "Excluir",
                                style: "destructive",
                                onPress: () =>
                                  void removeProject(row.id)
                                    .then(() => listProjects())
                                    .then(setRows)
                                    .catch(fail),
                              },
                            ])
                          }
                        />
                      )}
                    </View>
                  ))}
                </>
              )}
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}
export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <Screen />
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
const styles = StyleSheet.create({
  header: {
    height: 66,
    paddingHorizontal: 15,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottomWidth: 1,
    borderBottomColor: C.line,
  },
  brand: {
    width: 39,
    height: 42,
    borderWidth: 1,
    borderColor: C.line,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: C.panel,
  },
  homeCard: {
    minWidth: 145,
    width: "47.9%",
    flexGrow: 1,
    borderRadius: 19,
    padding: 18,
    backgroundColor: C.panel,
    borderWidth: 1,
    borderColor: C.line,
    minHeight: 150,
  },
  iconTile: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  metric: {
    minWidth: 146,
    padding: 13,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: C.line,
    backgroundColor: C.panel,
  },
  transport: {
    height: 67,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-evenly",
    paddingHorizontal: 12,
    borderTopWidth: 1,
    borderColor: C.line,
    backgroundColor: C.panel,
  },
  tabs: {
    height: 62,
    flexDirection: "row",
    paddingHorizontal: 6,
    backgroundColor: C.bg,
    borderTopWidth: 1,
    borderColor: C.line,
  },
  rail: {
    width: 72,
    borderRightWidth: 1,
    borderColor: C.line,
    justifyContent: "space-evenly",
  },
  sheet: {
    backgroundColor: C.panel,
    borderTopLeftRadius: 25,
    borderTopRightRadius: 25,
    borderWidth: 1,
    borderColor: C.line,
  },
  fields: { flexDirection: "row", flexWrap: "wrap", gap: 14 },
});
