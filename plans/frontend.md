# Frontend

## Сделано

- [x] Каркас React + TypeScript + Vite, слои `app / pages / features / shared`
- [x] Biome, `.gitignore`, `.editorconfig`, `.gitattributes` в корне
- [x] i18n ru/en на JSON с типизированными ключами и проверкой совпадения ключей
- [x] Нейтральные токены, глобальные стили, CSS Modules по компонентам
- [x] Анимации входа и выхода: `usePresence`, `Transition`, `Dialog`, тосты
- [x] Ошибки: `ApiError`, `describeError`, 404, ошибка маршрута, устаревший чанк, корневой error boundary, тосты ошибок мутаций
- [x] Проверки правил в `scripts/checks` с тестами, покрытие ≥ 80 %, e2e с axe
- [x] Dockerfile, nginx и корневой `docker-compose.yml`
- [x] Дизайн-система 21n в токенах, экраны загрузки и результатов на демонстрационных данных
- [x] [Улучшить подачу рекомендаций на экране результатов](results-screen-presentation.md)

## Дальше

- [ ] Согласовать акцентные цвета (индиго для выбора, янтарный для уточнений) и обновить `frontend/DESIGN.md`
- [ ] Согласовать контракт API с backend, добавить прокси `/api` в nginx и сервис backend в compose
- [ ] CI: `npm run verify` и e2e на каждый PR
