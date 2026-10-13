import React, { useMemo, useRef, useState } from "react";
import { View, Text } from "react-native";
import {
  Canvas,
  Path,
  Skia,
  Group,
  Circle,
  RoundedRect,
  Line,
  vec,
} from "@shopify/react-native-skia";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import { CATALOG } from "../../../packages/scientific-core/flowsheet";
import {
  copy,
  type Project,
  type NodeKind,
} from "../../../packages/scientific-core/types";
import { connect } from "../../../packages/scientific-core/project";
import { session } from "./session";
import { Action, C, T } from "./ui";
const W = 106,
  H = 78;
function Symbol({ kind, selected }: { kind: NodeKind; selected: boolean }) {
  const col = selected ? C.cyan : C.green,
    p = Skia.Path.Make();
  if (kind === "source" || kind === "sink") {
    p.moveTo(18, 22);
    p.lineTo(66, 22);
    p.lineTo(85, 39);
    p.lineTo(66, 56);
    p.lineTo(18, 56);
    p.close();
  } else if (kind === "valve") {
    p.moveTo(20, 20);
    p.lineTo(86, 58);
    p.lineTo(86, 20);
    p.lineTo(20, 58);
    p.close();
  } else if (kind === "mixer" || kind === "splitter") {
    p.moveTo(21, 20);
    p.lineTo(85, 39);
    p.lineTo(21, 58);
    p.close();
  } else if (kind === "tank" || kind === "cstr") {
    p.moveTo(25, 20);
    p.lineTo(25, 59);
    p.quadTo(53, 77, 81, 59);
    p.lineTo(81, 20);
    p.quadTo(53, 4, 25, 20);
    p.moveTo(53, 4);
    p.lineTo(53, 50);
    p.moveTo(36, 46);
    p.lineTo(70, 52);
  } else {
    p.moveTo(24, 22);
    p.lineTo(82, 56);
    p.moveTo(24, 56);
    p.lineTo(82, 22);
  }
  return (
    <Group>
      <RoundedRect
        x={0}
        y={0}
        width={W}
        height={H}
        r={16}
        color={selected ? "#183643" : "#142A34"}
      />
      {["pump", "exchanger"].includes(kind) && (
        <Circle
          cx={53}
          cy={39}
          r={27}
          style="stroke"
          strokeWidth={2}
          color={col}
        />
      )}
      <Path path={p} color={col} style="stroke" strokeWidth={2.2} />
      {["heater", "cooler"].includes(kind) && (
        <RoundedRect
          x={20}
          y={16}
          width={67}
          height={47}
          r={5}
          style="stroke"
          strokeWidth={2}
          color={kind === "heater" ? C.amber : C.cyan}
        />
      )}
    </Group>
  );
}
export function FlowCanvas({
  project,
  height = 235,
  onDetails,
}: {
  project: Project;
  height?: number;
  onDetails: () => void;
}) {
  const [width, setWidth] = useState(360),
    [mode, setMode] = useState<"move" | "pan" | "connect">("pan");
  const [v, setV] = useState({
    zoom: project.layout.zoom,
    pan: project.layout.pan,
    nodes: project.layout.nodes,
  });
  const vr = useRef(v);
  vr.current = v;
  const [port, setPort] = useState<{ id: string; port: string } | null>(null),
    [error, setError] = useState("");
  React.useEffect(() => {
    setV({
      zoom: project.layout.zoom,
      pan: project.layout.pan,
      nodes: project.layout.nodes,
    });
  }, [project.id, project.layout]);
  const fixed = project.model !== "flowsheet" || !!project.readOnlyReason;
  const commit = () => {
    const p = copy(session.project);
    p.layout = { ...p.layout, ...vr.current };
    session.edit(p, false);
  };
  const world = (x: number, y: number) => ({
    x: (x - vr.current.pan.x) / vr.current.zoom,
    y: (y - vr.current.pan.y) / vr.current.zoom,
  });
  const hit = (x: number, y: number) =>
    project.graph.nodes.find((n) => {
      const pos = vr.current.nodes[n.id];
      return (
        pos && x >= pos.x && x <= pos.x + W && y >= pos.y && y <= pos.y + H
      );
    });
  const tap = (x: number, y: number, details = false) => {
    const p = world(x, y);
    if (mode === "connect" && !fixed) {
      for (const n of project.graph.nodes) {
        const at = vr.current.nodes[n.id];
        if (!at) continue;
        const cat = CATALOG[n.kind];
        if (!cat) continue;
        for (const side of ["inputs", "outputs"] as const)
          for (let i = 0; i < cat[side].length; i++) {
            const xx = at.x + (side === "inputs" ? 0 : W),
              yy = at.y + (H * (i + 1)) / (cat[side].length + 1);
            if (Math.hypot(p.x - xx, p.y - yy) < 27 / vr.current.zoom) {
              if (side === "outputs") {
                setPort({ id: n.id, port: cat[side][i] });
                setError("Toque na porta de entrada");
                return;
              }
              if (port) {
                try {
                  session.edit(
                    connect(
                      session.project,
                      port.id,
                      port.port,
                      n.id,
                      cat[side][i],
                    ),
                  );
                  setError("Conectado");
                  setPort(null);
                } catch (e) {
                  setError(String(e));
                }
                return;
              }
            }
          }
      }
    }
    const n = hit(p.x, p.y);
    if (n) {
      session.selected = n.id;
      session.publish();
      if (details) onDetails();
    }
  };
  const start = useRef({ x: 0, y: 0, zoom: 1, node: "", nx: 0, ny: 0 });
  const gestures = useMemo(() => {
    const pan = Gesture.Pan()
      .minDistance(6)
      .runOnJS(true)
      .onStart((e) => {
        const p = world(e.x, e.y),
          n = hit(p.x, p.y),
          a = vr.current;
        start.current = {
          x: a.pan.x,
          y: a.pan.y,
          zoom: a.zoom,
          node: mode === "move" && !fixed ? (n?.id ?? "") : "",
          nx: n ? a.nodes[n.id].x : 0,
          ny: n ? a.nodes[n.id].y : 0,
        };
      })
      .onUpdate((e) => {
        const s = start.current,
          a = vr.current;
        const next = s.node
          ? {
              ...a,
              nodes: {
                ...a.nodes,
                [s.node]: {
                  x: Math.round((s.nx + e.translationX / a.zoom) / 10) * 10,
                  y: Math.round((s.ny + e.translationY / a.zoom) / 10) * 10,
                },
              },
            }
          : { ...a, pan: { x: s.x + e.translationX, y: s.y + e.translationY } };
        vr.current = next;
        setV(next);
      })
      .onEnd(commit);
    const pinch = Gesture.Pinch()
      .runOnJS(true)
      .onStart(() => {
        start.current = {
          ...start.current,
          zoom: vr.current.zoom,
          x: vr.current.pan.x,
          y: vr.current.pan.y,
        };
      })
      .onUpdate((e) => {
        const s = start.current,
          z = Math.max(0.3, Math.min(2.5, s.zoom * e.scale)),
          next = {
            ...vr.current,
            zoom: z,
            pan: {
              x: e.focalX - ((e.focalX - s.x) * z) / s.zoom,
              y: e.focalY - ((e.focalY - s.y) * z) / s.zoom,
            },
          };
        vr.current = next;
        setV(next);
      })
      .onEnd(commit);
    const single = Gesture.Tap()
      .runOnJS(true)
      .onEnd((e) => tap(e.x, e.y));
    const double = Gesture.Tap()
      .numberOfTaps(2)
      .runOnJS(true)
      .onEnd((e) => tap(e.x, e.y, true));
    const long = Gesture.LongPress()
      .runOnJS(true)
      .onStart((e) => tap(e.x, e.y, true));
    return Gesture.Race(pinch, pan, Gesture.Exclusive(double, long, single));
  }, [project, mode, port, fixed]);
  function fit() {
    const points = Object.values(v.nodes);
    if (!points.length) return;
    const minx = Math.min(...points.map((p) => p.x)),
      maxx = Math.max(...points.map((p) => p.x)) + W,
      miny = Math.min(...points.map((p) => p.y)),
      maxy = Math.max(...points.map((p) => p.y)) + H;
    const z = Math.min(
      1.25,
      (width - 45) / (maxx - minx),
      (height - 85) / (maxy - miny),
    );
    const next = {
      ...v,
      zoom: z,
      pan: {
        x: (width - (maxx - minx) * z) / 2 - minx * z,
        y: (height - 45 - (maxy - miny) * z) / 2 - miny * z,
      },
    };
    vr.current = next;
    setV(next);
    commit();
  }
  React.useEffect(() => {
    fit();
  }, [width, height, project.id]);
  return (
    <View
      onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
      style={{
        height,
        backgroundColor: "#0C1820",
        borderRadius: 18,
        overflow: "hidden",
        borderWidth: 1,
        borderColor: C.line,
      }}
    >
      <GestureDetector gesture={gestures}>
        <View accessible={false} testID="flow-canvas" style={{ flex: 1 }}>
          <Canvas style={{ flex: 1 }}>
            {Array.from({ length: Math.ceil(width / 28) }, (_, i) => (
              <Line
                key={`x${i}`}
                p1={vec(i * 28, 0)}
                p2={vec(i * 28, height)}
                color="#14252E"
                strokeWidth={0.6}
              />
            ))}
            {Array.from({ length: Math.ceil(height / 28) }, (_, i) => (
              <Line
                key={`y${i}`}
                p1={vec(0, i * 28)}
                p2={vec(width, i * 28)}
                color="#14252E"
                strokeWidth={0.6}
              />
            ))}
            <Group
              transform={[
                { translateX: v.pan.x },
                { translateY: v.pan.y },
                { scale: v.zoom },
              ]}
            >
              {project.graph.edges.map((e) => {
                const a = v.nodes[e.source],
                  b = v.nodes[e.target],
                  na = project.graph.nodes.find((n) => n.id === e.source),
                  nb = project.graph.nodes.find((n) => n.id === e.target);
                if (!a || !b || !na || !nb) return null;
                const ca = CATALOG[na.kind],
                  cb = CATALOG[nb.kind];
                if (!ca || !cb) return null;
                const ay =
                    a.y +
                    (H * (ca.outputs.indexOf(e.source_port) + 1)) /
                      (ca.outputs.length + 1),
                  by =
                    b.y +
                    (H * (cb.inputs.indexOf(e.target_port) + 1)) /
                      (cb.inputs.length + 1),
                  mid = (a.x + W + b.x) / 2,
                  p = Skia.Path.Make();
                p.moveTo(a.x + W, ay);
                p.lineTo(mid, ay);
                p.lineTo(mid, by);
                p.lineTo(b.x, by);
                p.moveTo(b.x - 9, by - 5);
                p.lineTo(b.x, by);
                p.lineTo(b.x - 9, by + 5);
                return (
                  <Path
                    key={e.id}
                    path={p}
                    color={C.cyan}
                    style="stroke"
                    strokeWidth={2}
                  />
                );
              })}
              {project.graph.nodes.map((n) => {
                const pos = v.nodes[n.id];
                if (!pos || !CATALOG[n.kind]) return null;
                return (
                  <Group
                    key={n.id}
                    transform={[{ translateX: pos.x }, { translateY: pos.y }]}
                  >
                    <Symbol
                      kind={n.kind}
                      selected={n.id === session.selected}
                    />
                    {(["inputs", "outputs"] as const).flatMap((side) =>
                      CATALOG[n.kind][side].map((p, i) => (
                        <Circle
                          key={side + p}
                          cx={side === "inputs" ? 0 : W}
                          cy={
                            (H * (i + 1)) / (CATALOG[n.kind][side].length + 1)
                          }
                          r={mode === "connect" ? 10 : 4}
                          color={port?.id === n.id ? C.amber : C.cyan}
                        />
                      )),
                    )}
                  </Group>
                );
              })}
            </Group>
          </Canvas>
          <View pointerEvents="none" style={{ position: "absolute", inset: 0 }}>
            {project.graph.nodes.map((n) => {
              const p = v.nodes[n.id];
              return p ? (
                <Text
                  key={n.id}
                  style={{
                    position: "absolute",
                    left: p.x * v.zoom + v.pan.x,
                    top: (p.y + H + 5) * v.zoom + v.pan.y,
                    width: W * v.zoom,
                    textAlign: "center",
                    fontSize: Math.max(9, 11 * v.zoom),
                    color: C.text,
                    fontWeight: "600",
                  }}
                >
                  {n.id}
                </Text>
              ) : null;
            })}
          </View>
        </View>
      </GestureDetector>
      <View
        style={{
          position: "absolute",
          top: 8,
          left: 12,
          right: 8,
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Text style={[T.label, { fontSize: 9 }]}>
          {fixed ? "MODELO FIXO" : "EDITOR DE PLANTA"} · MATERIAL →
        </Text>
        <Text style={[T.label, { fontSize: 9 }]}>
          {Math.round(v.zoom * 100)}%
        </Text>
      </View>
      <View
        style={{
          position: "absolute",
          bottom: 3,
          right: 6,
          flexDirection: "row",
          backgroundColor: "#091218F0",
          borderRadius: 12,
        }}
      >
        <Action
          icon="hand-back-right-outline"
          label="Mover planta"
          compact
          active={mode === "pan"}
          onPress={() => setMode("pan")}
        />
        {!fixed && (
          <>
            <Action
              icon="cursor-move"
              label="Mover equipamento"
              compact
              active={mode === "move"}
              onPress={() => setMode("move")}
            />
            <Action
              icon="vector-polyline"
              label="Conectar portas"
              compact
              active={mode === "connect"}
              onPress={() => setMode("connect")}
            />
          </>
        )}
        <Action
          icon="fit-to-screen-outline"
          label="Centralizar planta"
          compact
          onPress={fit}
        />
      </View>
      {!!error && (
        <Text
          style={{
            position: "absolute",
            bottom: 55,
            left: 12,
            right: 10,
            fontSize: 11,
            color: C.amber,
          }}
        >
          {error}
        </Text>
      )}
    </View>
  );
}
