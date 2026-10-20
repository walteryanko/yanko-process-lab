# Mathematical scope and proofs

All statements below concern the stated model class, not an experimentally identified industrial reactor. Time is in hours. All worlds share the same known feed histories, parameters, reference, actuator constraints and initial measured temperatures. Initial chemical states range over an open positive domain admitted by the six-state benchmark. This does not impose a separately validated liquid equation of state. If additional exact admissibility constraints are imposed, the constructed equivalence class must be intersected with them; its quoted dimension need not survive. Solutions are unique up to the considered finite horizon and remain in that set. Inputs can depend causally on measured temperatures. Exact information statements use noiseless measurements or a coupling with the same additive sensor-noise realization.

## Proposition 1: a calorimetric equivalence class

Let the four species obey $\dot c=F/V-D(t)c+\nu r$, with $\nu=(-1,-1,1,0)^T$ and $r=k(T)C_A$. Suppose the thermal dynamics depend on composition only through $C_A$ and $W(T,c)=\sum_i c_{p,i}(T)C_i$. Heat exchange can be any locally Lipschitz function of $T,T_t,u$ independent of the remaining chemical coordinates. Reaction enthalpy can depend on temperature, consistently or otherwise, without changing this statement.

For constant heat capacities, two initial states satisfying
$$\delta C_A=0,\quad\delta T=\delta T_t=0,\qquad
c_{p,B}\delta C_B+c_{p,C}\delta C_C+c_{p,M}\delta C_M=0$$
generate identical temperatures for every common admissible input, for as long as both trajectories exist in the physical domain. The chemical differences are
$$\delta c(t)=e^{-\int_0^tD(s)\,ds}\delta c(0).$$

Proof. Equal $C_A,T$ imply equal reaction rates. Subtraction of the species balances then gives homogeneous dilution for the remaining differences. Their calorimetric combination stays zero, so both thermal derivatives agree. Uniqueness closes the argument. Under causal feedback, equal histories imply equal next actions, and uniqueness continues the equality. There are two independent chemical directions in this kernel. Thus the six free states cannot be locally reconstructed in full. The observable quotient has at most four coordinates $(C_A,W,T,T_t)$. This is a sufficient construction of indistinguishability, not a claim that all indistinguishable pairs have this form.

This result survives restoring reciprocal heat transfer between jacket and reactor. Therefore the absence of jacket feedback is not, by itself, the cause of the two-dimensional composition ambiguity.

## Proposition 1b: functional heat-capacity rank

Define the linear space
$$\mathcal S=\operatorname{span}\{(c_{p,B}(T),c_{p,C}(T),c_{p,M}(T)):T\in\mathcal I\}.$$
Every difference with $\delta C_A=0$ and $(\delta C_B,\delta C_C,\delta C_M)\in\mathcal S^\perp$ satisfies the same construction. Its dimension is $3-\dim\mathcal S$.

Proof. Its thermal capacity difference vanishes at every temperature in $\mathcal I$. The species differences all acquire the same scalar dilution factor. The preceding proof applies unchanged, including temperature-dependent reaction enthalpy and feed sensible enthalpies. For constant Cp, rank is one. For species-wise affine Cp(T), rank is at most two, leaving at least one invisible direction. For independent quadratic Cp functions, this particular kernel can disappear. The absence of this kernel is NOT a proof of complete nonlinear observability: other symmetries, singular operating states and poor sensitivity may remain.

A useful sensor-design consequence follows. A scalar chemical measurement $a^Tc$ resolves product on a given equivalence class only if
$$\ker(a^T|_{\mathcal N})\subseteq\ker(e_C^T|_{\mathcal N}),$$
where $\mathcal N$ is the invisible chemical subspace. Measuring $C_C$ directly satisfies this requirement, while an arbitrary additional concentration need not. Known $C_A+C_C$ also determines product once $C_A$ is identified, but its initial value is additional information.


## Proposition 1c: a bad constant input and a local quotient test

For M0 with constant inputs, write $A=C_A$, $W=\sum c_{p,i}C_i$,
$q=F_A/V$, $c=F_{cp}/V$, $n=c_{p,C}-c_{p,A}-c_{p,B}$,
$a(T)=[Q(T)+F_{cp}(T_0-T)]/V$ and $b(T)=-\Delta H_r k(T)$.
Then
$\dot A=q-(D+k)A,\quad\dot W=c-DW+nkA,\quad
g=\dot T=(a+bA)/W.$
At a chemical/thermal stationary point with $\dot A=0$ and $a+bA=0$, arbitrary sufficiently small perturbations of B, C and M leave A and both temperatures constant under this same fixed input. They merely change W and decay with dilution. Thus three chemical directions are invisible under this particular unexcited experiment, although only two belong to the preceding all-input calorimetric family. Excitation can distinguish the extra direction. This is a property of a fixed input experiment, not a claim of a three-dimensional all-input symmetry.

A useful sufficient local test uses the gradients of $T,T_t,L_fT,L_f^2T$ on the quotient $(A,W,T,T_t)$. The relevant two-by-two minor for $(A,W)$ is
$\det\begin{bmatrix}g_A&g_W\\(L_fg)_A&(L_fg)_W\end{bmatrix}
=-\frac{b[bq+(D+k)a]}{W^3}
+\frac{(a+bA)[-ba_T+bc+ab_T-ank]}{W^4}.$
This follows by differentiating
$L_fg=\frac{bq+Da-bkA}{W}
+\frac{(a+bA)(a_T+b_TA-c-nkA)}{W^2}.$
A nonzero minor is sufficient for rank four of this local quotient observability test. It vanishes at the nominal equilibrium under the constant input. A zero value alone does not prove unobservability; the explicit invariant-trajectory construction above proves the special equilibrium case. The six-state model still has rank at most four under the all-input symmetry. Numerical arbitrary-precision evaluations are supporting local computations, not a global rank theorem.

## Proposition 2: estimation and tracking bounds

Let two possible product concentrations at time $t$ have separation $\Delta(t)$. Any estimator based on their common information has the same output in both worlds, hence
$$\max_i|\hat C_C(t)-C_C^{(i)}(t)|\geq\Delta(t)/2.$$
The proof is the triangle inequality. The midpoint attains the bound if precisely those two values are the only possibilities, so the two-point bound is sharp under that information model.

The same inequality holds with a common tracking reference in place of the estimate. Integrating gives a different, trajectory-level statement:
$$\max_i\operatorname{IAE}_i(H)\geq\frac12\int_0^H\Delta(t)\,dt.$$
For constant dilution and initial separation $\Delta_0$, the right-hand side is $\Delta_0(1-e^{-DH})/(2D)$. This is a bound on worst-case tracking error, not on regret relative to a state-informed oracle. The oracle may itself have unavoidable transient tracking loss. Decay of these bounds by dilution is physical replacement of the unknown initial inventory, not information supplied by the sensors.

For a fixed open-loop input and two Gaussian observation records with the same known covariance $\Sigma$, their KL divergence is $\frac12(\mu_1-\mu_2)^T\Sigma^{-1}(\mu_1-\mu_2)$. A two-world expected absolute estimation-risk bound is $\Delta(1-\mathrm{TV})/2$; using Pinsker gives the nonnegative bound $\Delta\max(0,1-\sqrt{\mathrm{KL}/2})/2$. This does not apply unchanged to adaptive noisy feedback with action-dependent product separation. The present campaign does not claim an industrial stochastic lower bound from this formula.

## Proposition 3: state ambiguity versus decision conflict

Let a finite set of indistinguishable worlds have continuous costs $J_i$ on a common nonempty compact feasible action-sequence set $\mathcal U$. Let $J_i^*=\min_{u\in\mathcal U}J_i(u)$. Define
$$\mathcal R^*=\min_{u\in\mathcal U}\max_i[J_i(u)-J_i^*].$$
Then $\mathcal R^*=0$ if and only if the worlds' minimizing sets have a common point. Otherwise $\mathcal R^*>0$.

Proof. Regrets are nonnegative. A common minimizer makes every regret zero. Conversely, continuity and compactness give a minimizer of the maximum regret; if its value is zero, that point minimizes every cost. Disjoint minimizers therefore imply a strictly positive attained value. Large chemical separation can coexist with zero decision regret when all worlds prefer the same action, including common actuator saturation.

If world-specific feasibility sets differ, evaluate individual optima in their declared sets and the robust decision in their intersection. An empty intersection is infeasibility, not finite regret. Numerical results explicitly mark absent common feasible candidates.


## Proposition 3b: when representing ambiguity cannot change the expected-cost action

For the exact PG twins with the same known feed history, coolant flow does not change the dilution rate. Let the possible products under any common plan be $C_C(t;u,\delta)=C_C(t;u,0)+d(t)\delta$, with $d(t)=e^{-\int_0^tD(s)ds}$ independent of the optimized coolant plan. Suppose the distribution over offsets has zero mean, all representatives remain physically admissible, the feasibility constraints depend only on their common thermal states and actions, and the tracking cost is a fixed weighted sum of squared product errors plus common thermal and actuation costs. Then
$\mathbb E_\delta J_\delta(u)=J_0(u)+\mathbb E[\delta^2]\sum_j w_jd(t_j)^2,$
where the final term is independent of $u$. Therefore nominal and expected-cost optimization have exactly the same minimizing action set. The result holds for both finite and continuous action classes under these assumptions.

Proof. Expand each squared error and average. The cross term vanishes by the zero-mean offset, while all other costs and constraints are shared. This is a certainty-equivalence special case, not a universal robustness theorem. Nonquadratic losses, action-dependent dilution, asymmetrically truncated beliefs, state-dependent physical constraints or a changed information policy can invalidate it. In the implemented symmetric three-representative P1 experiment it predicts a null control benefit, apart from admissibility exclusions and numerical tie handling. This is a falsification of any claim that merely including those symmetric worlds must improve this quadratic NMPC.

## Proposition 4: a conditional quantitative regret bound

If two costs are $\mu$-strongly convex on the same convex action set and have respective minimizers $u_1^*,u_2^*$, then
$$\mathcal R^*\geq\frac{\mu}{8}\|u_1^*-u_2^*\|^2.$$
Strong convexity and first-order optimality yield $J_i(u)-J_i(u_i^*)\geq\mu\|u-u_i^*\|^2/2$. At least one distance is at least half the distance between the minimizers, proving the bound. Convexity also prevents improvement by randomizing actions when the criterion is maximum expected cost. These convexity conditions are NOT established for the nonlinear PG optimization. Accordingly no numerical PG regret is described as certified by this bound.

For exact indistinguishability over a whole horizon and deterministic noiseless causal policies whose realizable sequences belong to $\mathcal U$, every policy realizes a common sequence. Its maximum regret is at least the minimax value over $\mathcal U$. A finite candidate grid supplies an exact result only within that grid. If the per-world oracle costs are held fixed at their continuous optima, restricting the decision set gives an upper bound on the continuous minimax value. Here both the decisions and the per-world oracle optima are restricted to the grid. Consequently the reported value has no general one-sided bound relative to continuous minimax regret. It is not a lower bound valid for all physical controllers. If future measurements can distinguish the worlds, open-loop sequence regret cannot be substituted for the value of an optimal adaptive policy.

## Known scope versus possible contribution

Observability, detectability, two-point risk bounds, minimax regret and decision-aware estimation are established concepts. The proofs above are elementary specializations and should not be advertised as a new universal control law. The candidate case-specific contribution is the functional-Cp classification, its application to a traced PG model, and an audit connecting physical closure, distinguishability, chemical sampling and decision cost. A comprehensive novelty review and calibrated physical data are still needed.
