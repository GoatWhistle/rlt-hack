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

DIRECTORY_LISTING = """<!doctype html>
<html><body>
  <ul class="companies">
    <li><a href="/company/kanctorg">ООО «Канцторг»</a></li>
    <li><a href="/company/kanctorg">ООО «Канцторг»</a></li>
  </ul>
  <a class="next" href="/katalog/bumaga?page=2">Следующая</a>
</body></html>
"""

DIRECTORY_LISTING_PAGE_2 = """<!doctype html>
<html><body>
  <ul class="companies">
    <li><a href="/company/papirus">АО «Папирус»</a></li>
  </ul>
</body></html>
"""

COMPANY_PAGE = """<!doctype html>
<html><body>
  <h1>ООО «Канцторг»</h1>
  <div class="region">Санкт-Петербург</div>
  <div class="requisites">ИНН: 7804428656, КПП 780601001</div>
  <a href="https://kanctorg.test/">Сайт компании</a>
  <table class="goods">
    <tr class="item"><td><a href="/company/kanctorg/paper-a4">Бумага А4</a></td>
        <td class="price">350,50 ₽</td><td class="note">Склад в Санкт-Петербурге</td></tr>
    <tr class="item"><td><a href="/company/kanctorg/pen">Ручка шариковая</a></td>
        <td class="price">25 ₽</td><td class="note"></td></tr>
  </table>
  <script>var tracker = 1;</script>
</body></html>
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

DIRECTORY_HOME = """<!doctype html>
<html><body>
  <nav>
    <a href="/katalog/bumaga">Бумага и картон</a>
    <a href="/about">О сайте</a>
  </nav>
</body></html>
"""

COMPANY_PAGE_PAPIRUS = """<!doctype html>
<html><body>
  <h1>АО «Папирус»</h1>
  <div class="region">Москва</div>
  <div class="requisites">ИНН 7707049388 КПП 770701001</div>
  <a href="https://papirus.test/">papirus.test</a>
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
