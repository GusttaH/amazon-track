import requests
import boto3
import re
import time
from bs4 import BeautifulSoup
from datetime import datetime as date

aws_access_key_id=
aws_secret_access_key=

# user agent
HEADERS = ({'User-Agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
            'Accept-Language': 'en-US, en;q=0.5'})

def execute():
  print('> Initializing Proccess....')
  url = 'https://www.amazon.com.br/dp/B0754C5G89/ref=redir_mobile_desktop?_encoding=UTF8&psc=1&ref_=ox_sc_act_image_1&smid=A2I75BZTKIDOGV'
  count = 0
  price_before = 0
  while(1):
    time_coleta = date.now()
    print('\n> [%s] > coleta numero %s' % (time_coleta, count))
    soup = fetch_page(url)
    product_data = get_product_data(soup)
    price_after = format_value_real(product_data['price'])
    print('> Product: %s  \n> Price: %s \n> Seller: %s' % (product_data['title'], product_data['price'], product_data['seller']['name']))

    if(price_after < price_before):
      print('> O Preço caiu! Enviando E-Mail...')
      send_email(product_data, price_after, price_before)

    price_before = price_after
    write_log(product_data, time_coleta)
    count = count + 1
    time.sleep(600)


def send_email(product_data, price_after, price_before):

  client = boto3.client(
    'ses',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key  
  )

  try:
    client.send_email(
        Source='contato.gustta.h@hotmail.com',
        Destination={
            'ToAddresses': [
                'dev.gustta.h@gmail.com',
                'Vitoria.isabela28@gmail.com'
            ],
        },
        Message={
            'Subject': {
                'Data': 'Atualização de preço {}'.format(product_data['title']),
                'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {
                    'Data': 'string',
                    'Charset': 'UTF-8'
                },
                'Html': {
                    'Data': """
                      <img src={} style="width: 300px"/>
                      <h1>Produto: {}</h1>
                      </br>
                      <h2>Preço Atual: {}</h2>
                      <h2>Preço Anterior: R${:.2f}</h2>
                      <h2>Economia: R${:.2f}</h2>
                      <h2>Frete: {}
                      <h2>Preço Total(Preço + Frete): R${:.2f}</h2>
                      <h2>Entrega: {} </h2>
                      <hr/>
                      <h1>Sobre o Vendedor: </h1>
                      <h2>Nome: {} </h2>
                      <h2>Avaliação: {} </h2>
                      <h2>Página do Vendedor: <a href="{}">Clique aqui</a> </h2>
                    
                    """.format(
                          product_data['image']
                        , product_data['title']
                        , product_data['price']
                        , price_before
                        , (price_before - price_after)
                        , product_data['shipping']['shipping']
                        , product_data['total']
                        , product_data['shipping']['dead_line']
                        , product_data['seller']['name']
                        , product_data['seller']['avaliation']
                        , product_data['seller']['url']
                      ),
                    'Charset': 'UTF-8'
                }
            }
        },
    )
    print('> Email succeeded!')
  except Exception as ex:
    print('Send Email error!', ex)

def get_product_data(soup):
  product_shipping = soup.find(id='mir-layout-DELIVERY_BLOCK-slot-DELIVERY_MESSAGE').text
  imageBody = soup.find(id='landingImage')['data-a-dynamic-image']
  shipping  = get_shipping(product_shipping)
  price = soup.find(id="price_inside_buybox").text.replace('\n', '')
  tot = format_value_real(shipping['shipping']) + format_value_real(price) if re.match('R\$', shipping['shipping']) else format_value_real(price)
  
  seller = get_seller(soup.find(id='sellerProfileTriggerId'))

  return { 
      'price': price
    , 'title': soup.find(id='productTitle').text.replace('\n', '')
    , 'image': re.findall('https://.*?"', imageBody)[0].replace('"', '') 
    , 'shipping': shipping
    , 'total': tot
    , 'seller': seller
  }

def write_log(product_data, time_coleta):
  f = open("log.txt", "a")
  f.write("\n[{}] > \"{}\" \t Price: {}".format(time_coleta, product_data['title'], product_data['price']))
  f.close()
  print('> Writing log...')

def get_shipping(shipping_string):
  shipping = shipping_string.replace('\n', '').replace(' com Frete GRÁTIS', '').split('Entrega:')
  return {
    'shipping': 'Frete Grátis' if not re.match('R\$', shipping[0]) else re.findall('R\$\d+[.|,]\d+', shipping[0])[0],
    'dead_line': shipping[1].strip(),
  }

def get_seller(seller):
  seller_url = 'https://amazon.com.br' + seller['href']
  seller_name = seller.text

  seller_page = fetch_page(seller_url)
  seller_avaliation = seller_page.find('a', {'class': 'feedback-detail-description'}).text
  return { 
      'name': seller_name
    , 'url': seller_url
    , 'avaliation': seller_avaliation
  }

def fetch_page(url):
    try:
        page = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(page.content, "html.parser")
        return soup
    except Exception as ex:
      print('Errror on request', ex)

def format_value_real(value):
  value = re.sub(r'([^0-9\,])','', value.strip())
  value = re.sub(r',','.', value.strip())
  return float(value)

execute()
