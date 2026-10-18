function xk1 = modeloDT(xk,uk,mdk,Ts,N)

delta = Ts/N;
xk1 = xk;
sizex=size(xk1,1);
for ct=1:N
	rk1=delta*modeloCT(xk1,uk,mdk);
	rk2=delta*modeloCT(xk1+rk1/2,uk,mdk);
	rk3=delta*modeloCT(xk1+rk2/2,uk,mdk);
	rk4=delta*modeloCT(xk1+rk3,uk,mdk);
    xk1 = xk1 + (rk1+2*rk2+2*rk3+rk4)/6;
% Force non-negativity
    for i=1:sizex
        if xk1(i)< 0
            xk1(i)=0;
        end
    end
end