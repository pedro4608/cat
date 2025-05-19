from playwright.sync_api import sync_playwright
import time
import xml.etree.ElementTree as ET
from ftplib import FTP

def coletar_carros():
    car_data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--window-size=1920,1080",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-gpu"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        base_url = "https://www.sandroveiculos.com.br/estoque/veiculos/p-"
        pagina = 1

        facebook_body_styles = {
            "hatch": "HATCHBACK",
            "sedan": "SEDAN",
            "suv": "SUV",
            "pickup": "PICKUP",
            "van": "VAN",
            "truck": "TRUCK",
            "coupe": "COUPE",
            "convertible": "CONVERTIBLE",
            "wagon": "WAGON",
            "minivan": "MINIVAN",
            "roadster": "ROADSTER",
            "sportscar": "SPORTSCAR"
        }

        def detect_body_style(texto):
            texto = texto.lower()
            for chave, valor in facebook_body_styles.items():
                if chave in texto:
                    return valor
            return "OTHER"

        while True:
            print(f"\nAcessando página {pagina}...")
            page.goto(base_url + str(pagina))
            time.sleep(5)

            try:
                page.wait_for_selector('a[title="Ver Detalhes"]', timeout=10000)
                links = page.locator('a[title="Ver Detalhes"]').all()
            except:
                links = []

            print(f"🟢 Encontrados {len(links)} carros nesta página.")
            if len(links) == 0:
                print(f"🔴 Nenhum carro encontrado na página {pagina}. Encerrando.")
                break

            hrefs = list(set([
                f"https://www.sandroveiculos.com.br{link.get_attribute('href')}"
                if link.get_attribute("href").startswith("/")
                else link.get_attribute("href")
                for link in links
            ]))
            print(f"🟢 Total de {len(hrefs)} links únicos encontrados.")

            for href in hrefs:
                print(f"🔄 Processando {href} ...")
                page.goto(href)
                time.sleep(5)

                try:
                    vehicle_id = href.split("/")[5]

                    image_urls = []
                    image_tags = page.locator('div.slick-slide img').all()
                    for img in image_tags:
                        src = img.get_attribute("src")
                        if src and "w=800" in src:
                            url = src.split('?')[0]
                            if url not in image_urls:
                                image_urls.append(url)

                    if not image_urls:
                        continue

                    image_link = image_urls[0]
                    additional_image_link = ",".join(image_urls[1:])

                    price_elements = page.locator('p.font-description').all()
                    price_raw = ""
                    for elem in price_elements:
                        text = elem.text_content()
                        if "R$" in text:
                            price_raw = text.strip()
                            break
                    if not price_raw:
                        continue
                    price_clean = price_raw.replace("R$", "").replace(".", "").replace(",", ".").strip()
                    price = f"{float(price_clean):.2f} BRL"

                    items = page.locator('.main_features.font-description ul li').all()
                    brand = model = year = mileage = body_style_raw = ""
                    for item in items:
                        labels = item.locator("p").all()
                        if len(labels) >= 2:
                            label = labels[0].text_content().strip().lower()
                            value = labels[1].text_content().strip()
                            if "marca" in label:
                                brand = value
                            elif "modelo" in label:
                                model = value
                            elif "versão" in label:
                                body_style_raw = value.lower()
                            elif "ano" in label:
                                year = value.split("/")[0].strip()
                            elif "km" in label:
                                mileage = value.replace(".", "").replace("km", "").replace("KM", "").strip()

                    if not all([brand, model, year]):
                        continue

                    detected_style = detect_body_style(f"{brand} {model} {body_style_raw}")

                    car_data.append({
                        "vehicle_id": vehicle_id,
                        "title": f"{brand} {model} {body_style_raw} {year}",
                        "description": f"{brand} {model} {body_style_raw}, ano {year}, {mileage} KM.",
                        "url": href,
                        "body_style": detected_style,
                        "price": price,
                        "state_of_vehicle": "USED",
                        "make": brand,
                        "model": model,
                        "year": year,
                        "mileage": mileage,
                        "image": image_link,
                        "additional_image_link": additional_image_link,
                        "address": "Av. Universitária, 1805 - Santa Isabel, Anápolis - GO"
                    })
                except Exception as e:
                    print(f"⚠️ Erro ao processar {href}: {e}")
                    continue

            pagina += 1

        browser.close()
    return car_data

def gerar_xml(car_data):
    root = ET.Element("listings")
    for car in car_data:
        listing = ET.SubElement(root, "listing")
        ET.SubElement(listing, "vehicle_id").text = car["vehicle_id"]
        ET.SubElement(listing, "vehicle_offer_id").text = car["vehicle_id"]
        ET.SubElement(listing, "title").text = car["title"]
        ET.SubElement(listing, "description").text = car["description"]
        ET.SubElement(listing, "url").text = car["url"]
        ET.SubElement(listing, "body_style").text = car["body_style"]
        ET.SubElement(listing, "price").text = car["price"]
        ET.SubElement(listing, "state_of_vehicle").text = car["state_of_vehicle"]
        ET.SubElement(listing, "make").text = car["make"]
        ET.SubElement(listing, "model").text = car["model"]
        ET.SubElement(listing, "year").text = str(car["year"])
        mileage = ET.SubElement(listing, "mileage")
        ET.SubElement(mileage, "unit").text = "KM"
        ET.SubElement(mileage, "value").text = str(car["mileage"])
        image_main = ET.SubElement(listing, "image")
        ET.SubElement(image_main, "url").text = car["image"]
        additional_images = car["additional_image_link"].split(',')
        for img_url in additional_images:
            if img_url.strip():
                image_additional = ET.SubElement(listing, "image")
                ET.SubElement(image_additional, "url").text = img_url.strip()
        address = ET.SubElement(listing, "address", format="simple")
        ET.SubElement(address, "component", name="addr1").text = car["address"]
        ET.SubElement(address, "component", name="city").text = "Anápolis"
        ET.SubElement(address, "component", name="region").text = "Goiás"
        ET.SubElement(address, "component", name="country").text = "Brasil"

    xml_filename = "catalogo_facebook.xml"
    tree = ET.ElementTree(root)
    tree.write(xml_filename, encoding="utf-8", xml_declaration=True)
    print(f"✅ Catálogo XML gerado com sucesso: {xml_filename}")
    return xml_filename

def enviar_via_ftp(file_path):
    ftp_host = "147.93.64.85"
    ftp_user = "u684149221.feiraosandroveiculos.site"
    ftp_pass = "Anapolis10@"
    remote_path = "/public_html/catalogo_facebook.xml"

    try:
        ftp = FTP(ftp_host)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        print(f"✅ Conectado ao servidor FTP: {ftp_host}")
        with open(file_path, "rb") as file:
            ftp.storbinary(f"STOR {remote_path}", file)
        print(f"✅ Arquivo enviado com sucesso para {remote_path}")
        ftp.quit()
    except Exception as e:
        print(f"❌ Erro ao enviar o arquivo: {e}")

if __name__ == "__main__":
    carros = coletar_carros()
    xml_file = gerar_xml(carros)
    enviar_via_ftp(xml_file)
