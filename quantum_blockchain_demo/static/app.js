// web/static/app.js
async function callAPI(path, method='GET', body=null){
  const options = { method, headers: {} };
  if(body) { options.headers['Content-Type']='application/json'; options.body = JSON.stringify(body); }
  const res = await fetch(path, options);
  return res.json();
}

document.getElementById('genKeysBtn').onclick = async () => {
  const data = await callAPI('/generate_keys');
  document.getElementById('keysOutput').textContent = JSON.stringify(data, null, 2);
  // Autofill public/private into fields for demo
  document.getElementById('privateKeyPem').value = data.private_key_pem;
  document.getElementById('publicKeyPem').value = data.public_key_pem;
};

document.getElementById('signBtn').onclick = async () => {
  const priv = document.getElementById('privateKeyPem').value;
  const pub = document.getElementById('publicKeyPem').value;
  const recipient = document.getElementById('recipient').value;
  const amount = parseFloat(document.getElementById('amount').value);

  if(!priv || !recipient || !amount) { alert('private key, recipient, amount required'); return; }
  const data = await callAPI('/sign', 'POST', { private_key_pem: priv, public_key_pem: pub, recipient, amount });
  document.getElementById('signatureOutput').textContent = JSON.stringify(data, null, 2);
};

document.getElementById('sendTxBtn').onclick = async () => {
  const pub = document.getElementById('publicKeyPem').value;
  const signJson = JSON.parse(document.getElementById('signatureOutput').textContent || '{}');
  const signature = signJson.signature;
  const recipient = document.getElementById('recipient').value;
  const amount = parseFloat(document.getElementById('amount').value);

  if(!pub || !signature){ alert('generate keys and sign first'); return; }
  const tx = { sender_public_key: pub, recipient, amount, signature };
  const res = await callAPI('/new_transaction', 'POST', tx);
  document.getElementById('sendTxOutput').textContent = JSON.stringify(res, null, 2);
};

document.getElementById('mineBtn').onclick = async () => {
  const res = await callAPI('/mine');
  document.getElementById('mineOutput').textContent = JSON.stringify(res, null, 2);
};

document.getElementById('showChainBtn').onclick = async () => {
  const res = await callAPI('/get_chain');
  document.getElementById('chainOutput').textContent = JSON.stringify(res, null, 2);
};

document.getElementById('validateBtn').onclick = async () => {
  const res = await callAPI('/validate_chain');
  document.getElementById('validateOutput').textContent = JSON.stringify(res, null, 2);
};
async function callAPI(path, method='GET', body=null) {
  const res = await fetch(path, {
    method,
    headers: {'Content-Type':'application/json'},
    body: body ? JSON.stringify(body) : undefined
  });
  return res.json();
}

document.getElementById('fetchApiBtn').onclick = async () => {
  const lat = parseFloat(document.getElementById('apiLat').value);
  const lon = parseFloat(document.getElementById('apiLon').value);
  const res = await callAPI('/fetch_weather', 'POST', {lat, lon, use_mine: true});
  document.getElementById('fetchApiOutput').textContent = JSON.stringify(res, null, 2);
};

document.getElementById('verifyBtn').onclick = async () => {
  const idx = parseInt(document.getElementById('verifyIndex').value);
  const res = await callAPI('/verify_api_block', 'POST', {block_index: idx});
  document.getElementById('verifyOutput').textContent = JSON.stringify(res, null, 2);
};
