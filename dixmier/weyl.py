import sympy as sp
t = sp.Symbol('t')   # theta = x*d

# Element of A_1: dict {weight w: poly in theta}, meaning sum f_w(theta) v_w,
# v_w = x^w (w>0), d^{-w} (w<0), v_0 = 1.
def clean(e): return {w:sp.expand(f) for w,f in e.items() if sp.expand(f)!=0}

def phi(c, shift=0):   # x^c d^c = theta(theta-1)...(theta-c+1), shifted
    return sp.prod([t + shift - j for j in range(c)])
def psi(c, shift=0):   # d^c x^c = (theta+1)...(theta+c), shifted
    return sp.prod([t + shift + j for j in range(1, c+1)])

def vmul(w1, w2):
    # v_{w1} v_{w2} = mu(theta) v_{w1+w2}
    if w1 >= 0 and w2 >= 0: return sp.Integer(1)
    if w1 <= 0 and w2 <= 0: return sp.Integer(1)
    if w1 > 0 and w2 < 0:
        c = -w2
        if w1 >= c:  return phi(c, -(w1 - c))     # x^{w1} d^c = phi_c(theta-(w1-c)) x^{w1-c}
        else:        return phi(w1)               # = phi_{w1}(theta) d^{c-w1}
    else:  # w1 < 0 < w2
        c = -w1
        if w2 >= c:  return psi(c)                # d^c x^{w2} = psi_c(theta) x^{w2-c}
        else:        return psi(w2, c - w2)       # = psi_{w2}(theta + c - w2) d^{c-w2}

def mul(e1, e2):
    out = {}
    for w1, f in e1.items():
        for w2, g in e2.items():
            coef = sp.expand(f * g.subs(t, t - w1) * vmul(w1, w2))
            out[w1+w2] = sp.expand(out.get(w1+w2, 0) + coef)
    return clean(out)

def comm(a, b):
    m1, m2 = mul(a, b), mul(b, a)
    ws = set(m1) | set(m2)
    return clean({w: m1.get(w,0) - m2.get(w,0) for w in ws})

def add(*es):
    out={}
    for e in es:
        for w,f in e.items(): out[w]=sp.expand(out.get(w,0)+f)
    return clean(out)

def smul(c,e): return clean({w:sp.expand(c*f) for w,f in e.items()})

# cross-check kernel against independent normal-ordering formula on x^a d^b basis
def to_xd(e):
    # convert to normal-ordered dict {(a,b): coeff} using x^a d^b basis
    x, d = sp.symbols('xx dd', commutative=True)  # bookkeeping only
    out = {}
    for w, f in e.items():
        # f(theta) v_w : for w>=0, f(theta) x^w = x^w f(theta+w); ff_k(theta) after x^w gives x^{w+k} d^k.
        # for w<0, ff_k(theta) d^c = x^k d^{k+c} directly.
        if w >= 0: f = f.subs(t, t + w)
        # falling factorial expansion: f(t) = sum c_k * t(t-1)...(t-k+1)
        rem = sp.expand(f); k = 0; coeffs = {}
        while rem != 0:
            c = sp.Rational(1, sp.factorial(k)) * rem.subs(t, k)  # ff_j(k)=0 for j>k, ff_k(k)=k!
            if c != 0: coeffs[k] = c
            rem = sp.expand(rem - c * sp.prod([t - i for i in range(k)]))
            k += 1
            if k > 60: raise RuntimeError
        for k2, c in coeffs.items():
            if w >= 0: key = (k2 + w, k2)
            else:      key = (k2, k2 - w)
            out[key] = sp.expand(out.get(key, 0) + c)
    return {k: v for k, v in out.items() if v != 0}

def xd_mul(m1, m2):
    # (x^a d^b)(x^c d^e) = sum_k C(b,k) c!/(c-k)! x^{a+c-k} d^{b+e-k}
    out = {}
    for (a,b), c1 in m1.items():
        for (c,e), c2 in m2.items():
            for k in range(0, min(b,c)+1):
                co = c1*c2*sp.binomial(b,k)*sp.ff(c,k)
                key = (a+c-k, b+e-k)
                out[key] = sp.expand(out.get(key,0)+co)
    return {k:v for k,v in out.items() if v != 0}

if __name__ == '__main__':
    import random
    random.seed(1)
    for trial in range(30):
        e1 = {random.randint(-3,3): sp.Integer(random.randint(-2,2))*t**random.randint(0,2)+random.randint(-2,2)}
        e2 = {random.randint(-3,3): sp.Integer(random.randint(-2,2))*t**random.randint(0,2)+random.randint(-2,2)}
        lhs = to_xd(mul(e1,e2))
        rhs = xd_mul(to_xd(e1), to_xd(e2))
        ws = set(lhs)|set(rhs)
        assert all(sp.expand(lhs.get(k,0)-rhs.get(k,0))==0 for k in ws), (e1,e2)
    print('kernel validated: GWA arithmetic == independent normal-ordering formula (30 random products)')
    # positive control: classical tame pair P = d + x^2, Q = -x
    P = {-1: sp.Integer(1), 2: sp.Integer(1)}
    Q = {1: sp.Integer(-1)}
    print('[Q,P] for (d+x^2, -x):', comm(Q,P))
