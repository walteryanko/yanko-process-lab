import * as SQLite from 'expo-sqlite';
import {type Project} from '../../../packages/scientific-core/types';
import {type Checkpoint} from '../../../packages/scientific-core/engine';
type Row={id:string;name:string;model:string;updated:number;payload:string};
let db:SQLite.SQLiteDatabase;let queue=Promise.resolve();
export async function initStore(){
 db=await SQLite.openDatabaseAsync('processlab-v1.db');
 await db.execAsync('PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,model TEXT NOT NULL,updated INTEGER NOT NULL,payload TEXT NOT NULL); CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL); PRAGMA user_version=1;');
}
export function saveProject(project:Project,checkpoint?:Checkpoint){
 const payload=JSON.stringify({project,checkpoint}),updated=Date.now();
 const task=queue.then(async()=>{await db.withTransactionAsync(async()=>{
  await db.runAsync('INSERT INTO projects(id,name,model,updated,payload) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,model=excluded.model,updated=excluded.updated,payload=excluded.payload',project.id,project.name,project.model,updated,payload);
  await db.runAsync("INSERT INTO meta(key,value) VALUES('last',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",project.id);
 });});queue=task.catch(()=>{});return task;
}
export async function listProjects(){return db.getAllAsync<Row>('SELECT id,name,model,updated FROM projects ORDER BY updated DESC');}
export async function loadProject(id:string):Promise<{project:Project;checkpoint?:Checkpoint}|null>{const r=await db.getFirstAsync<Row>('SELECT payload FROM projects WHERE id=?',id);return r?JSON.parse(r.payload):null;}
export async function lastProject(){const r=await db.getFirstAsync<{value:string}>("SELECT value FROM meta WHERE key='last'");return r?loadProject(r.value):null;}
export async function removeProject(id:string){await queue;await db.runAsync('DELETE FROM projects WHERE id=?',id);}
