# VPN-01 — WireGuard entrypoint — COMPLETED ✅

**Дата завершения:** 2025-11-07  
**Статус:** Готово к поставке

---

## Реализованные изменения

### 1. Bootstrap WireGuard внутри контейнера
- **Файл:** `api-gateway/app/core/vpn_bootstrap.py`
- Новый модуль включает:
  - Проверку наличия `wg-quick` и `ip`, валидацию `WG_CONFIG_PATH`
  - Вызов `wg-quick up <config>` (не по интерфейсу) и ожидание статуса `state UP`
  - Fail-fast через `WireGuardBootstrapError`, чтобы контейнер останавливался при любых ошибках
  - Функцию `bootstrap_from_env()` — читает `VPN_ENABLED`, `VPN_TYPE`, `WG_CONFIG_PATH`, `WG_INTERFACE` и используется как entrypoint

### 2. Обязательный запуск VPN перед приложением
- **Файл:** `api-gateway/docker-entrypoint.sh`
- При `VPN_ENABLED` (1/true/on/yes) выполняется `python -m app.core.vpn_bootstrap` **до** миграций и запуска приложения. Если VPN не поднялся, процесс завершается → трафик не выйдет в обход туннеля.

### 3. Docker образ с зависимостями WireGuard
- **Файл:** `api-gateway/Dockerfile`
- В образ устанавливаются `wireguard-tools`, `iproute2`, `iptables`, `resolvconf`, чтобы `wg-quick` и маршрутизация работали сразу в CI/CD и prod.

### 4. Автотесты
- **Файл:** `api-gateway/tests/test_vpn_bootstrap.py`
- Покрыты сценарии:
  - пропуск, когда VPN выключен;
  - отсутствие `WG_CONFIG_PATH`;
  - успешный запуск с вызовом `ensure_wireguard_up`;
  - интерфейс уже UP (wg-quick не вызывается);
  - вызов `wg-quick` и ожидание UP;
  - ошибки `wg-quick` и тайм-аут ожидания интерфейса.

---

## Тестирование

```bash
cd api-gateway && pytest tests/test_vpn_bootstrap.py
```

Все 7 тестов проходят.

---

## Соответствие AC

- ✅ При `VPN_ENABLED=1` запуск контейнера требует успешного `wg-quick up` (ошибка прерывает старт).
- ✅ Используется `WG_INTERFACE` и `WG_CONFIG_PATH` из окружения.
- ✅ Логирование `[vpn] ...` облегчает диагностику в CI и docker logs.
- ✅ При отключённом VPN (`VPN_ENABLED=0`) приложение стартует как раньше.

---

## Операционные заметки

1. В `docker-compose` нужно добавить:
   - `cap_add: ["NET_ADMIN"]`
   - volume с реальным конфигом (`config/vpn/wireguard/*.conf` → `/run/vpn/wireguard/`)
2. В `.env` выставить:
   - `VPN_ENABLED=1`
   - `WG_CONFIG_PATH=/run/vpn/wireguard/<file>.conf`
   - `WG_INTERFACE=wg0` (или другой, если требуется)
3. При ошибках `wg-quick` контейнер завершится → orkestrator перезапустит после исправления секрета.

---

## Следующие шаги

1. **VPN-02** — настроить split‑tunnel и документировать тестовый скрипт (curl/traceroute).
2. **VPN-03** — `/api/vpn/health` для проверки интерфейса/маршрутов.
3. **VPN-04** — обновить `docker-compose`/k8s манифесты с `NET_ADMIN`, volume и единственным внешним портом 9187.

VPN-01 выполнена и блокирует запуск приложения без активного WireGuard, как требуется в .memory-base.
