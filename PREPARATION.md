# ShipStation Connector — Preparation

**Статус:** Фаза 1 (Discovery + архитектурные решения) завершена. Влад
подтвердил объём релиза с первого сообщения по этому коннектору —
«максимальный функционал, полный максимум» (Ярус 1+2+3), без отдельного
запроса подтверждения (см. `CONNECTOR_DISCOVERY.md` шапка).
**Владелец продукта:** vlad@bluebeeweb.com
**Дата подготовки:** 2026-08-21, v0.1
**Vikunja task:** #2209 (BBW Imperal Apps), `[App Development]`.

**Почему сейчас:** ShipStation — крупнейший multi-carrier
shipping/fulfillment SaaS в портфеле, естественный сосед Shopify Connector
(Shopify = источник заказов, ShipStation = логистика после заказа: rate
shopping, лейблы, манифесты, пикапы, склады). Закрывает нишу продавцов и
3PL/фулфилмент-операторов.

---

## 1. Паспорт приложения

**Название в Marketplace (display_name): «ShipStation»**. Внутренний
app_id/папка: `shipstation-connector`.

**ShipStation Connector** — коннектор к ShipStation API V2 (`api.shipstation.com/v2`)
для управления отгрузками: сравнение тарифов у разных carrier'ов,
создание/отмена/тегирование посылок (shipments), печать/загрузка/void
этикеток (включая multi-package и return labels), пакетная обработка
(batches), таможенные манифесты, планирование пикапов, склады
(warehouses), пользовательские типы упаковки (package types), продукты,
webhooks (входящие уведомления о событиях). BYOK: пользователь подключает
свой собственный ShipStation-аккаунт через V2 API-ключ, сгенерированный в
своём аккаунте (Account Settings → API Settings). Imperal ничего не хостит
и не проксирует, кроме самого запроса.

## 2. Ключевые архитектурные решения (см. `CONNECTOR_DISCOVERY.md` §2-3, §8)

### 2.1 ShipStation API V2, не V1, не ShipEngine

Три разные поверхности существуют под похожими доменами/названиями
(см. Discovery §2) — коннектор целится строго в V2, актуальную и растущую
поверхность, привязанную к обычному аккаунту ShipStation пользователя.

### 2.2 BYOK, единственный секрет `shipstation_api_key`

Тот же паттерн, что Klaviyo/DataForSEO/n8n Connector: одно поле
`API-Key`, без OAuth. `connect_shipstation` валидирует ключ дешёвым GET
`/v2/carriers` перед сохранением.

### 2.3 Централизованный rate-limit/retry в клиенте, не в каждом handler'е

200 req/min лимит на весь аккаунт (не per-endpoint) → одна retry-логика
в `shipstation_client.py`, уважающая `Retry-After` при 429, с капом на
число попыток — та же дисциплина, что Klaviyo Connector применил к своим
двум fixed-window лимитам.

### 2.4 Явные денежные предупреждения на деструктивных/платных операциях

Нет официального sandbox → `create_label*`, `create_shipment`,
`schedule_pickup`, `create_manifest` явно помечены в docstring и в UI как
операции, которые могут стоить реальных денег/времени carrier'а. `void_label`
— best-effort возврат средств (не гарантирован всеми carrier'ами), тоже
явно помечен.

### 2.5 Bulk-обёртки как value-add (Ярус 3)

`bulk_void_labels` — пакетный voidа нескольких лейблов сразу
(сериализованно, с уважением rate-limit), по аналогии с
`bulk_delete_records`/`bulk_update_records` в других коннекторах
портфеля. `get_low_rate_report`, `get_shipping_activity_report`,
`audit_pending_shipments` — читающие агрегирующие отчёты, не голый
passthrough (аналог `get_store_summary`/`get_low_stock_report` в Shopify
Connector).

## 3. Секреты

| Имя | write_mode | Назначение |
|---|---|---|
| `shipstation_api_key` | both | V2 API-ключ, единственный секрет |

`write_mode="both"` — тот же аргумент, что во всех остальных BYOK-
коннекторах портфеля: платформенный Secrets-экран недостаточен для
первого запуска без объяснения, где взять ключ; `connect_shipstation`
даёт это объяснение прямо в панели.

## 4. Модель данных / сущности (sdl.Entity)

`ProviderConnection`/`ProviderConnectionList` (единый паттерн с
Klaviyo/Shopify/DataForSEO), `Carrier`, `CarrierList`, `CarrierOption`,
`CarrierPackageType`, `Warehouse`, `WarehouseList`, `Shipment`,
`ShipmentList`, `Rate`, `RateList`, `Label`, `LabelList`, `Batch`,
`BatchList`, `Manifest`, `ManifestList`, `Pickup`, `PickupList`,
`PackageType`, `PackageTypeList`, `Product`, `ProductList`, `Tag`,
`TagList`, `Insert`, `InsertList`, `AddressValidationResult`,
`TrackingInfo`, `Webhook`, `WebhookList`, `Store`, `StoreList`, `User`,
`UserList`, `LowRateReport`, `ShippingActivityReport`,
`PendingShipmentsAudit`, `DeleteResult`, `VoidResult`,
`BulkVoidLabelsResult`.

## 5. Инструменты (полный список, см. `CONNECTOR_DISCOVERY.md` §7)

Ярус 1 (must-have): connect_shipstation, disconnect_shipstation,
list_connections, list_carriers, get_carrier, list_carrier_options,
list_warehouses, get_warehouse, calculate_rates, create_shipment,
list_shipments, get_shipment, update_shipment, cancel_shipment,
tag_shipment, create_label, create_label_from_rate, create_return_label,
get_label, list_labels, void_label, download_label, list_webhooks,
create_webhook, get_webhook, update_webhook, delete_webhook.

Ярус 2 (полнота): create_batch, list_batches, get_batch, add_to_batch,
remove_from_batch, process_batch, create_manifest, list_manifests,
get_manifest, schedule_pickup, list_pickups, get_pickup, cancel_pickup,
list_carrier_package_types, create_package_type, list_package_types,
get_package_type, update_package_type, delete_package_type, list_products,
get_product, update_product, list_tags, create_tag, delete_tag,
list_inserts, validate_address, get_tracking, list_stores, list_users.

Ярус 3 (value-add): get_low_rate_report, get_shipping_activity_report,
audit_pending_shipments, bulk_void_labels.

## 6. UI (панели) — по `UI_INTERFACE_STANDARD.md`

Один правый (или левый, если так задан платформенный слот приложений)
сайдбар-слот с карточкой подключения (BYOK-форма с лейблами полей,
контекстуальный placeholder, без дублирующихся инструкций — инструкция
живёт только в модалке кнопки, не в самом сайдбаре) + secondary-кнопка
"App settings", открывающая отдельный центр-слот с полным набором
настроек (rotate/disconnect ключа, список вебхуков add/remove). Форма
подключения растянута на всю ширину сайдбара, поля внутри неё растянуты
на всю ширину формы — по прямому требованию из этого же документа-
инструкции (см. `UI_INTERFACE_STANDARD.md`, применено к Shopify/Salesforce/
Klaviyo одновременно).

## 7. Пост-аудит и публикация

Строго по `PRICING_POLICY.md`: код → чистый пост-аудит → deploy_app →
update_pricing → submit_for_review. Прайсинг — только после чистого
пост-аудита, шкала `{0, 8, 16, 20, 40, 60}`, `revenue_split_dev` по
партнёрскому тиру (как Asana/MuleSoft).
