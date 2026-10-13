import { AppState } from "react-native";
import {
  Engine,
  type Checkpoint,
} from "../../../packages/scientific-core/engine";
import {
  newProject,
  validateSettings,
} from "../../../packages/scientific-core/project";
import {
  type Project,
  type Settings,
  copy,
} from "../../../packages/scientific-core/types";
import { initStore, lastProject, saveProject, loadProject } from "./storage";
class Session {
  project: Project = newProject();
  engine: Engine | null = new Engine(this.project);
  selected = "R-101";
  running = false;
  ready = false;
  revision = 0;
  message = "";
  speed = 1;
  tab = "home";
  private listeners = new Set<() => void>();
  private timer: ReturnType<typeof setTimeout> | null = null;
  private task: Generator | undefined;
  private undoStack: Project[] = [];
  private redoStack: Project[] = [];
  private savedAt = 0;
  private initialized = false;
  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  };
  snapshot = () => this.revision;
  publish() {
    this.revision++;
    for (const fn of this.listeners) fn();
  }
  async initialize() {
    if (this.initialized) return;
    this.initialized = true;
    try {
      await initStore();
      const old = await lastProject();
      if (old) {
        this.project = old.project;
        try {
          this.engine = old.checkpoint
            ? Engine.restore(old.checkpoint)
            : new Engine(old.project);
        } catch (e) {
          this.engine = null;
          this.message = String(e);
        }
      }
      this.ready = true;
    } catch (e) {
      this.message = `Armazenamento: ${e}`;
      this.ready = true;
    }
    AppState.addEventListener("change", (state) => {
      if (state !== "active") {
        this.pause();
        void this.save().catch((e) => {
          this.message = String(e);
          this.publish();
        });
      }
    });
    this.publish();
  }
  pause() {
    this.running = false;
    if (this.timer) clearTimeout(this.timer);
    this.task = undefined;
    this.publish();
  }
  start() {
    try {
      if (!this.engine) this.engine = new Engine(this.project);
      if (this.engine.done) {
        this.message = "Simulação concluída. Reinicie para executar novamente.";
        this.publish();
        return;
      }
      this.running = true;
      this.message = "";
      this.publish();
      this.tick();
    } catch (e) {
      this.message = String(e);
      this.publish();
    }
  }
  private tick = () => {
    if (!this.running || !this.engine) return;
    const started = performance.now();
    let completed = 0;
    do {
      if (!this.task) this.task = this.engine.advance();
      const r = this.task.next();
      if (r.done) {
        this.task = undefined;
        completed++;
      }
      if (this.engine.done) {
        this.running = false;
        this.message = this.engine.error ?? "Experimento concluído";
        break;
      }
    } while (completed < this.speed && performance.now() - started < 8);
    this.publish();
    if (this.engine.history.length - this.savedAt >= 20 || !this.running) {
      this.savedAt = this.engine.history.length;
      void this.save().catch((e) => {
        this.message = `Falha ao salvar: ${e}`;
        this.pause();
      });
    }
    if (this.running)
      this.timer = setTimeout(
        this.tick,
        Math.max(16, 120 - (performance.now() - started)),
      );
  };
  reset() {
    this.pause();
    try {
      this.engine = new Engine(this.project);
      this.message = "";
    } catch (e) {
      this.engine = null;
      this.message = String(e);
    }
    this.savedAt = 0;
    void this.save();
    this.publish();
  }
  configure(patch: Partial<Settings>) {
    if (!this.engine) throw Error("Conecte a planta antes de configurar");
    this.task = undefined;
    const next = { ...this.project.science.settings, ...patch };
    validateSettings(next, this.engine.model);
    this.engine.configure(patch);
    this.project.science.settings = next;
    void this.save();
    this.publish();
  }
  edit(project: Project, scientific = true) {
    if (this.project.readOnlyReason) throw Error(this.project.readOnlyReason);
    if (scientific) this.pause();
    this.undoStack.push(copy(this.project));
    if (this.undoStack.length > 40) this.undoStack.shift();
    this.redoStack = [];
    this.project = project;
    if (scientific) {
      try {
        this.engine = new Engine(project);
        this.message = "";
      } catch (e) {
        this.engine = null;
        this.message = String(e);
      }
    } else if (this.engine) this.engine.project.layout = copy(project.layout);
    void this.save();
    this.publish();
  }
  private restoreEdit(project: Project) {
    const scienceChanged =
      JSON.stringify(project.science) !==
        JSON.stringify(this.project.science) ||
      JSON.stringify(project.graph) !== JSON.stringify(this.project.graph);
    this.project = project;
    if (scienceChanged) this.reset();
    else {
      if (this.engine) this.engine.project.layout = copy(project.layout);
      void this.save();
      this.publish();
    }
  }
  undo() {
    if (!this.undoStack.length) return;
    this.redoStack.push(copy(this.project));
    this.restoreEdit(this.undoStack.pop()!);
  }
  redo() {
    if (!this.redoStack.length) return;
    this.undoStack.push(copy(this.project));
    this.restoreEdit(this.redoStack.pop()!);
  }
  async replace(project: Project, checkpoint?: Checkpoint) {
    this.pause();
    this.project = project;
    this.undoStack = [];
    this.redoStack = [];
    this.selected = project.graph.nodes[0]?.id ?? "";
    try {
      this.engine = checkpoint
        ? Engine.restore(checkpoint)
        : new Engine(project);
      this.message = project.readOnlyReason ?? "";
    } catch (e) {
      this.engine = null;
      this.message = String(e);
    }
    this.tab = "plant";
    this.savedAt = 0;
    await this.save();
    this.publish();
  }
  async open(id: string) {
    const p = await loadProject(id);
    if (p) await this.replace(p.project, p.checkpoint);
  }
  save() {
    return this.ready
      ? saveProject(this.project, this.engine?.checkpoint())
      : Promise.resolve();
  }
}
export const session = new Session();
