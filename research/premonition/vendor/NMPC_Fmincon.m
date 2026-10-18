 function mvseq = NMPC_Fmincon(x,y,ref,md,mvseq0,Ts,P,M,u1LowLimit,u1HighLimit,MaxIter,TolCon,TolFun,TolX,N,Q,R)
%% Obtain optimal control sequence by solving a nonlinear optimization problem at run time using |fmincon|.
%
% Copyright 2016 The MathWorks, Inc.

LB = u1LowLimit*ones(M,1);
UB = u1HighLimit*ones(M,1);
lastmv = mvseq0(1);
FUN = @(mvseq) costFunction(mvseq,x,y,ref,md,lastmv,Ts,P,M,N,Q,R);

OPTIONS = optimoptions('fmincon','Display','none','Algorithm','sqp','MaxIter',MaxIter,'TolCon',TolCon,'TolFun',TolFun,'TolX',TolX);
mvseq = fmincon(FUN,mvseq0,[],[],[],[],LB,UB,[],OPTIONS);


function J = costFunction(mvseq,x,y,ref,md,lastmv,Ts,P,M,N,Q,R)
%% Cost function of nonlinear MPC
%
% Inputs:
%   mvseq:  optimization variable, from time k to time k+N-1 
%   x:      plant state at time k
%   y:      measured output at time k
%   ref:    references with previewing, from time k+1 to time k+N
%   md:     measured disturbance at time k
%   u0:     previous controller output at time k-1
%   Ts:     controller sample time
%   P:      prediction horizon
%   M:      control horizon
%
% Output:
%   J:      objective function cost

%% Nonlinear MPC design parameters
% Q matrix penalizes tracking error for performance.
%Q = 1;

% R matrix penalizes MV rate of change for robustness.
%R = 0;

%% Cost Calculation
% Set initial plant states.
xk = x;

% Obtain output disturbance at current time as an offset.
[~,yk] = modeloCT(xk,mvseq(1),md);
offset = y - yk;

% Loop through each prediction step.
J = 0;

for ct=1:P
    % Get MV, next MV, and the change from last MV to MV at step k.
    if ct <= M
        uk = mvseq(ct);
        if ct<M
            uk1 = mvseq(ct+1);
        else
            uk1 = mvseq(M);
        end
        if ct==1
            du = uk - lastmv;
        else
            du = uk - mvseq(ct-1);
        end
    else
        uk = mvseq(M);
        uk1 = mvseq(M);
        du = 0;
    end
    
    % Obtain plant state at next prediction step.
    xk1 = modeloDT(xk,uk,md,Ts,N);
    
    % Obtain plant output at next prediction step
    [~,yk1] = modeloCT(xk1,uk1,md);
    
    % Apply offset from output disturbance
    yk1 = yk1 + offset;
    
    % accumulate tracking cost from y(k+1) to y(k+N).
    % use yLow to scale
%     J = J + Q*((ref(ct) - yk1)/(0.1433))^2;
 J = J + Q*((ref(ct) - yk1)/(0.1433))^2;
    
    % Accumulate MV rate of change cost from u(k) to u(k+N-1).
    % uLow(1) to scale
    J = J + R*(du/1000)^2;
    
    if xk1(5)>=160
        J = J + 1000*((160-xk1(5))/(160))^2;
    end
    
    % Update xk for the next prediction step.
    xk = xk1;
end
