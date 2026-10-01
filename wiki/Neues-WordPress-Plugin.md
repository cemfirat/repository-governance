# Neues WordPress Plugin

## 1. Profil wählen

- `simple` – kleines, fokussiertes Utility-Plugin.
- `application` – umfangreicheres Plugin mit Integrationen, Datenflüssen, APIs oder größerer Admin-Oberfläche.
- `block` – Block-Plugin; Produktcode zuerst mit dem offiziellen WordPress-`@wordpress/create-block`-Tool aufsetzen.

Siehe [[Plugin Profile]].

## 2. Fakten festlegen

Vor dem Scaffold müssen mindestens geklärt sein:

- Plugin-Slug;
- Name und Zweck;
- WordPress-/PHP-Mindestversion;
- Lizenzmodell;
- Distribution;
- Update-Modell;
- Repository-Name;
- gegebenenfalls abweichender Package-Root.

Governance darf diese Entscheidungen nicht erraten.

## 3. Scaffold erzeugen

Beispiel für ein einfaches GitHub-verteiltes Plugin:

```bash
python3 scripts/wordpress-plugin-scaffold.py \
  --destination ../wordpress-example-plugin \
  --profile simple \
  --slug wordpress-example-plugin \
  --name "WordPress Example Plugin" \
  --description "Adds a focused example capability to WordPress." \
  --license-mode managed-gpl \
  --distribution github-releases \
  --updates none \
  --repository cemfirat/wordpress-example-plugin
```

Der Generator schreibt nicht nach GitHub, überschreibt kein nicht-leeres Ziel und erfindet keinen Updater.

## 4. Danach

Repository anlegen, Produktcode entwickeln, echte Tests ergänzen und ab dann immer nach [[Arbeitsablauf]] arbeiten.
