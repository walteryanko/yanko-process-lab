"""Scenarios transcribed from Brandao (2019), printed pp. 51-72.

Event values are fractions of nominal, never successive percentage products.
Temperature percentages apply to Fahrenheit as explicitly stated in the thesis.
The complete historical model is used; no hidden physical mismatch is injected.
"""
from dataclasses import dataclass,asdict
import numpy as np
from .physics import LEGACY_U0,LEGACY_RHO,CUNIT,equilibrium

U_NOM=LEGACY_U0.copy()
X_NOM=equilibrium(U_NOM,variant=1)
SP_NOM=.1433*CUNIT
T_LIMIT=(160.-32)/1.8+273.15
CONVERSION=np.array([CUNIT]*4+[1/1.8]*2)
Q_HIST=np.array([5.616e-8]*3+[2.4246e-13,.0346356,.0066123])*CONVERSION**2
P_HIST=1e-6*CONVERSION**2
R_HIST=(np.array([1.385,1.062])/1.8)**2
INPUT_STD=np.array([.8,10.,1.,0.,.75,.6])*np.array([.45359237]*4+[1/1.8]*2)
X_START=np.array([0.,LEGACY_RHO[1],0.,0.,U_NOM[4],U_NOM[5]])
INPUT_NAMES=['FA','FB','FM','mw','Tfeed','Tcool']

@dataclass(frozen=True)
class Scenario:
    key:str
    title:str
    kind:str
    hours:float
    events:tuple
    figures:str
    pages:str
    startup:bool=False
    note:str=''
    def as_dict(self):return asdict(self)

def ev(variable,first,second=1.,times=(4.,8.)):
    return ((times[0],variable,first),(times[1],variable,second))

SCENARIOS=[
 Scenario('OL_START','Partida em malha aberta','open',3.,(),'19, 27','51, 61',True),
 Scenario('OL_FA','Malha aberta: FA ±10%','open',17.,ev('FA',.9,1.,(1.,5.))+ev('FA',1.1,1.,(9.,13.)),'20','52'),
 Scenario('OL_FB','Malha aberta: FB ±10%','open',17.,ev('FB',1.1,1.,(1.,5.))+ev('FB',.9,1.,(9.,13.)),'21','53'),
 Scenario('OL_FM','Malha aberta: FM ±50%','open',17.,ev('FM',1.5,1.,(1.,5.))+ev('FM',.5,1.,(9.,13.)),'22','54'),
 Scenario('OL_MW','Malha aberta: mw ±50%','open',17.,ev('mw',1.5,1.,(1.,5.))+ev('mw',.5,1.,(9.,13.)),'23','55'),
 Scenario('OL_TF','Malha aberta: T0 ±10% em °F','open',17.,ev('Tfeed',.9,1.,(1.,5.))+ev('Tfeed',1.1,1.,(9.,13.)),'24','56'),
 Scenario('OL_TC','Malha aberta: Ta1 ±20% em °F','open',17.,ev('Tcool',1.2,1.,(1.,5.))+ev('Tcool',.8,1.,(9.,13.)),'25','56-57',note='Eixo térmico da figura é inconsistente com Tcool=60°F documentado; prevalecem código, tabela e percentuais do texto.'),
 Scenario('REG_FA10','Regulatório: FA −10% e retorno','regulatory',12.,ev('FA',.9),'29','63'),
 Scenario('REG_FB10','Regulatório: FB +10% e retorno','regulatory',12.,ev('FB',1.1),'30','63-64'),
 Scenario('REG_TF10','Regulatório: T0 −10% em °F','regulatory',12.,ev('Tfeed',.9),'31','64'),
 Scenario('REG_TC20','Regulatório: Ta1 −20% em °F','regulatory',12.,ev('Tcool',.8),'32','65'),
 Scenario('SERVO_P10','Servo: CC +10% e retorno','servo',12.,ev('SP',1.1),'33','65'),
 Scenario('REG_FA15','Regulatório forte: FA −15%','regulatory',12.,ev('FA',.85),'34','68-69'),
 Scenario('REG_TF30','Regulatório forte: T0 −30% em °F','regulatory',12.,ev('Tfeed',.7),'35','69'),
 Scenario('SERVO_M20','Servo forte: CC −20%','servo',12.,((4.,'SP',.8),),'36','70'),
 Scenario('CL_START','Partida com controle','startup',3.,(),'37, 38','71-72',True),
 Scenario('SERVO_P20','Servo térmico: CC +20% em 3 h','servo',6.,((3.,'SP',1.2),),'39','72',note='Amplitude +20% e instante 3 h lidos da referência tracejada da Figura 39; não numerados no parágrafo.'),
 Scenario('TUNING','Sequência de sintonia do NMPC','combined',12.,((2.,'FA',.9),(4.,'FA',1.),(6.,'FA',1.1),(8.,'FA',1.),(10.,'SP',.9)),'Tabela 6','67-68'),
 Scenario('OL_STEADY','Estimação em regime permanente','open',3.,(),'28','61',note='Ensaio explícito de regime permanente; mesmos ruídos e covariâncias dos demais cenários.'),
]
BY_KEY={c.key:c for c in SCENARIOS}

def commanded(scenario,t):
    u=U_NOM.copy();sp=SP_NOM
    for when,var,factor in scenario.events:
        if t+1e-10<when:continue
        if var=='SP':sp=SP_NOM*factor
        else:
            j=INPUT_NAMES.index(var)
            u[j]=U_NOM[j]*factor if j<4 else (((U_NOM[j]-273.15)*1.8+32)*factor-32)/1.8+273.15
    return u,float(sp)

def initial_state(scenario):return (X_START if scenario.startup else X_NOM).copy()

def observer_options(x0,integrator=0):
    return dict(initial_state=np.asarray(x0,float),initial_covariance=P_HIST,process_variance=Q_HIST,
                measurement_variance=R_HIST,alpha=1e-3,integrator=integrator)

def time_grid(hours):
    t=np.arange(0,hours+1e-9,.015)
    if hours-t[-1]>1e-8:t=np.r_[t,hours]
    return t
