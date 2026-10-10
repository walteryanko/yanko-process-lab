function [dxdt,y] = modeloCT(x,u,md)

%% Declaração das variáveis
%Entradas
Fa0 = md(1);
Fb0 = md(2);
Fm0 = md(3);
mc = u(1);
T0 = md(4);
Ta1 = md(5);
%Estados
Ca = x(1);
Cb = x(2);
Cc = x(3);
Cm = x(4);
T = x(5);
Tj = x(6);

%% Parâmetros e equações explícitas
cpa=35;
cpb=18;
cpc=46;
cpm=19.5;
roa=0.923;
rob=3.45;
rom=1.54;
E=32400;
R=1.987;
k0=16.96e12;
DeltaH=-36000;
Vcam=38.85; %ft^3
V=500/7.484;  %ft^3
UA=16000; %Btu/h*°F

v0=Fa0/roa+Fb0/rob+Fm0/rom;
tau=V/v0;
tetacp=cpa+Fb0/Fa0*cpb+Fm0/Fa0*cpm;

Ca0=Fa0/v0; %0.1812; %lbmol/ft^3
Cb0=Fb0/v0; %2.2652; %lbmol/ft^3
Cm0=Fm0/v0; %0.2265; %lbmol/ft^3

k=k0*exp(-E/R/(T+460));
ra=-k*Ca;
rb=-k*Ca;
rc=k*Ca;

Nm=Cm*V;
Na=Ca*V;
Nb=Cb*V;
Nc=Cc*V;

Q=mc*cpb*(Ta1-T)*(1-exp(-UA/(cpb*mc)));
NCp=Na*cpa+Nb*cpb+Nc*cpc+Nm*cpm;

%% Derivadas
dxdt(1,1) = 1/tau*(Ca0 - Ca)+ra;
dxdt(2,1) = 1/tau*(Cb0 - Cb)+rb;
dxdt(3,1) = 1/tau*(0 - Cc)+rc;
dxdt(4,1) = 1/tau*(Cm0 - Cm);
dxdt(5,1) = (Q-Fa0*tetacp*(T-T0)+(DeltaH)*ra*V)/NCp;
dxdt(6,1) = (mc*cpb*(Ta1 - Tj) - Q)/(rob*cpb*Vcam);

%% Variavel controlada
% y=(Ca0 - Ca)/Ca0;
y=x(3);
end

