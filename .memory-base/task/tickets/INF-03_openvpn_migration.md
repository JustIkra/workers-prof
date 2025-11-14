ID: INF-03
Title: Миграция проекта на OpenVPN
Type: infrastructure
Priority: P2
Status: Planned
Owner: backend
Created: 2025-01-27

Кратко
— Добавить поддержку OpenVPN в дополнение к существующим WireGuard и AWG. Проект должен поддерживать выбор VPN-протокола через переменную окружения `VPN_TYPE=openvpn|wireguard|awg`.

Контекст
— В проекте уже реализована поддержка WireGuard и AWG (AmneziaWG) для доступа к Gemini API через VPN. Необходимо добавить поддержку OpenVPN для расширения возможностей выбора VPN-провайдера. Конфигурационный файл OpenVPN (`open_vpn.ovpn`) уже предоставлен.

Текущее состояние
— VPN реализован в `api-gateway/app/core/vpn_bootstrap.py`:
  - Поддерживаются типы: `wireguard`, `awg`
  - Конфигурация через переменные окружения: `VPN_ENABLED`, `VPN_TYPE`, `WG_CONFIG_PATH`
  - Split-tunnel маршрутизация: `all`, `domains`, `cidr`
  - Dockerfile устанавливает `wireguard-tools`
  - Конфигурации хранятся в `config/vpn/wireguard/` и `config/vpn/awg/`

Требования
1. Добавить поддержку `VPN_TYPE=openvpn`
2. Установить OpenVPN клиент в Dockerfile
3. Реализовать функции запуска/остановки OpenVPN в `vpn_bootstrap.py`
4. Поддержать split-tunnel маршрутизацию для OpenVPN (аналогично WireGuard)
5. Создать директорию `config/vpn/openvpn/` с примером конфигурации
6. Обновить документацию и переменные окружения

Зона изменений

- Backend (`api-gateway/app/core/vpn_bootstrap.py`):
  - Добавить функцию `ensure_openvpn_up(config_path, interface, timeout, poll_interval)`
  - Обновить `bootstrap_from_env()` для поддержки `VPN_TYPE=openvpn`
  - Адаптировать `configure_split_tunnel()` для работы с интерфейсом OpenVPN (обычно `tun0`)
  - Добавить проверку наличия бинарника `openvpn`
  - Обработать специфичные для OpenVPN ошибки (certificate validation, routing)

- Backend (`api-gateway/app/core/config.py`):
  - Обновить `vpn_type: Literal["wireguard", "awg", "openvpn"]`
  - Добавить `openvpn_config_path: str | None` (аналог `wg_config_path`)
  - Обновить валидацию: если `VPN_TYPE=openvpn`, требуется `OPENVPN_CONFIG_PATH`

- Dockerfile (`Dockerfile.multistage`):
  - Добавить установку `openvpn` пакета в секцию system dependencies
  - Обновить комментарии о поддержке VPN-протоколов

- Конфигурация (`config/vpn/openvpn/`):
  - Создать директорию `config/vpn/openvpn/`
  - Создать `README.md` с описанием настройки OpenVPN
  - Создать `openvpn.conf.example` (шаблон на основе `open_vpn.ovpn`)
  - Документировать переменные окружения для OpenVPN

- Документация:
  - Обновить `PRODUCTION_ENV_GUIDE.md` с примерами для OpenVPN
  - Обновить `CLAUDE.md` в секции VPN
  - Обновить `config/vpn/wireguard/README.md` с упоминанием OpenVPN
  - Обновить `.env.example` (если нужно)

- Тесты (`api-gateway/tests/test_vpn_bootstrap.py`):
  - Добавить тесты для `VPN_TYPE=openvpn`
  - Проверить валидацию конфигурации OpenVPN
  - Проверить split-tunnel для OpenVPN

- Entrypoint скрипты:
  - Проверить `docker-entrypoint.sh` и `docker-entrypoint-worker.sh` — возможно, обновить логирование

Детали реализации

OpenVPN специфика:
- Интерфейс обычно называется `tun0` (или `tunN`), не `wg0`
- Конфигурация в формате `.ovpn` (текстовый файл с встроенными сертификатами)
- Запуск: `openvpn --config /path/to/config.ovpn --daemon`
- Проверка статуса: `ip link show dev tun0` или `ps aux | grep openvpn`
- Остановка: `pkill openvpn` или `killall openvpn`

Маршрутизация:
- OpenVPN может автоматически менять default route (если в конфиге есть `redirect-gateway`)
- Для split-tunnel нужно:
  1. Запустить OpenVPN с опцией `--route-nopull` (чтобы не применять маршруты из сервера)
  2. Или удалить `redirect-gateway` из конфига перед запуском
  3. Вручную настроить маршруты через `ip route` (аналогично WireGuard)

Переменные окружения:
```bash
VPN_ENABLED=1
VPN_TYPE=openvpn
OPENVPN_CONFIG_PATH=/run/vpn/openvpn/openvpn.ovpn
OPENVPN_INTERFACE=tun0  # опционально, по умолчанию tun0
VPN_ROUTE_MODE=domains
VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com
VPN_BYPASS_CIDRS=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16
```

Пример функции `ensure_openvpn_up`:
```python
def ensure_openvpn_up(
    config_path: str,
    interface: str = "tun0",
    *,
    timeout: float = 15.0,
    poll_interval: float = 0.5,
) -> None:
    """
    Bring OpenVPN interface up using the provided config file.
    """
    _require_binary("openvpn")
    _require_binary("ip")
    
    cfg = Path(config_path)
    if not cfg.exists():
        raise WireGuardBootstrapError(f"OpenVPN config not found: {cfg}")
    
    _log(f"Ensuring OpenVPN interface '{interface}' is up (config={cfg})")
    
    if _interface_up(interface):
        _log(f"OpenVPN interface '{interface}' already up – skipping.")
        return
    
    # Запуск OpenVPN в фоновом режиме
    # Используем --route-nopull для split-tunnel (маршруты настроим вручную)
    _run_or_raise([
        "openvpn",
        "--config", str(cfg),
        "--daemon",
        "openvpn",
        "--route-nopull",  # Не применять маршруты из сервера
        "--dev", interface,
    ])
    
    _wait_for_interface(interface, timeout, poll_interval)
    _log(f"OpenVPN interface '{interface}' is up.")
```

Важные моменты:
- OpenVPN может требовать прав root для создания TUN интерфейса (в Docker обычно уже есть)
- Нужно обработать случай, когда OpenVPN уже запущен (проверка процесса)
- Логи OpenVPN обычно идут в `/var/log/openvpn/` или stderr (можно перенаправить)

Тестирование (обязательно)
- Unit-тесты:
  - `test_bootstrap_from_env_openvpn()` — проверка запуска с `VPN_TYPE=openvpn`
  - `test_ensure_openvpn_up()` — проверка поднятия интерфейса
  - `test_openvpn_split_tunnel()` — проверка split-tunnel маршрутизации
  - `test_openvpn_config_validation()` — проверка валидации конфигурации

- Интеграционные тесты:
  - Запуск контейнера с `VPN_TYPE=openvpn` и проверка доступности интерфейса
  - Проверка маршрутизации через OpenVPN (split-tunnel)
  - Проверка работы Gemini API через OpenVPN

- Ручное тестирование:
  - `docker-compose up` с `VPN_TYPE=openvpn`
  - Проверка `ip link show dev tun0`
  - Проверка маршрутов: `ip route show`
  - Проверка доступа к Gemini API

Критерии приёмки
- Проект поддерживает `VPN_TYPE=openvpn` наряду с `wireguard` и `awg`
- OpenVPN клиент установлен в Docker образе
- Функция `ensure_openvpn_up()` корректно запускает OpenVPN и проверяет интерфейс
- Split-tunnel маршрутизация работает для OpenVPN (аналогично WireGuard)
- Конфигурация OpenVPN читается из `OPENVPN_CONFIG_PATH`
- Все тесты проходят (unit + integration)
- Документация обновлена с примерами для OpenVPN
- Обратная совместимость: существующие конфигурации WireGuard/AWG продолжают работать

Связанные объекты
- Модуль VPN: `api-gateway/app/core/vpn_bootstrap.py`
- Конфигурация: `api-gateway/app/core/config.py`
- Dockerfile: `Dockerfile.multistage`
- Документация: `PRODUCTION_ENV_GUIDE.md`, `CLAUDE.md`
- Тесты: `api-gateway/tests/test_vpn_bootstrap.py`
- Конфигурации VPN: `config/vpn/`

Оценка
- Реализация OpenVPN в `vpn_bootstrap.py`: 4–6 ч
- Обновление конфигурации и Dockerfile: 1–2 ч
- Создание документации и примеров: 2–3 ч
- Тестирование (unit + integration): 3–4 ч
- Итого: 10–15 ч

Зависимости
- Нет (можно выполнять параллельно с другими задачами)

Примечания
- Конфигурационный файл `open_vpn.ovpn` уже предоставлен и содержит все необходимые сертификаты
- OpenVPN использует TUN интерфейс (обычно `tun0`), в отличие от WireGuard (`wg0`)
- Для split-tunnel может потребоваться модификация конфигурационного файла OpenVPN (удаление `redirect-gateway` или использование `--route-nopull`)
- OpenVPN может автоматически менять DNS через `dhcp-option DNS` — нужно учесть это при настройке маршрутизации

