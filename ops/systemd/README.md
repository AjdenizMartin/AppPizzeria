# Print Agent (systemd)

Autoarranque recomendado para Linux en restaurante.

## Instalar servicio

Desde la raíz del proyecto:

```bash
./ops/systemd/install_print_agent_service.sh /opt/pizzeria-app restaurant
```

Parámetros:

1. `APP_DIR` (default: `/opt/pizzeria-app`)
2. `RUN_USER` (default: usuario actual)
3. `PYTHON_BIN` (default: `APP_DIR/.venv/bin/python`)

## Configurar variables

Editar:

```bash
sudo nano /etc/pizzeria-print-agent.env
```

Mínimo obligatorio:

```env
PRINT_AGENT_KEY=la_misma_clave_que_backend
PRINT_AGENT_API_URL=https://app.tudominio.com
```

Reiniciar tras cambios:

```bash
sudo systemctl restart pizzeria-print-agent.service
```

## Comandos útiles

```bash
sudo systemctl status pizzeria-print-agent.service
sudo journalctl -u pizzeria-print-agent.service -f
```

## Desinstalar

```bash
./ops/systemd/uninstall_print_agent_service.sh
```
