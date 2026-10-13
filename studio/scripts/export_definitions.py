"""Persist executable example definitions and the structural schema."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from processlab.scenarios import scenarios
from processlab.schema import CATALOG

root=Path(__file__).resolve().parents[1]
(root/'examples').mkdir(exist_ok=True)
for p in scenarios():
    (root/'examples'/(p['id']+'.processlab.json')).write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
quantity={'oneOf':[{'type':'number'},{'type':'object','required':['value','unit'],'properties':{'value':{'type':'number'},'unit':{'type':'string'}},'additionalProperties':False}]}
node={'type':'object','required':['id','kind','parameters','layout'],'properties':{
    'id':{'type':'string'},'kind':{'enum':list(CATALOG)},'label':{'type':'string'},
    'parameters':{'type':'object','additionalProperties':{'$ref':'#/$defs/quantity'}},
    'layout':{'type':'object','required':['x','y'],'properties':{'x':{'type':'number'},'y':{'type':'number'}}}}}
edgekeys=['id','source','target','source_port','target_port','kind']
edge={'type':'object','required':edgekeys,'properties':{k:{'type':'string'} for k in edgekeys}}
schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:ycs:processlab:project:1','title':'ProcessLab Studio project v1','type':'object','required':['schema_version','id','name','model','experiment'],'properties':{
    'schema_version':{'const':1},'id':{'type':'string','pattern':'^[a-zA-Z0-9_-]{1,80}$'},'name':{'type':'string'},
    'model':{'enum':['flowsheet','pg-original','eb-reduced']},'nodes':{'type':'array','maxItems':40,'items':node},
    'edges':{'type':'array','maxItems':100,'items':edge},'experiment':{'type':'object'},'control_equipment':{'type':'string'}},
    '$defs':{'quantity':quantity},'$comment':'Structural contract. schema.canonical and Flowsheet compiler additionally enforce dimensions, numerical limits and topology.'}
(root/'project.schema.json').write_text(json.dumps(schema,indent=2)+'\n',encoding='utf-8')
