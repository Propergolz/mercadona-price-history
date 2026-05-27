# Configuracion en GitHub

## Crear repositorio privado

1. En GitHub, crea un repositorio privado.
2. Nombre sugerido: `mercadona-price-history`.
3. No hace falta anadir README desde GitHub si vas a subir esta carpeta.

## Subir el proyecto

Desde PowerShell:

```powershell
cd C:\Users\sergi\Documents\mercadona-price-history
git init
git add .
git commit -m "Initial Mercadona price history project"
git branch -M main
git remote add origin https://github.com/OWNER/mercadona-price-history.git
git push -u origin main
```

Cambia `OWNER` por tu usuario de GitHub.

## Activar la captura

GitHub detectara el workflow:

```text
.github/workflows/daily-capture.yml
```

Puedes probarlo manualmente:

```text
Actions > Daily Mercadona price capture > Run workflow
```

Si la ejecucion termina bien, veras un commit automatico con nuevos archivos en `data/`.

## Coste

Con GitHub Free hay minutos gratuitos mensuales para Actions en repos privados. Este workflow diario deberia consumir muy poco. Aun asi, revisa el uso en:

```text
GitHub > Settings > Billing and plans > Usage
```

