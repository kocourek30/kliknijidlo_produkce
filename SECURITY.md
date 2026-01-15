# Security Policy

## 🔒 Security Features

KlikniJídlo v2 implementuje následující bezpečnostní funkce:

### Django Security Settings

- **HTTPS/SSL Enforcement**: Všechny požadavky jsou přesměrovány na HTTPS v produkci
- **HSTS (HTTP Strict Transport Security)**: 1 rok s preload
- **Secure Cookies**: SESSION a CSRF cookies jsou označeny jako secure a httponly
- **CSRF Protection**: Ochrana proti Cross-Site Request Forgery útokům
- **XSS Protection**: Secure Content-Type a X-XSS-Protection headers
- **Clickjacking Protection**: X-Frame-Options nastaveno na DENY
- **Referrer Policy**: strict-origin-when-cross-origin

### Authentication & Authorization

- **Strong Password Requirements**: Minimálně 8 znaků s validací
- **Session Management**: 4 hodinový timeout
- **Custom User Model**: Rozšířený uživatelský model
- **Permission-Based Access**: Granular permissions pro různé role

### Database Security

- **Connection Pooling**: Optimalizované DB připojení
- **SQL Injection Protection**: Django ORM automaticky escapuje dotazy
- **Prepared Statements**: Všechny dotazy používají prepared statements

### File Upload Security

- **Size Limits**: Maximální velikost souboru 5MB
- **File Permissions**: Správné UNIX permissions (644 pro soubory, 755 pro adresáře)
- **Allowed Extensions**: Whitelist povolených přípon

### Logging & Monitoring

- **Security Logs**: Samostatný log pro bezpečnostní události
- **Error Logging**: Rotované logy s retencí
- **Admin Email Alerts**: Automatické notifikace při chybách

---

## ⚙️ Bezpečnostní konfigurace

### Před nasazením na produkci

1. **Spusť bezpečnostní kontrolu**:
   ```bash
   python check_security.py
   ```

2. **Spusť Django deployment check**:
   ```bash
   python manage.py check --deploy
   ```

3. **Ověř nastavení v .env**:
   - `DEBUG=False`
   - Nový `SECRET_KEY`
   - Platná `ALLOWED_HOSTS`
   - HTTPS nastavení zapnuta

### Doporučené dodatky

1. **Fail2Ban**: Ochrana proti brute-force útokům
   ```bash
   sudo apt install fail2ban
   ```

2. **Django-Axes**: Rate limiting pro login
   ```bash
   pip install django-axes
   ```

3. **Změna Admin URL**: Změníte `/admin/` na něco méně předvídatežného

4. **Two-Factor Authentication**: Zvažte přidání 2FA pro admin účty

---

## 🚨 Nahlášení bezpečnostních chyb

### Reporting a Vulnerability

Pokud najdete bezpečnostní chybu, prosím:

1. **NE🚫vytářejte public issue** na GitHubu
2. **O🚫 zaslete email** na: kocourek30@gmail.com
3. Uveďte:
   - Popis zranitelnosti
   - Kroky k reprodukci
   - Možný dopad
   - Návrh řešení (pokud máte)

### Response Timeline

- **24 hodin**: Potvrzení přijetí
- **7 dnů**: První analýza a feedback
- **30 dnů**: Oprava a release (pokud je critical)

### Severity Levels

- **Critical**: Okamžitá akce (RCE, SQL injection, auth bypass)
- **High**: Oprava do 7 dnů (XSS, CSRF, privilege escalation)
- **Medium**: Oprava do 30 dnů (information disclosure, DoS)
- **Low**: Oprava v příštím release (minor issues)

---

## 🛡️ Security Best Practices

### Pro administrátory

1. **Silná hesla**:
   - Minimálně 12 znaků
   - Kombinace písmen, čísel a speciálních znaků
   - Použijte password manager

2. **Pravidelné aktualizace**:
   ```bash
   pip list --outdated
   pip install -U Django
   ```

3. **Monitoring logů**:
   ```bash
   tail -f logs/security.log
   grep "FAILED" logs/security.log
   ```

4. **Zálohy**:
   - Denní zálohy databáze
   - Týenní zálohy media souborů
   - Testování obnovení měsíčně

5. **Přístupová práva**:
   - Princip nejmenších oprávnění
   - Pravidelná revize uživatelských účtů
   - Deaktivace nepřístupných účtů

### Pro vývojáře

1. **Nikdy necommitujte**:
   - `.env` soubory
   - Hesla nebo API klíče
   - SSH klíče
   - Databázové dumpy s citlivými daty

2. **Code Review**:
   - Všechny změny procházejí code review
   - Kontrola bezpečnosti před mergem
   - Použití pull requestů

3. **Dependencies**:
   - Pravidelná aktualizace závislostí
   - Kontrola známých zranitelností
   - Pin verze v production

4. **Testing**:
   - Unit testy pro kritickou funkcionalitu
   - Security testy pro authentication
   - Penetrační testování před major releases

---

## 📊 Security Checklist

### Denně
- [ ] Zkontrolovat security logs
- [ ] Zkontrolovat failed login attempts
- [ ] Ověřit zálohy proběhly

### Týdně
- [ ] Review Django error logs
- [ ] Kontrola diskového prostoru
- [ ] Kontrola nevyřízených bezpečnostních alertů

### Měsíčně
- [ ] Aktualizace bezpečnostních patchů
- [ ] Review uživatelských účtů a oprávnění
- [ ] Test obnovení ze záloh
- [ ] SSL certifikát renewal check
- [ ] Security headers test (securityheaders.com)
- [ ] SSL test (ssllabs.com)

### Čtvrtletně
- [ ] Full security audit
- [ ] Penetrační testování
- [ ] Review a update security policies
- [ ] Security training pro tým

---

## 📝 Incident Response

### Při bezpečnostním incidentu

1. **Okamžitě**:
   - Izolovat postiité systémy
   - Změnit všechna hesla
   - Zablokovat kompromitigované účty

2. **Do 1 hodiny**:
   - Identifikovat rozsah incidentu
   - Začít sbírat logy a evidence
   - Informovat administrátory

3. **Do 24 hodin**:
   - Analýza příčiny
   - Implementace hot-fixů
   - Komunikace s postiitými uživateli
   - Nahlášení příslušným úřadům (pokud je nutné)

4. **Post-Incident**:
   - Podrobná analýza
   - Aktualizace security procedures
   - Implementace preventivních opatření
   - Dokumentace lessons learned

---

## 🔗 Resources

### Django Security
- [Django Security Documentation](https://docs.djangoproject.com/en/5.2/topics/security/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

### Tools
- [Security Headers Check](https://securityheaders.com/)
- [SSL Labs Test](https://www.ssllabs.com/ssltest/)
- [Observatory by Mozilla](https://observatory.mozilla.org/)

### Updates
- [Django Security Releases](https://www.djangoproject.com/weblog/)
- [Python Security Advisories](https://python-security.readthedocs.io/)

---

## 📞 Contact

Pro bezpečnostní otázky kontaktujte:
- **Email**: kocourek30@gmail.com
- **GitHub**: [@kocourek30](https://github.com/kocourek30)

**Poznámka**: Pro kritické bezpečnostní problémy použijte email, ne public issues.
