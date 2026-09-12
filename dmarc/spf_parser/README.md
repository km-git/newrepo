SPF parser (RFC 7208). Counts DNS-causing mechanisms (`include`, `a`, `mx`,
`ptr`, `exists`, `redirect`) and warns above the 10-lookup budget, on missing
`all`, and on `+all`. CLI: `dmarc spf parse --domain example.com.au`. Primary
tools: dnspython plus this custom parser. Does not change DNS.
