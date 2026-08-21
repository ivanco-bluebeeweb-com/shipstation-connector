# ShipStation Connector — Connector Discovery

**Дата discovery:** 2026-08-21
**Метод:** `Docs/session-notes/CONNECTOR_DISCOVERY_STANDARD.md`.
**Vikunja task:** #2209 (BBW Imperal Apps), `[App Development]`.
**Статус:** Ярусы 1-3 пройдены (свежее чтение docs.shipstation.com,
2026-08-21). Объём заявлен Владом с первого сообщения по этому коннектору
(«максимальный функционал, полный максимум») — по Шагу 5 стандарта это
действует как уже данный ответ, отдельный вопрос не требуется. Берём
Ярус 1 + Ярус 2 + Ярус 3.

---

## 1. Целевой сервис и источники

ShipStation — multi-carrier shipping/fulfillment SaaS (Auctane), самый
крупный логистический слой в портфеле e-commerce-коннекторов. Естественный
сосед Shopify Connector: многие продавцы используют Shopify как источник
заказов и ShipStation как fulfillment engine (rate shopping, печать
этикеток, манифесты, пикапы).

Источники (прочитаны 2026-08-21):
- `docs.shipstation.com/api-overview` — три разные API-поверхности ShipStation
  предлагает (см. §2, критично не перепутать).
- `docs.shipstation.com/getting-started` — что покрывает V2: rate shopping,
  create/update/cancel shipments, tag shipments, labels (create/download/
  list/void, multi-package, return labels), batches, custom package types,
  manifests, pickups, products (create/update), list users.
- `docs.shipstation.com/authentication` — заголовок `API-Key`, HTTPS/TLS 1.2+
  обязателен, 401 при отсутствующем/неверном ключе.
- `docs.shipstation.com/rate-limits` — 200 запросов/минуту по умолчанию,
  `429 Too Many Requests` + заголовок `Retry-After`; лимит применяется
  глобально на аккаунт (не per-endpoint) — retry-логика должна быть на
  уровне клиента, не отдельно в каждом handler'е. Поле `error_source` в
  ответе различает лимит самого ShipStation и лимит carrier/marketplace.
- `docs.shipstation.com/apis/openapi/*` — предметные разделы: labels,
  shipments, rates, batches, manifests, carriers, warehouses, tags,
  webhooks, package_types, package_pickups.
- `www.shipstation.com/docs/api/stores/list/`, `.../models/webhook/` —
  дополнительные модельные страницы (stores/marketplaces, webhook payload
  shape).

## 2. КРИТИЧНО: три разные API-поверхности ShipStation — не перепутать

1. **ShipStation API V2** (целевая для этого коннектора) — base
   `https://api.shipstation.com/v2`, современная, растущая, «early release
   stage» по собственному заявлению документации. Аутентификация —
   простой заголовок `API-Key` (НЕ OAuth, НЕ Basic).
2. **ShipStation API V1 (legacy)** — base `https://ssapi.shipstation.com/`,
   отдельные креды (API Key + API Secret, HTTP Basic), помечен как
   устаревший и будет удалён в будущем. НЕ строим на нём — только V2.
3. **ShipStation API (formerly ShipEngine)** — base
   `https://api.shipengine.com/v1`, standalone multi-carrier API вне
   самого приложения ShipStation, со своим sandbox (`TEST_`-префикс
   ключей). Это ОТДЕЛЬНЫЙ продукт/аккаунт, не тот же API, что V2 — не
   путать при чтении доков (многие статьи на docs.shipstation.com
   фактически описывают ShipEngine, а не ShipStation V2).

**Решение:** коннектор строит **ShipStation API V2**, привязанную к
собственному аккаунту ShipStation пользователя (не ShipEngine, не V1).

## 3. Аутентификация — BYOK, единственный секрет

`API-Key` header, один активный V2 API-ключ на аккаунт (генерируется в
ShipStation UI: Account → Account Settings → API Settings, показывается
единожды). Ровно та же модель, что Klaviyo/DataForSEO/n8n Connector в
портфеле — единственный секрет, без client_id/client_secret, без OAuth.
`connect_shipstation` валидирует ключ дешёвым GET-запросом (`/v2/carriers`
или `/v2/users`) перед сохранением — тот же паттерн, что
`connect_klaviyo`/`connect_dataforseo`.

## 4. КРИТИЧНО: нет официального sandbox — все операции идут в проде

В отличие от ShipEngine (`TEST_`-ключи) у ShipStation V2 нет
изолированной тестовой среды. Создание лейбла реально списывает деньги
у carrier-аккаунта пользователя. Официальная рекомендация — использовать
`test_label=true` там, где ShipStation это поддерживает (create_label),
и/или сразу void'ить тестовые лейблы. **Это должно быть явно отражено в
дизайне**: `create_label`/`create_label_from_rate` получают явный
параметр `test_label` (default false, с предупреждением в описании),
и в панели/чате перед первым реальным использованием — предупреждение
о реальных деньгах, аналогично тому, как WordPress Hub предупреждает
о деструктивных операциях.

## 5. Rate limiting — правило для клиента

200 req/min по умолчанию (aккаунт может попросить больше у поддержки).
`429` + `Retry-After` header. `error_source` в теле ответа различает
источник лимита (ShipStation vs carrier/marketplace passthrough).
Клиент (`shipstation_client.py`) реализует один retry-on-429 с уважением
`Retry-After`, централизованно — тот же паттерн, что
`klaviyo_client.request()`.

## 6. Карта возможностей (направление на каждую)

| Возможность | Ingress/Egress/Both | Комментарий |
|---|---|---|
| Rates (calculate) | Ingress | Rate shopping across carriers — не создаёт shipment |
| Shipments CRUD + cancel + tag | Both | Основная сущность до печати лейбла |
| Labels (create/create-from-rate/list/get/void/download) | Both | Egress-тяжёлая — реальные деньги за не-void |
| Multi-package / return labels | Egress | Частные случаи create_label |
| Batches (create/list/get/add-to/remove-from/process/errors) | Both | Массовая печать лейблов |
| Manifests (create/list/get) | Both | End-of-day carrier manifest (pickup paperwork) |
| Pickups (schedule/list/get/cancel) | Both | Запрос забора груза у carrier |
| Carriers (list/get/options/add-funds where supported) | Ingress | Подключённые carrier-аккаунты в ShipStation |
| Carrier package types (list) | Ingress | Стандартные упаковки carrier'а |
| Custom package types (create/list/get/update/delete) | Both | Свои пресеты упаковки |
| Warehouses (create/list/get/update/delete) | Both | Склады отправки |
| Products (list/get/update) | Both | SKU-справочник ShipStation (используется в rating/labels) |
| Tags (list/create/delete) — shipment tags | Both | Организационные метки на shipments |
| Inserts (list) | Ingress | Digital package inserts, привязанные к продукту/carrier |
| Address validation | Ingress | Проверка адреса перед созданием shipment |
| Tracking (get by tracking number/carrier) | Ingress | Статус доставки |
| Downloads (download file by id) | Ingress | PDF/PNG/ZPL этикетки и манифесты |
| Stores/connections (list) | Ingress | Подключённые торговые площадки внутри аккаунта ShipStation |
| Users (list) | Ingress | Пользователи аккаунта ShipStation (для назначения) |
| Webhooks (create/list/get/update/delete) | Both | Событийные уведомления (label created, track update, batch complete и т.д.) |

## 7. Ярусы

**Ярус 1 (ключевое, обязательное):**
connect/disconnect/list_connections, calculate_rates, create/update/get/
list/cancel shipment, tag/untag shipment, create_label,
create_label_from_rate, get_label, list_labels, void_label,
download_file, list_carriers, get_carrier, list_warehouses,
create_warehouse, list_webhooks, create_webhook, delete_webhook.

**Ярус 2 (полнота):**
batches (create/list/get/add/remove/process), manifests (create/list/
get), pickups (schedule/list/get/cancel), carrier_options,
carrier_package_types, package_types (create/list/get/update/delete),
products (list/get/update), tags (list/create/delete), inserts (list),
validate_address, get_tracking, list_stores, list_users,
update_webhook, get_webhook.

**Ярус 3 (доп. ценность / отчётность, наш собственный value-add, не
голый passthrough):**
`get_low_rate_report` (сравнить тарифы всех carrier'ов по одному
shipment и подсветить самый дешёвый/быстрый — аналог
`get_low_stock_report` в Shopify Connector), `get_shipping_activity_report`
(агрегат по лейблам за период: кол-во, суммарная стоимость, по carrier'ам —
аналог `get_store_summary`), `audit_pending_shipments` (shipments без
лейбла старше N дней — операционная гигиена), `bulk_void_labels` (пакетный
void нескольких лейблов сразу — типовой value-add bulk-обёртки, как в
других коннекторах портфеля).

## 8. Известные ограничения / риски (зафиксировать в PREPARATION и README)

1. Нет sandbox → все `create_label*`/`create_shipment`/`schedule_pickup`
   вызовы стоят реальных денег/времени carrier'а. `test_label` параметр
   передаётся ShipStation'у где поддерживается, но НЕ гарантирует
   отсутствие списания в 100% случаев по всем carrier'ам — предупреждение
   должно быть явным в UI и в docstring каждого такого инструмента.
2. V2 — «early release» по собственному заявлению ShipStation: не все
   V1-возможности перенесены (например, часть функций B2B/EDI может
   отсутствовать) — коннектор строится строго на подтверждённых V2
   эндпоинтах из этого discovery, не на предположениях по аналогии с V1.
3. Rate limit применяется на весь аккаунт, а не per-token — bulk-операции
   (batches, bulk_void_labels) должны сериализовать запросы и уважать
   `Retry-After`, а не бить параллельно.
