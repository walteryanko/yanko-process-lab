function [Cost] = cost(Q)
load otim

sizet = size(u,1);
Xest = zeros(376,6);

xest = [0;3.45;0;0;75;60];
P = 0*diag([0.1,0.1,0.1,0.1,10,10]);
C = [0, 0, 0, 0, 1, 0;
     0, 0, 0, 0, 0, 1];
MatR = 1e-1*diag([1,1]);
MatQ = Q*diag([1,1,1,1,1,1]);

for i=1:sizet    
%% Filtro de Kalman
%% Inicialização e parâmetros do FK
%% Etapa de Previsão
[xest,F]=CSTRmdl_FK(xest, u(i,:)');
P = F*P*F' + MatQ; 
%% Etapa de Correção
K = P*C'/(C*P*C' + MatR);
xest = xest + K*(z(i,:)'-C*xest);
P = (eye(size(K*C))-K*C)*P;
%% Limitação
if xest(1)<0
    xest(1)=0;
elseif xest(2)<0
    xest(2)=0;
elseif xest(3)<0
    xest(3)=0;
elseif xest(4)<0
    xest(4)=0;
elseif xest(5)<0
    xest(5)=0;
elseif xest(6)<0
    xest(6)=0;
end
%% Saídas
x = [xest(1), xest(2), xest(3), xest(4), xest(5), xest(6)];
Xest(i,:)=x';
end
%% Função custo
Soma=sum((X-Xest).^2);
Cost=sum(Soma');