from darwin.dashboard import app

def test_health_and_data():
    c=app.test_client();assert c.get('/api/health').json['ok']
    d=c.get('/api/data');assert d.status_code==200 and d.json['available']
    assert 'A_rich' in d.json['summary'] and 'A_rich' in d.json['traces']

def test_input_validation_and_export():
    c=app.test_client();assert c.post('/api/run',json={'scenario':'../../passwd'}).status_code==400
    assert c.post('/api/run',json={'seed':-1}).status_code==400
    assert c.get('/api/export/estimation.csv').status_code==200
    assert c.get('/api/export/unknown.csv').status_code==404

def test_real_simulation_endpoint():
    c=app.test_client();d=c.post('/api/run',json={'scenario':'A_rich','seed':891}).json
    assert len(d['truth'])==121 and 'Darwin' in d['methods'] and d['seed']==891
    assert d['truth'][0]!=d['truth'][-1]
