RUA aggregate ingest. Parses RFC 7489 XML (plain, gzip, zip) from a directory,
shipped fixtures, or IMAP (`DMARC_IMAP_PASS` only — never a repo secret).
parsedmarc remains the optional primary CLI (`parsedmarc --config parsedmarc.ini`);
this module ships a built-in parser so the toolkit runs without Elasticsearch.
Honest gap: the operator must publish `rua=mailto:dmarc@customer-domain`.
