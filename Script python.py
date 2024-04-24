from google.cloud import bigquery
import os
import requests
from datetime import timedelta
import pandas as pd
import time
import re

# Création d'un client BigQuery
client = bigquery.Client()

# Configuration des paramètres pour chaque sport avec leurs endpoints et clés API spécifiques
configs = {
    "basket": {
        "table_id": "basket_orders",
        "api_url": os.environ.get("SHOPIFY_BASKET_ENDPOINT"),
        "api_key": os.environ.get("SHOPIFY_BASKET_API_KEY"),
        "password": os.environ.get("SHOPIFY_BASKET_PASSWORD")
    },
    "rugby": {
        "table_id": "rugby_orders",
        "api_url": os.environ.get("SHOPIFY_RUGBY_ENDPOINT"),
        "api_key": os.environ.get("SHOPIFY_RUGBY_API_KEY"),
        "password": os.environ.get("SHOPIFY_RUGBY_PASSWORD")
    },
    "foot": {
        "table_id": "foot_orders",
        "api_url": os.environ.get("SHOPIFY_FOOT_ENDPOINT"),
        "api_key": os.environ.get("SHOPIFY_FOOT_API_KEY"),
        "password": os.environ.get("SHOPIFY_FOOT_PASSWORD")
    }
}

# Fonction pour extraire une valeur d'un dictionnaire contenu dans une série Pandas
def extract_from_dict(col, key):
    return col.apply(lambda x: x.get(key) if isinstance(x, dict) else None)

# Fonction pour extraire une chaîne de valeurs à partir d'une liste de dictionnaires dans une série Pandas
def extract_from_list_of_dicts(col, key, separator=", "):
    return col.apply(lambda x: separator.join([str(sub[key]) for sub in x if key in sub]) if isinstance(x, list) else None)

# Fonction pour sommer tous les montants de réduction à partir de la liste des codes de réduction
def sum_discounts(col):
    return col.apply(lambda x: sum([float(d['amount']) for d in x]) if isinstance(x, list) else 0)

# Fonction pour supprimer les pictogrammes et caractères indésirables d'une chaîne de texte
def remove_pictograms(text):
    text = re.sub(r'\(X\d+\)', '', text)  
    text = re.sub(r'\+', '', text)        
    text = re.sub(r'/\s*', '', text)      
    emoji_reg = re.compile('[\U00010000-\U0010ffff]', flags=re.UNICODE) 
    text = emoji_reg.sub(r'', text)
    return text.strip()

# Fonction pour extraire les tailles des articles d'une chaîne de texte
def extract_sizes(lineitem_name, predefined_sizes):
    if isinstance(lineitem_name, str):
        for size in predefined_sizes:
            if re.search(r'\b{}\b'.format(re.escape(size)), lineitem_name, flags=re.IGNORECASE):
                return size
    return None
# Prédéfinition des tailles standard pour la recherche dans les noms des articles
predefined_sizes = ['Standard', 'L', '13/14 ans', '11/12 ans', '5/6 ans', '9/10 ans', '7/8 ans', 'XL', 'S', 'M', 'XS', '2XL', 'XXL', '3XL', '4XL', '5XL', '3/4 ans', '4 ans', '14 ans', '10 ans', '12 ans', '8 ans', '6 ans', 'Taille unique']

# Fonction pour décomposer la colonne 'line_items' en plusieurs lignes pour chaque commande
def unpack_items(df):
    items = df['line_items'].apply(lambda x: [{'quantity': item['quantity'], 
                                                'price': item['price'], 
                                                'title': item['title'],
                                                'variant_title': item.get('variant_title', 'Unknown')}  # Use .get() with default
                                                for item in x] if isinstance(x, list) else None)
    rows = []
    for i, row in enumerate(items):
        if row:
            for item in row:
                new_row = df.iloc[i].to_dict()
                new_row.update(item)
                rows.append(new_row)
        else:
            new_row = df.iloc[i].to_dict()
            new_row.update({'quantity': None, 'price': None, 'title': None, 'variant_title': 'Unknown'})  # Provide default value here too
            rows.append(new_row)
    
    return pd.DataFrame(rows)

# Dictionnaire de correspondance des départements français aux régions
departments_to_regions = {
    '01': 'Auvergne-Rhône-Alpes',
    '02': 'Hauts-de-France',
    '03': 'Auvergne-Rhône-Alpes',
    '04': 'Provence-Alpes-Côte dAzur',
    '05': 'Provence-Alpes-Côte dAzur',
    '06': 'Provence-Alpes-Côte dAzur',
    '07': 'Auvergne-Rhône-Alpes',
    '08': 'Grand Est',
    '09': 'Occitanie',
    '10': 'Grand Est',
    '11': 'Occitanie',
    '12': 'Occitanie',
    '13': 'Provence-Alpes-Côte dAzur',
    '14': 'Normandie',
    '15': 'Auvergne-Rhône-Alpes',
    '16': 'Nouvelle-Aquitaine',
    '17': 'Nouvelle-Aquitaine',
    '18': 'Centre-Val de Loire',
    '19': 'Nouvelle-Aquitaine',
    '20': 'Corse',
    '21': 'Bourgogne-Franche-Comté',
    '22': 'Bretagne',
    '23': 'Nouvelle-Aquitaine',
    '24': 'Nouvelle-Aquitaine',
    '25': 'Bourgogne-Franche-Comté',
    '26': 'Auvergne-Rhône-Alpes',
    '27': 'Normandie',
    '28': 'Centre-Val de Loire',
    '29': 'Bretagne',
    '30': 'Occitanie',
    '31': 'Occitanie',
    '32': 'Occitanie',
    '33': 'Nouvelle-Aquitaine',
    '34': 'Occitanie',
    '35': 'Bretagne',
    '36': 'Centre-Val de Loire',
    '37': 'Centre-Val de Loire',
    '38': 'Auvergne-Rhône-Alpes',
    '39': 'Bourgogne-Franche-Comté',
    '40': 'Nouvelle-Aquitaine',
    '41': 'Centre-Val de Loire',
    '42': 'Auvergne-Rhône-Alpes',
    '43': 'Auvergne-Rhône-Alpes',
    '44': 'Pays de la Loire',
    '45': 'Centre-Val de Loire',
    '46': 'Occitanie',
    '47': 'Nouvelle-Aquitaine',
    '48': 'Occitanie',
    '49': 'Pays de la Loire',
    '50': 'Normandie',
    '51': 'Grand Est',
    '52': 'Grand Est',
    '53': 'Pays de la Loire',
    '54': 'Grand Est',
    '55': 'Grand Est',
    '56': 'Bretagne',
    '57': 'Grand Est',
    '58': 'Bourgogne-Franche-Comté',
    '59': 'Hauts-de-France',
    '60': 'Hauts-de-France',
    '61': 'Normandie',
    '62': 'Hauts-de-France',
    '63': 'Auvergne-Rhône-Alpes',
    '64': 'Nouvelle-Aquitaine',
    '65': 'Occitanie',
    '66': 'Occitanie',
    '67': 'Grand Est',
    '68': 'Grand Est',
    '69': 'Auvergne-Rhône-Alpes',
    '70': 'Bourgogne-Franche-Comté',
    '71': 'Bourgogne-Franche-Comté',
    '72': 'Pays de la Loire',
    '73': 'Auvergne-Rhône-Alpes',
    '74': 'Auvergne-Rhône-Alpes',
    '75': 'Île-de-France',
    '76': 'Normandie',
    '77': 'Île-de-France',
    '78': 'Île-de-France',
    '79': 'Nouvelle-Aquitaine',
    '80': 'Hauts-de-France',
    '81': 'Occitanie',
    '82': 'Occitanie',
    '83': 'Provence-Alpes-Côte dAzur',
    '84': 'Provence-Alpes-Côte dAzur',
    '85': 'Pays de la Loire',
    '86': 'Nouvelle-Aquitaine',
    '87': 'Nouvelle-Aquitaine',
    '88': 'Grand Est',
    '89': 'Bourgogne-Franche-Comté',
    '90': 'Bourgogne-Franche-Comté',
    '91': 'Île-de-France',
    '92': 'Île-de-France',
    '93': 'Île-de-France',
    '94': 'Île-de-France',
    '95': 'Île-de-France',
    '97': 'Outre mer',
    '0': 'Autres pays',
}

# Liste des colonnes requises pour la base de données BigQuery
columns_required = [
    'id', 'created_at', 'closed_at', 'order_number', 'current_subtotal_price', 'current_total_discounts',
    'current_total_price', 'current_total_tax', 'email', 'source_name', 'name', 'user_id',
    'subtotal_price', 'total_price', 'discount_code', 'discount_amount', 'tags',
    'shipping_amount', 'shipping_address1', 'shipping_zip', 'shipping_country_code',
    'quantity', 'price', 'title', 'region', 'sizes', 'zip', 'buyer_accepts_marketing'
]

# Fonction pour charger les données dans BigQuery
def load_data_to_bigquery(df, dataset_id, table_id):
    schema = [
        bigquery.SchemaField("_id_", "INTEGER"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
        bigquery.SchemaField("closed_at", "TIMESTAMP"),
        bigquery.SchemaField("order_number", "INTEGER"),
        bigquery.SchemaField("current_subtotal_price", "FLOAT"),
        bigquery.SchemaField("current_total_discounts", "FLOAT"),
        bigquery.SchemaField("current_total_price", "FLOAT"),
        bigquery.SchemaField("current_total_tax", "FLOAT"),
        bigquery.SchemaField("email", "STRING"),
        bigquery.SchemaField("source_name", "STRING"),
        bigquery.SchemaField("name", "STRING"),
        bigquery.SchemaField("user_id", "FLOAT"),
        bigquery.SchemaField("subtotal_price", "FLOAT"),
        bigquery.SchemaField("total_price", "FLOAT"),
        bigquery.SchemaField("discount_code", "STRING"),
        bigquery.SchemaField("discount_amount", "FLOAT"),
        bigquery.SchemaField("tags", "STRING"),
        bigquery.SchemaField("shipping_amount", "FLOAT"),
        bigquery.SchemaField("shipping_address1", "STRING"),
        bigquery.SchemaField("shipping_zip", "STRING"),
        bigquery.SchemaField("shipping_country_code", "STRING"),
        bigquery.SchemaField("quantity", "INTEGER"),
        bigquery.SchemaField("price", "FLOAT"),
        bigquery.SchemaField("title", "STRING"),
        bigquery.SchemaField("region", "STRING"),
        bigquery.SchemaField("sizes", "STRING"),
        bigquery.SchemaField("zip", "INTEGER"),
        bigquery.SchemaField("buyer_accepts_marketing", "BOOLEAN"),
    ]
    job_config = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_APPEND")
    job = client.load_table_from_dataframe(df, f"{client.project}.{dataset_id}.{table_id}", job_config=job_config)
    job.result()  # Wait for the job to complete
    print(f"Loaded {df.shape[0]} rows into {dataset_id}:{table_id}")

# Fonction pour récupérer et charger les données pour un sport spécifique
def fetch_and_load_data_for_sport(sport_key):
    config = configs[sport_key]
    table_id = f"elated-bison-419709.bonmaillot.{config['table_id']}"
    
    # Fetch the latest close timestamp from BigQuery
    query = f'SELECT MAX(closed_at) AS last_close FROM `{table_id}`'
    result = client.query(query).to_dataframe()
    last_close = result['last_close'][0] if not result.empty else None
    print(f"Last close for {sport_key} was on: {last_close}")

    # Setup API request
    params = {'limit': 250, 'status': 'any'}
    if last_close:
        formatted_last_close = (last_close + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"{config['api_url']}?limit={params['limit']}&status={params['status']}&created_at_min={formatted_last_close}"
    else:
        url = f"{config['api_url']}?limit={params['limit']}&status={params['status']}"

    all_orders = []
    while url:
        response = requests.get(url, auth=(config['api_key'], config['password']))
        if response.status_code == 429:
            time.sleep(10) # Gestion de la limitation de taux
            continue
        if response.status_code != 200:
            print(f"Failed to fetch data for {sport_key}: {response.status_code} - {response.text}")
            break
        data = response.json()
        orders = data.get('orders', [])
        all_orders.extend(orders)
        print(f"Fetched {len(orders)} orders for {sport_key}.")
        url = response.links.get('next', {}).get('url')

    if all_orders:
        df = pd.DataFrame(all_orders)
        df = process_dataframe(df)
        load_data_to_bigquery(df, 'bonmaillot', config['table_id'])
    else:
        print(f"No new orders to process for {sport_key}.")

# Fonction principale pour traiter les données de dataframe
def process_dataframe(df):
    date_columns = ['created_at', 'closed_at']  
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    df = unpack_items(df)
    df['sizes'] = df['variant_title'].apply(lambda x: extract_sizes(x, predefined_sizes))
    df['discount_amount'] = sum_discounts(df['discount_codes'])
    df['shipping_amount'] = extract_from_dict(df['total_shipping_price_set'].apply(lambda x: x.get('shop_money') if isinstance(x, dict) else None), 'amount')
    df['discount_code'] = extract_from_list_of_dicts(df['discount_codes'], 'code')
    df['shipping_address1'] = extract_from_dict(df['shipping_address'], 'address1')
    df['shipping_zip'] = extract_from_dict(df['shipping_address'], 'zip')
    df['shipping_country_code'] = extract_from_dict(df['shipping_address'], 'country_code')
    df['shipping_zip'] = df['shipping_zip'].astype(str)
    df['region'] = df.apply(lambda x: departments_to_regions.get(x['shipping_zip'][:2]) if x['shipping_country_code'] == 'FR' else None, axis=1)
    df['title'] = df['title'].apply(remove_pictograms)
    df['name'] = extract_from_dict(df['billing_address'], 'name')
    df['user_id'] = extract_from_dict(df['customer'], 'id')
    df['zip'] = df.apply(lambda x: x['shipping_zip'][:2] if x['shipping_country_code'] == 'FR' else None, axis=1)
    df['region'] = df['zip'].map(departments_to_regions)
    df['zip'] = pd.to_numeric(df['zip'], errors='coerce').fillna(0).astype(int)
    float_columns = [
        'current_subtotal_price', 'current_total_discounts', 'current_total_price',
        'current_total_tax', 'subtotal_price', 'total_price', 'discount_amount', 
        'shipping_amount', 'price', 'user_id'
    ]
    for col in float_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df[columns_required]
    df = df.rename(columns={"id": "_id_"})
    return df

# Boucle sur chaque configuration de sport pour lancer la récupération et le chargement des données
for sport in configs.keys():
    fetch_and_load_data_for_sport(sport)




