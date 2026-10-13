"""Five explicit built-in definitions; experimental absence never yields synthetic results."""
from .schema import canonical


def node(id,kind,x,y,**parameters):
    return {"id":id,"kind":kind,"label":id,"parameters":parameters,"layout":{"x":x,"y":y}}


def edge(id,source,target,source_port="out",target_port="in",kind="material"):
    return dict(id=id,source=source,target=target,source_port=source_port,target_port=target_port,kind=kind)


def scenarios():
    base={"schema_version":1,"id":"heated-tank","name":"B · Tanque com controle PID","model":"flowsheet","nodes":[node("F-101","source",20,80,flow=1,temperature=298.15,fraction=.1),node("T-101","tank",300,80,volume=.1,temperature=298.15,fraction=.1,duty=20000),node("P-101","sink",580,80)],"edges":[edge("S-1","F-101","T-101"),edge("S-2","T-101","P-101")],"control_equipment":"T-101","experiment":{"dt":5,"duration":600,"controller":"pid","observer":"ekf","setpoint":310,"manual":20000,"kp":7000,"ki":100,"disturbance_time":200,"disturbance_value":-8}}
    basic={"schema_version":1,"id":"basic-flowsheet","name":"A · Mistura e aquecimento","model":"flowsheet","nodes":[node("F-101","source",10,30,flow=1,temperature=295.15,fraction=.1),node("F-102","source",10,210,flow=.5,temperature=315.15,fraction=.3),node("M-101","mixer",230,100),node("H-101","heater",430,100,duty=15000),node("T-101","tank",630,100,volume=.1,temperature=300,fraction=.15,duty=0),node("P-101","sink",830,100)],"edges":[edge("S-1","F-101","M-101",target_port="in1"),edge("S-2","F-102","M-101",target_port="in2"),edge("S-3","M-101","H-101"),edge("S-4","H-101","T-101"),edge("S-5","T-101","P-101")],"experiment":{"manual":0,"controller":"manual","setpoint":304.2082145,"disturbance_value":0}}
    pg={"schema_version":1,"id":"pg-original","name":"C · Propilenoglicol — modelo original","model":"pg-original","experiment":{"dt":54,"duration":2160,"controller":"pid","observer":"ukf","manual":453.59237,"setpoint":332.333618,"kp":20,"ki":.02,"disturbance_time":540,"disturbance_value":2,"chemical_period":10,"chemical_delay":3,"sensor_sigma":.15,"initial_estimate_offset":.1}}
    eb={"schema_version":1,"id":"eb-reduced","name":"D · Etilbenzeno — R1 reduzido","model":"eb-reduced","experiment":{"dt":72,"duration":2160,"controller":"manual","observer":"ekf","setpoint":160,"manual":1,"disturbance_time":720,"disturbance_value":1,"sensor_sigma":.1,"initial_estimate_offset":.05}}
    # The archived EB duty is computed by its own recovered source, not a copied guess.
    from .models import ResearchModel
    eb["experiment"]["manual"]=ResearchModel("eb-reduced").u0
    advanced={**base,"id":"tank-nmpc","name":"E · Tanque NMPC + UKF (experimental)","experiment":{**base["experiment"],"controller":"nmpc","observer":"ukf","dt":10,"duration":300,"horizon":5,"disturbance_time":120}}
    return [canonical(p) for p in [basic,base,pg,eb,advanced]]
