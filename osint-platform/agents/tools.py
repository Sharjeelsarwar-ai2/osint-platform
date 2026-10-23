"""
Real OSINT Tools — All open-source, no paid APIs, Streamlit Cloud compatible.
Each function is callable by Groq agents via tool calling.
"""

import json
import socket
import ipaddress
import re
from collections import Counter

import dns.resolver
import whois
import requests
from duckduckgo_search import DDGS


# ═══════════════════════════════════════════════════════
#  DNS TOOLS
# ═══════════════════════════════════════════════════════

def dns_lookup(domain: str, record_type: str = "ALL") -> dict:
    """Perform DNS lookup for a domain. record_type: A, AAAA, MX, NS, TXT, SOA, CNAME, CAA, ALL"""
    types_to_query = (
        ['A', 'AAAA', 'MX', 'NS', 'TXT', 'SOA', 'CNAME', 'CAA']
        if record_type == "ALL"
        else [record_type.upper()]
    )
    results = {}
    for rtype in types_to_query:
        try:
            answers = dns.resolver.resolve(domain, rtype)
            results[rtype] = [str(r) for r in answers]
        except dns.resolver.NoAnswer:
            results[rtype] = []
        except dns.resolver.NXDOMAIN:
            results[rtype] = ["NXDOMAIN - Domain does not exist"]
        except dns.resolver.NoNameservers:
            results[rtype] = ["SERVFAIL - No nameservers responded"]
        except Exception as e:
            results[rtype] = [f"Error: {str(e)[:100]}"]
    return {"domain": domain, "records": results}


def enumerate_subdomains(domain: str) -> dict:
    """Attempt subdomain enumeration via DNS brute-force of common prefixes."""
    common_prefixes = [
        "www", "mail", "ftp", "admin", "api", "dev", "staging",
        "test", "blog", "shop", "app", "portal", "cdn", "docs",
        "status", "dashboard", "login", "vpn", "remote", "webmail",
        "mx", "ns1", "ns2", "git", "jenkins", "ci", "db", "redis",
        "elastic", "kibana", "grafana", "monitor", "backup"
    ]
    found = []
    for prefix in common_prefixes:
        subdomain = f"{prefix}.{domain}"
        try:
            answers = dns.resolver.resolve(subdomain, 'A')
            ips = [str(a) for a in answers]
            found.append({"subdomain": subdomain, "ips": ips})
        except Exception:
            pass
    return {
        "domain": domain,
        "subdomains_found": len(found),
        "subdomains": found,
        "prefixes_checked": len(common_prefixes)
    }


# ═══════════════════════════════════════════════════════
#  WHOIS TOOLS
# ═══════════════════════════════════════════════════════

def whois_lookup(domain: str) -> dict:
    """Perform WHOIS lookup for domain registration information."""
    try:
        w = whois.whois(domain)
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]
        expiration = w.expiration_date
        if isinstance(expiration, list):
            expiration = expiration[0]
        return {
            "domain": domain,
            "registrar": str(w.registrar) if w.registrar else "Unknown",
            "creation_date": str(creation) if creation else "Unknown",
            "expiration_date": str(expiration) if expiration else "Unknown",
            "updated_date": str(w.updated_date) if w.updated_date else "Unknown",
            "name_servers": w.name_servers if w.name_servers else [],
            "status": w.status if w.status else [],
            "org": str(w.org) if w.org else "Unknown",
            "country": str(w.country) if w.country else "Unknown",
            "whois_server": str(w.whois_server) if w.whois_server else "Unknown"
        }
    except Exception as e:
        return {"domain": domain, "error": str(e)[:200]}


# ═══════════════════════════════════════════════════════
#  HTTP SECURITY TOOLS
# ═══════════════════════════════════════════════════════

def check_security_headers(url: str) -> dict:
    """Analyze HTTP security headers for a URL."""
    if not url.startswith("http"):
        url = "https://" + url

    important_headers = {
        "Strict-Transport-Security": {"desc": "HSTS - Forces HTTPS connections", "severity": "HIGH"},
        "Content-Security-Policy": {"desc": "CSP - Prevents XSS and injection", "severity": "HIGH"},
        "X-Content-Type-Options": {"desc": "Prevents MIME-type sniffing", "severity": "MEDIUM"},
        "X-Frame-Options": {"desc": "Prevents clickjacking attacks", "severity": "MEDIUM"},
        "X-XSS-Protection": {"desc": "Legacy XSS filter", "severity": "LOW"},
        "Referrer-Policy": {"desc": "Controls referrer information leakage", "severity": "MEDIUM"},
        "Permissions-Policy": {"desc": "Controls browser feature access", "severity": "MEDIUM"},
        "Cross-Origin-Opener-Policy": {"desc": "COOP - Isolates browsing context", "severity": "MEDIUM"},
        "Cross-Origin-Resource-Policy": {"desc": "CORP - Prevents cross-origin reads", "severity": "MEDIUM"}
    }

    try:
        resp = requests.get(url, timeout=15, allow_redirects=True,
                            headers={"User-Agent": "Mozilla/5.0 OSINTBot/1.0"})
        headers = resp.headers
        analysis = {}
        present_count = 0

        for header, info in important_headers.items():
            value = headers.get(header)
            is_present = value is not None
            if is_present:
                present_count += 1
            analysis[header] = {
                "present": is_present,
                "value": value[:200] if value else "MISSING",
                "description": info["desc"],
                "risk_if_missing": info["severity"]
            }

        score = round((present_count / len(important_headers)) * 100)
        return {
            "url": url,
            "status_code": resp.status_code,
            "server": headers.get("Server", "Hidden"),
            "powered_by": headers.get("X-Powered-By", "Hidden"),
            "score": score,
            "headers_present": present_count,
            "headers_total": len(important_headers),
            "analysis": analysis
        }
    except requests.exceptions.SSLError:
        return {"url": url, "error": "SSL/TLS certificate error - site may have invalid cert", "score": 0}
    except Exception as e:
        return {"url": url, "error": str(e)[:200], "score": 0}


def check_ssl_info(domain: str) -> dict:
    """Check SSL/TLS certificate information via socket connection."""
    try:
        import ssl
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
            s.settimeout(10)
            s.connect((domain, 443))
            cert = s.getpeercert()
            cipher = s.cipher()
            return {
                "domain": domain,
                "ssl_version": s.version(),
                "cipher_name": cipher[0] if cipher else "Unknown",
                "cipher_bits": cipher[2] if cipher else 0,
                "subject": dict(x[0] for x in cert.get("subject", ())),
                "issuer": dict(x[0] for x in cert.get("issuer", ())),
                "not_before": cert.get("notBefore", "Unknown"),
                "not_after": cert.get("notAfter", "Unknown"),
                "san": cert.get("subjectAltName", [])
            }
    except ssl.SSLCertVerificationError as e:
        return {"domain": domain, "error": f"Certificate verification failed: {str(e)[:150]}", "valid": False}
    except Exception as e:
        return {"domain": domain, "error": str(e)[:150], "valid": False}


# ═══════════════════════════════════════════════════════
#  IP ANALYSIS TOOLS
# ═══════════════════════════════════════════════════════

def analyze_ip(ip_address: str) -> dict:
    """Analyze an IP address for type, geolocation hints, and reputation."""
    try:
        ip = ipaddress.ip_address(ip_address)
        result = {
            "ip": str(ip),
            "version": f"IPv{ip.version}",
            "is_private": ip.is_private,
            "is_reserved": ip.is_reserved,
            "is_loopback": ip.is_loopback,
            "is_multicast": ip.is_multicast,
            "is_global": ip.is_global,
            "is_link_local": ip.is_link_local
        }
        try:
            result["reverse_dns"] = socket.getfqdn(ip_address)
        except Exception:
            result["reverse_dns"] = "No reverse DNS"
        return result
    except ValueError as e:
        return {"error": f"Invalid IP: {str(e)}"}


def resolve_domain_to_ips(domain: str) -> dict:
    """Resolve a domain to all its IP addresses."""
    ips = {"ipv4": [], "ipv6": []}
    try:
        for rdata in dns.resolver.resolve(domain, 'A'):
            ips["ipv4"].append(str(rdata))
    except Exception:
        pass
    try:
        for rdata in dns.resolver.resolve(domain, 'AAAA'):
            ips["ipv6"].append(str(rdata))
    except Exception:
        pass
    return {"domain": domain, "ips": ips, "total": len(ips["ipv4"]) + len(ips["ipv6"])}


# ═══════════════════════════════════════════════════════
#  EMAIL OSINT TOOLS
# ═══════════════════════════════════════════════════════

def check_email_security(domain: str) -> dict:
    """Check email security records: SPF, DMARC, DKIM, MX."""
    results = {"domain": domain}

    # MX Records
    try:
        mx = dns.resolver.resolve(domain, 'MX')
        results["mx_records"] = [str(r) for r in mx]
        results["mail_servers"] = len(mx)
    except Exception:
        results["mx_records"] = []
        results["mail_servers"] = 0

    # SPF
    try:
        txt = dns.resolver.resolve(domain, 'TXT')
        spf = [str(r) for r in txt if 'v=spf1' in str(r)]
        results["spf"] = spf if spf else ["NOT CONFIGURED"]
        results["spf_configured"] = bool(spf)
    except Exception:
        results["spf"] = ["DNS ERROR"]
        results["spf_configured"] = False

    # DMARC
    try:
        dmarc = dns.resolver.resolve(f"_dmarc.{domain}", 'TXT')
        results["dmarc"] = [str(r) for r in dmarc]
        results["dmarc_configured"] = True
    except Exception:
        results["dmarc"] = ["NOT CONFIGURED"]
        results["dmarc_configured"] = False

    # DKIM (common selectors)
    dkim_found = []
    for selector in ["default", "google", "selector1", "selector2", "k1", "mail", "s1", "s2"]:
        try:
            dkim = dns.resolver.resolve(f"{selector}._domainkey.{domain}", 'TXT')
            dkim_found.append({"selector": selector, "record": str(dkim[0])[:100]})
        except Exception:
            pass
    results["dkim"] = dkim_found if dkim_found else ["No common DKIM selectors found"]
    results["dkim_configured"] = bool(dkim_found)

    # Overall email security score
    score = 0
    if results.get("spf_configured"):
        score += 33
    if results.get("dmarc_configured"):
        score += 34
    if results.get("dkim_configured"):
        score += 33
    results["email_security_score"] = score

    return results


# ═══════════════════════════════════════════════════════
#  THREAT INTELLIGENCE / SEARCH TOOLS
# ═══════════════════════════════════════════════════════

def search_threat_intel(query: str, max_results: int = 5) -> dict:
    """Search for threat intelligence, breach data, and security incidents."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f'"{query}" security breach vulnerability CVE exploit',
                max_results=max_results
            ))
        return {
            "query": query,
            "results": [
                {"title": r["title"], "snippet": r["body"][:300], "source": r["href"]}
                for r in results
            ],
            "count": len(results)
        }
    except Exception as e:
        return {"query": query, "error": str(e)[:200], "results": []}


def search_domain_reputation(domain: str) -> dict:
    """Search for domain reputation and abuse reports."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f'"{domain}" abuse phishing malware scam report',
                max_results=5
            ))
        return {
            "domain": domain,
            "reputation_mentions": [
                {"title": r["title"], "snippet": r["body"][:300], "source": r["href"]}
                for r in results
            ],
            "negative_mentions": len(results)
        }
    except Exception as e:
        return {"domain": domain, "error": str(e)[:200]}


def search_company_news(company: str, max_results: int = 5) -> dict:
    """Search for recent news about a company or domain."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(company, max_results=max_results))
        return {
            "company": company,
            "news": [
                {"title": r["title"], "source": r["source"], "date": r["date"], "url": r["url"]}
                for r in results
            ]
        }
    except Exception as e:
        return {"company": company, "error": str(e)[:200]}


# ═══════════════════════════════════════════════════════
#  TECHNOLOGY DETECTION
# ═══════════════════════════════════════════════════════

def detect_technologies(url: str) -> dict:
    """Detect web technologies from HTTP response headers and HTML."""
    if not url.startswith("http"):
        url = "https://" + url

    tech_signatures = {
        "Server Headers": {
            "nginx": "Nginx",
            "apache": "Apache",
            "cloudflare": "Cloudflare",
            "aws": "AWS",
            "gunicorn": "Gunicorn (Python)",
            "uvicorn": "Uvicorn (Python)",
            "express": "Express.js",
            "iis": "Microsoft IIS",
            "tomcat": "Apache Tomcat"
        },
        "Powered-By Headers": {
            "php": "PHP",
            "asp.net": "ASP.NET",
            "express": "Express.js",
            "next.js": "Next.js",
            "nuxt": "Nuxt.js"
        }
    }

    try:
        resp = requests.get(url, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0 OSINTBot/1.0"})
        headers = resp.headers
        html = resp.text[:50000].lower()
        detected = []

        # Check server header
        server = headers.get("Server", "").lower()
        for sig, name in tech_signatures["Server Headers"].items():
            if sig in server:
                detected.append({"technology": name, "source": "Server header", "confidence": "High"})

        # Check X-Powered-By
        powered = headers.get("X-Powered-By", "").lower()
        for sig, name in tech_signatures["Powered-By Headers"].items():
            if sig in powered:
                detected.append({"technology": name, "source": "X-Powered-By", "confidence": "High"})

        # Check HTML signatures
        html_sigs = {
            "wp-content": "WordPress",
            "wp-includes": "WordPress",
            "shopify": "Shopify",
            "squarespace": "Squarespace",
            "wix.com": "Wix",
            "react": "React",
            "vue.js": "Vue.js",
            "angular": "Angular",
            "jquery": "jQuery",
            "bootstrap": "Bootstrap",
            "tailwind": "Tailwind CSS",
            "google-analytics": "Google Analytics",
            "gtag": "Google Tag Manager",
            "cloudflare": "Cloudflare CDN",
            "akamai": "Akamai CDN",
            "fastly": "Fastly CDN",
            "vercel": "Vercel",
            "netlify": "Netlify",
            "stripe": "Stripe Payments",
            "recaptcha": "reCAPTCHA"
        }
        for sig, name in html_sigs.items():
            if sig in html:
                detected.append({"technology": name, "source": "HTML content", "confidence": "Medium"})

        # Remove duplicates
        seen = set()
        unique = []
        for d in detected:
            if d["technology"] not in seen:
                seen.add(d["technology"])
                unique.append(d)

        return {
            "url": url,
            "technologies_detected": len(unique),
            "technologies": unique,
            "server": headers.get("Server", "Hidden"),
            "status_code": resp.status_code
        }
    except Exception as e:
        return {"url": url, "error": str(e)[:200]}


# ═══════════════════════════════════════════════════════
#  TOOL REGISTRY (maps tool names to functions)
# ═══════════════════════════════════════════════════════

TOOL_REGISTRY = {
    "dns_lookup": dns_lookup,
    "enumerate_subdomains": enumerate_subdomains,
    "whois_lookup": whois_lookup,
    "check_security_headers": check_security_headers,
    "check_ssl_info": check_ssl_info,
    "analyze_ip": analyze_ip,
    "resolve_domain_to_ips": resolve_domain_to_ips,
    "check_email_security": check_email_security,
    "search_threat_intel": search_threat_intel,
    "search_domain_reputation": search_domain_reputation,
    "search_company_news": search_company_news,
    "detect_technologies": detect_technologies
}


def execute_tool(tool_name: str, tool_args: dict) -> dict:
    """Execute a tool by name with given arguments."""
    func = TOOL_REGISTRY.get(tool_name)
    if not func:
        return {"error": f"Unknown tool: {tool_name}. Available: {list(TOOL_REGISTRY.keys())}"}
    return func(**tool_args)


# ═══════════════════════════════════════════════════════
#  GROQ TOOL DEFINITIONS (JSON schemas for function calling)
# ═══════════════════════════════════════════════════════

GROQ_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "dns_lookup",
            "description": "Perform DNS lookup for a domain. Returns A, AAAA, MX, NS, TXT, SOA, CNAME, CAA records.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name e.g. example.com"},
                    "record_type": {"type": "string", "description": "DNS record type: A, AAAA, MX, NS, TXT, SOA, CNAME, CAA, or ALL", "default": "ALL"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enumerate_subdomains",
            "description": "Discover subdomains via DNS brute-force of common prefixes (www, api, dev, mail, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Base domain e.g. example.com"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "whois_lookup",
            "description": "Get WHOIS registration data: registrar, creation date, expiration, nameservers, org, country.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_security_headers",
            "description": "Analyze HTTP security headers (HSTS, CSP, X-Frame-Options, etc.) and score the site.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL or domain e.g. https://example.com"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_ssl_info",
            "description": "Check SSL/TLS certificate details: issuer, expiry, cipher, SAN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_ip",
            "description": "Analyze an IP address: version, private/public, reverse DNS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ip_address": {"type": "string", "description": "IP address e.g. 8.8.8.8"}
                },
                "required": ["ip_address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_domain_to_ips",
            "description": "Resolve domain to all IPv4 and IPv6 addresses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_email_security",
            "description": "Check email security: SPF, DMARC, DKIM records and MX servers. Returns security score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain name"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_threat_intel",
            "description": "Search for threat intelligence, breaches, CVEs, and exploits related to a target.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query e.g. domain name or company"},
                    "max_results": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_domain_reputation",
            "description": "Search for domain reputation, abuse reports, phishing, and malware mentions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain to check"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_company_news",
            "description": "Search for recent news articles about a company or domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company or domain name"},
                    "max_results": {"type": "integer", "default": 5}
                },
                "required": ["company"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_technologies",
            "description": "Detect web technologies, frameworks, CDNs, and services from HTTP headers and HTML.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to analyze"}
                },
                "required": ["url"]
            }
        }
    }
]