# Changelog

## 1.0.21

- Fix: Addon startete nicht mehr (Supervisor-Status "error"). Beim Binden des
  Webservers löste die Reverse-DNS-Abfrage des Hostnamens einen
  UnicodeDecodeError aus, wenn der PTR-Eintrag kein gültiges UTF-8 ist.
  Die Abfrage ist jetzt abgesichert, der Server startet auch dann.
- Server läuft jetzt threaded, damit parallele Abrufe sich nicht blockieren.
