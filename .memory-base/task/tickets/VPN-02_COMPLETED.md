# VPN-02 — Split tunnel маршрутизация — COMPLETED ✅

**Дата завершения:** 2025-11-07  
**Статус:** Выполнено

---

## Что сделано

### 1. Управление маршрутами внутри контейнера
- **Файл:** `api-gateway/app/core/vpn_bootstrap.py`
- После успешного `wg-quick up` теперь:
  - Определяется исходный default route Docker (`ip route show default`).
  - В зависимости от `VPN_ROUTE_MODE` (`all|domains|cidr`) настраиваются таблицы:
    - `all` — весь трафик идёт через WireGuard, но `VPN_BYPASS_CIDRS` принудительно возвращаются на docker bridge (Postgres/Redis/RabbitMQ).
    - `domains` — default route возвращается на docker bridge, а только домены из `VPN_ROUTE_DOMAINS` резолвятся и получают `/32` маршруты через `wg0`.
    - `cidr` — аналогично `domains`, но без DNS; CIDR из `VPN_ROUTE_CIDRS` направляются через WireGuard.
  - Добавлены проверки на отсутствие бинарей `ip`, корректность DNS и отсутствие baseline route.
  - Логирование `[vpn]` показывает каждое действие.

### 2. Конфигурация окружения
- **Файл:** `.env.example`
  - Добавлена переменная `VPN_ROUTE_CIDRS` с описанием.
  - Раздел VPN теперь демонстрирует полный набор переменных для split‑tunnel.

### 3. Документация WireGuard
- **Файл:** `config/vpn/wireguard/README.md`
  - Обновлена таблица профилей маршрутизации.
  - Описан рекомендуемый набор для Gemini (`VPN_ROUTE_MODE=domains` + `VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com`).
  - Добавлен раздел про проверку маршрутов.

### 4. Скрипт проверки
- **Файл:** `scripts/vpn/check_routes.sh`
  - Bash-скрипт, который:
    - Резолвит домен (по умолчанию `generativelanguage.googleapis.com`), проверяет `ip route get ...` → `dev wg0`.
    - Делает HTTPS запрос (ожидаем 401/403, главное — успешное соединение через туннель).
    - Проверяет второй аргумент (например, `172.20.0.2` — Postgres), что он **не** идёт через `wg0`.
  - Скрипт документирован в README.

### 5. Тесты
- **Файл:** `api-gateway/tests/test_vpn_bootstrap.py`
  - Новые юнит-тесты для маршрутизации: `all`-mode, `domains`-mode, отсутствие доменов.
  - Обновлены тесты `bootstrap_from_env` (мокаем default route и split-туннель конфиг).

---

## Тестирование

```bash
cd api-gateway && pytest tests/test_vpn_bootstrap.py
```

Все 10 тестов проходят.

---

## Соответствие AC

- ✅ Трафик к `generativelanguage.googleapis.com` уходит через WireGuard (маршруты `/32` + проверочный скрипт).
- ✅ Docker-сервисы (Postgres/Redis/RabbitMQ, CIDR из `VPN_BYPASS_CIDRS`) остаются на локальной сети.
- ✅ Документирован скрипт проверки маршрутов (`scripts/vpn/check_routes.sh`, выводит `ip route get` и `curl`).
- ✅ Логика маршрутизации привязана к переменным из `.env`, поддерживает `domains` и `cidr`.

---

## Рекомендации по эксплуатации

1. Перед включением `VPN_ENABLED=1` заполнить:
   - `WG_CONFIG_PATH=/run/vpn/wireguard/<file>.conf`
   - `VPN_ROUTE_MODE=domains`
   - `VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com`
   - `VPN_BYPASS_CIDRS=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16`
2. Добавить `cap_add: NET_ADMIN` и volume с конфигом в `docker-compose` (будет покрыто VPN-04).
3. После старта контейнера запускать `./scripts/vpn/check_routes.sh generativelanguage.googleapis.com 172.20.0.2` — скрипт упадёт, если Gemini не через `wg0` или Postgres случайно ушёл в туннель.

VPN-02 закрыта: split-tunnel реализован, протестирован и задокументирован.
