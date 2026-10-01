"""Данные для проверки парсеров."""

FEED_FULL = """<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog date="2026-10-01 09:00">
  <shop>
    <name>Канцторг</name>
    <company>ООО «Канцторг»</company>
    <url>https://shop.test/</url>
    <categories>
      <category id="1">Бумага</category>
    </categories>
    <offers>
      <offer id="A-1" available="true">
        <url>https://shop.test/paper-a4</url>
        <price>350.50</price>
        <currencyId>RUR</currencyId>
        <categoryId>1</categoryId>
        <name>Бумага А4 500 листов</name>
        <vendor>Светокопи</vendor>
        <vendorCode>SV-500</vendorCode>
        <description>Офисная бумага плотностью 80 г/м2.</description>
        <param name="Плотность">80 г/м2</param>
        <param name="Формат">А4</param>
      </offer>
      <offer id="A-2" available="false">
        <url>https://shop.test/paper-a3</url>
        <price>720.00</price>
        <currencyId>RUR</currencyId>
        <categoryId>1</categoryId>
        <name>Бумага А3 500 листов</name>
      </offer>
    </offers>
  </shop>
</yml_catalog>
"""

# Второй обход: А3 из фида исчезла, у А4 изменилась только цена.
FEED_WITHOUT_A3 = FEED_FULL.replace("<price>350.50</price>", "<price>399.00</price>")
_CUT = FEED_WITHOUT_A3.index('      <offer id="A-2"')
FEED_WITHOUT_A3 = (
    FEED_WITHOUT_A3[:_CUT]
    + """    </offers>
  </shop>
</yml_catalog>
"""
)

SUPPLIERS_CSV = """lot_id,supplier_inn,supplier_kpp,is_winner
4257576,7707049388,784201001,true
4652711,636200108061,780601001,false
4652711,7804428656,780601001,true
4652720,0000000000,781401001,false
"""

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://kanctorg.test/sitemap-goods.xml</loc></sitemap>
</sitemapindex>
"""

SITEMAP_GOODS = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://kanctorg.test/product/paper-a4</loc></url>
  <url><loc>https://kanctorg.test/about</loc></url>
</urlset>
"""

PRODUCT_PAGE = """<!doctype html>
<html><body>
  <h1>Бумага А4</h1>
  <p>ИНН 7804428656</p>
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": "Product",
   "name": "Бумага А4 500 листов", "sku": "SV-500",
   "description": "Офисная бумага 80 г/м2.",
   "brand": {"@type": "Brand", "name": "Светокопи"},
   "category": "Бумага",
   "additionalProperty": [{"@type": "PropertyValue", "name": "Плотность", "value": "80 г/м2"}],
   "offers": {"@type": "Offer", "price": "350.50", "priceCurrency": "RUB",
              "availability": "https://schema.org/InStock",
              "url": "https://kanctorg.test/product/paper-a4"}}
  </script>
</body></html>
"""

# Третий обход: фид отдал пустой каталог — снимать предложения по нему нельзя.
FEED_EMPTY = """<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog date="2026-10-03 09:00">
  <shop>
    <name>Канцторг</name>
    <company>ООО «Канцторг»</company>
    <url>https://shop.test/</url>
    <offers>
    </offers>
  </shop>
</yml_catalog>
"""

# Каталоги читаются по sitemap, поэтому фикстуры повторяют разметку живых
# страниц: перечень адресов и разметку карточки каждого источника.

OPTKATALOG_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://optkatalog.ru/</loc></url>
  <url><loc>https://optkatalog.ru/postavschiki/</loc></url>
  <url><loc>https://optkatalog.ru/postavschiki/bumaga/ofisnaya/</loc></url>
  <url><loc>https://optkatalog.ru/postavschiki/bumaga/ofisnaya/kanctorg/</loc></url>
  <url><loc>https://optkatalog.ru/postavschiki/bumaga/ofisnaya/papirus/</loc></url>
</urlset>
"""

OPTKATALOG_CARD = """<!doctype html>
<html><body>
  <h1>ООО «Канцторг»</h1>
  <div class="ty-product-feature">
    <span class="ty-product-feature__label">Тип компании:</span>
    <div class="ty-product-feature__value">Производитель</div>
  </div>
  <div class="ty-product-feature">
    <span class="ty-product-feature__label">Город:</span>
    <div class="ty-product-feature__value"><ul>
      <li>Санкт-Петербург</li><li>Москва</li>
    </ul></div>
  </div>
  <div id="content_description" class="content-description"><div>
    <h2>О компании</h2>
    <p>Поставки офисной бумаги с 2001 года.</p>
    <h3>Юридическое наименование</h3>
    <p>ООО "Канцторг"</p>
    <h3>ИНН/ОГРН</h3>
    <p>7804428656</p>
    <h3>Год основания</h3>
    <p>2001</p>
    <h2>Товары, услуги</h2>
    <p>Бумага А4 500 листов<br/>Ручка шариковая</p>
    <h2>Адрес</h2>
    <p>Россия, г. Всеволожск, Ленинградская обл., ул. Заводская 1</p>
    <h2>Контакты</h2>
    <details>
      <p><a href="https://kanctorg.test/" rel="nofollow">САЙТ</a></p>
      <p><a href="tel:78120000000">+7 (812) 000-00-00</a></p>
      <p><a href="mailto:sales@kanctorg.test">sales@kanctorg.test</a></p>
    </details>
  </div></div>
  <script>var tracker = 1;</script>
</body></html>
"""

# Второй вариант разметки: реквизиты строками «Метка: значение», другой
# заголовок блока ассортимента, длинный абзац вместо перечня позиций и несколько
# типов компании в одном свойстве.
OPTKATALOG_CARD_INLINE = """<!doctype html>
<html><body>
  <h1>АО «Папирус»</h1>
  <div class="ty-product-feature">
    <span class="ty-product-feature__label">Тип компании:</span>
    <div class="ty-product-feature__value">Дистрибьютор, Оптовый поставщик</div>
  </div>
  <div id="content_description" class="content-description"><div>
    <h3>Юридическое наименование</h3>
    <p>АО "Папирус"</p>
    <p>Год основания: 1996</p>
    <p>ИНН/ОГРН: 7707049388/1027700132195</p>
    <h2>Продукция, услуги</h2>
    <p>Картон переплётный<br/>Компания поставляет картон и бумагу оптом по всей России
       со склада в Москве, работает с отсрочкой платежа и собственным автопарком.</p>
    <h2>Адрес</h2>
    <p>Россия, Москва, ул. Тверская 1</p>
  </div></div>
</body></html>
"""

ABOUTPARTNER_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://aboutpartner.ru/producers</loc></url>
  <url><loc>https://aboutpartner.ru/producer/crmindex-servicespbx</loc></url>
  <url><loc>https://aboutpartner.ru/producer/pc-producer-1</loc></url>
</urlset>
"""

ABOUTPARTNER_CARD = """<!doctype html>
<html><body>
  <h1>ООО «Канцторг»</h1>
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": ["Organization", "LocalBusiness"],
   "name": "ООО «Канцторг»", "legalName": "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ \\"КАНЦТОРГ\\"",
   "taxID": "7804428656", "telephone": "+7 (812) 000-00-00", "email": "sales@kanctorg.test",
   "sameAs": ["https://vk.com/kanctorg", "https://kanctorg.test"],
   "address": {"@type": "PostalAddress", "streetAddress": "ул. Заводская 1",
               "addressLocality": "Всеволожск", "addressRegion": "Ленинградская область"}}
  </script>
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": "ItemList",
   "itemListElement": [
     {"@type": "ListItem", "position": 1,
      "item": {"@type": "Product", "name": "Бумага А4 500 листов",
               "url": "https://aboutpartner.ru/product/pc-product-1",
               "description": "Офисная бумага 80 г/м2.",
               "brand": {"@type": "Brand", "name": "Светокопи"}}},
     {"@type": "ListItem", "position": 2,
      "item": {"@type": "Product", "name": "Ручка шариковая",
               "url": "https://aboutpartner.ru/product/pc-product-2"}}]}
  </script>
</body></html>
"""

# Карточка сервиса: компании на ней нет, поэтому в пакет она не попадает.
ABOUTPARTNER_SERVICE = """<!doctype html>
<html><body>
  <h1>Виртуальная АТС</h1>
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": "Виртуальная АТС"}
  </script>
</body></html>
"""

TEXZAKAZ_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://texzakaz.ru/proizvoditeli</loc></url>
  <url><loc>https://texzakaz.ru/p/10</loc></url>
</urlset>
"""

TEXZAKAZ_CARD = """<!doctype html>
<html><body>
  <h1>Канцторг</h1>
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@graph": [
    {"@type": "Organization", "name": "Канцторг",
     "alternateName": "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ \\"КАНЦТОРГ\\"",
     "taxID": "7804428656",
     "address": {"@type": "PostalAddress", "addressCountry": "RU",
                 "addressLocality": "Всеволожск", "addressRegion": "Ленинградская область"},
     "knowsAbout": ["Бумага А4 500 листов", "Ручка шариковая"]},
    {"@type": "BreadcrumbList", "itemListElement": []}]}
  </script>
</body></html>
"""


PULSCEN_SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://www.pulscen.ru/sitemap_firms_rubrics.xml.gz</loc></sitemap>
  <sitemap><loc>https://www.pulscen.ru/sitemap_price_1.xml.gz</loc></sitemap>
  <sitemap><loc>https://www.pulscen.ru/sitemap_price_f_2.xml.gz</loc></sitemap>
</sitemapindex>
"""

PULSCEN_SITEMAP_FIRMS = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.pulscen.ru/firms/010301-armatura</loc></url>
</urlset>
"""

PULSCEN_SITEMAP_PRICE = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.pulscen.ru/price/010301-armatura</loc></url>
</urlset>
"""

PULSCEN_PRODUCT_CARD = """<html><head>
<title>Арматура А400 купить от компании ООО "ПервоСтрой"</title>
</head><body><div class="seller">ООО "ПервоСтрой"
<a href="https://nsk.pulscen.ru/companies/99418958/reviews">Отзывы</a></div></body></html>"""

PULSCEN_PRODUCT_CARD_NEW_SELLER = """<html><head>
<title>Арматура купить от компании Сталь-Опт</title>
</head><body><div class="seller">Сталь-Опт
<a href="/companies/55500011/reviews">Отзывы</a></div></body></html>"""

PULSCEN_FIRMS_PAGE = """<html><head><link rel="next" href="https://www.pulscen.ru/firms/010301-armatura?page=2"></head><body>
<ul><li class="company-card js-company-card" data-id="99418958">
<span class="ccd-title" data-to="https://pervostroi.example">ПервоСтрой, ООО</span>
<div class="ccd-marker marker">Производитель</div>
<div class="ccd-marker marker">Оптовый продавец</div>
<div class="ccdc-row ccd-address"><div class="ccda-row">г. Новосибирск, ул. Ватутина, 99</div></div>
</li></ul></body></html>"""

PULSCEN_FIRMS_PAGE_2 = """<html><body><ul>
<li class="company-card" data-id="99418958"><span class="ccd-title">ПервоСтрой, ООО</span></li>
<li class="company-card" data-id="99469184"><span class="ccd-title">АМК-Групп</span>
<div class="ccd-marker marker">Услуги и сервис</div></li></ul></body></html>"""

PULSCEN_PRICE_PAGE = """<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"ItemList","itemListElement":[
{"@type":"ListItem","position":1,"item":{"@type":"Product","name":"Арматура А400 14 мм",
"offers":{"@type":"Offer","price":68.55,"priceCurrency":"RUB","availability":"https://schema.org/InStock"},
"url":"https://nsk.pulscen.ru/products/armatura_a3_14mm_185531520"}},
{"@type":"ListItem","position":2,"item":{"@type":"Product","name":"Арматура по запросу",
"url":"https://www.pulscen.ru/products/armatura_zapros_185531999"}}]}
</script></head><body></body></html>"""

PULSCEN_BOT_CHECK = "<html><title>Проверка безопасности - Pulscen</title></html>"


PULSCEN_CARD_WITH_RECOMMENDATIONS = """<html><head>
<title>Товар купить от компании Верный продавец</title>
</head><body>
<div class="recommended"><a href="/companies/99">Чужая компания</a></div>
<div class="seller"><span>Верный продавец</span>
<a href="/companies/10/reviews">Отзывы</a></div>
</body></html>"""

PULSCEN_CARD_AMBIGUOUS = """<html><head><title>Товар купить от компании Никто</title></head><body>
<a href="/companies/1">Первая</a><a href="/companies/2">Вторая</a></body></html>"""


PULSCEN_CARD_FOREIGN_LINK = """<html><head>
<title>Товар от компании Верный продавец</title>
</head><body>
<section itemprop="seller">Верный продавец</section>
<aside><a href="/companies/99/">Другой продавец</a></aside>
</body></html>"""

PULSCEN_CARD_LINK_IN_BODY = """<html><head>
<title>Товар от компании Верный продавец</title>
</head><body>
<a itemprop="seller" href="/companies/10/">Верный продавец</a>
<a href="/companies/99/">Другой продавец</a>
</body></html>"""


PULSCEN_CARD_REVIEWS_LINK = """<html><head>
<title>Арматура 10 мм от компании "Региональный Склад"</title>
</head><body><div class="product-tabber"><div>"Региональный Склад" о компании
<div class="recent-company-reviews"><a class="js-all-reviews" href="/companies/99682156/reviews">
Посмотреть все отзывы о компании</a></div></div></div>
<a href="/companies/55">Региональный Склад Соседний</a></body></html>"""
