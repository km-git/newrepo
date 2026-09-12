DKIM TXT checker. Resolves `selector._domainkey.domain` for google, selector1,
selector2, k1, s1, s2, cm, default, plus any customer selector. Uses
cryptography to measure RSA public-key length (<1024 warning, <2048 advisory).
CLI: `dmarc dkim check --domain example.com.au --selector google`.
