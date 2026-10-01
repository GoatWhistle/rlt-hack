# Название и знак LOTIVE

Утверждено пользователем 01.10.2026: название **LOTIVE**, знак **№15 «Фаска»** из [галереи](../frontend/prototypes/lotive-logos.html?variant=O).

Знак — гранёная L и отдельный ромб. Геометрия выбранного варианта сохранена без изменений. Основные цвета взяты из действующих токенов интерфейса: индиго `#4f46e5`, янтарь `#e9a23b`. Монохромная версия — графит `#1b1d29`.

## Файлы

- `frontend/public/brand/lotive-symbol.svg` — основной вектор на прозрачном фоне, viewBox 72 × 72; источник для дальнейшего использования.
- `frontend/public/brand/lotive-symbol-mono.svg` — тот же знак в одном цвете.
- `frontend/public/favicon.svg` — знак на светлой скруглённой подложке.
- `frontend/public/favicon.ico` — изображения 16, 32 и 48 px в одном контейнере.
- `frontend/public/icons/favicon-{16,32,48}x{16,32,48}.png` — растровые версии для вкладок браузера.
- `frontend/public/apple-touch-icon.png` — 180 px; дополнительные размеры 152 и 167 px лежат в `public/icons/`.
- `frontend/public/icons/icon-{192,512}x{192,512}.png` — иконки для манифеста.
- `frontend/public/icons/icon-maskable-512x512.png` — адаптивная иконка с безопасными отступами.
- `frontend/public/site.webmanifest` — название и иконки приложения; подключён в `frontend/index.html` вместе с favicon и Apple Touch Icons.

## Экспорт

PNG получены из SVG через `@resvg/resvg-js`. Для мобильных иконок используется непрозрачный белый квадрат 72 × 72 и преобразование исходного знака `translate(10.8 10.8) scale(.70)`. Углы заранее не скругляются: форму задаёт устройство. Все части знака помещаются в центральный круг радиусом 40% ширины.

Размеры и подключение сверены с [Apple Safari Web Content Guide](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html) и [документацией MDN по иконкам манифеста](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Define_app_icons).

Манифест добавляет метаданные и иконки; офлайн-режим и service worker этим изменением не реализованы. Галерея остаётся историей поиска, источником утверждённого знака служит отдельный SVG.
